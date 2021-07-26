__all__ = ["XRecordInterface", "AtSpiInterface"]

from abc import abstractmethod
import typing
import threading
import select
import logging
import queue
import subprocess
import time

# Imported to enable threading in Xlib. See module description. Not an unused import statement.
import Xlib.threaded as xlib_threaded

# Delete again, as the reference is not needed anymore after the import side-effect has done it’s work.
# This (hopefully) also prevents automatic code cleanup software from deleting an "unused" import and re-introduce
# issues.
from autokey.hotkey import Hotkey
from autokey.hotkey_listener import HotkeyListener
from autokey.key import Key
from autokey.key import _ALL_MODIFIERS_ as MODIFIERS

del xlib_threaded

from Xlib.error import ConnectionClosedError


import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk

try:
    gi.require_version('Atspi', '2.0')
    import pyatspi
    HAS_ATSPI = True
except ImportError:
    HAS_ATSPI = False
except ValueError:
    HAS_ATSPI = False
except SyntaxError:  # pyatspi 2.26 fails when used with Python 3.7
    HAS_ATSPI = False

from Xlib import X, XK, display, error
try:
    from Xlib.ext import record, xtest
    HAS_RECORD = True
except ImportError:
    HAS_RECORD = False
    
from Xlib.protocol import rq, event


logger = logging.getLogger("interface")

MASK_INDEXES = [
               (X.ShiftMapIndex, X.ShiftMask),
               (X.ControlMapIndex, X.ControlMask),
               (X.LockMapIndex, X.LockMask),
               (X.Mod1MapIndex, X.Mod1Mask),
               (X.Mod2MapIndex, X.Mod2Mask),
               (X.Mod3MapIndex, X.Mod3Mask),
               (X.Mod4MapIndex, X.Mod4Mask),
               (X.Mod5MapIndex, X.Mod5Mask),
               ]

CAPSLOCK_LEDMASK = 1<<0
NUMLOCK_LEDMASK = 1<<1


def str_or_bytes_to_bytes(x: typing.Union[str, bytes, memoryview]) -> bytes:
    if type(x) == bytes:
        # logger.info("using LiuLang's python3-xlib")
        return x
    if type(x) == str:
        logger.debug("using official python-xlib")
        return x.encode("utf8")
    if type(x) == memoryview:
        logger.debug("using official python-xlib")
        return x.tobytes()
    raise RuntimeError("x must be str or bytes or memoryview object, type(x)={}, repr(x)={}".format(type(x), repr(x)))


# This tuple is used to return requested window properties.
WindowInfo = typing.NamedTuple("WindowInfo", [("wm_title", str), ("wm_class", str)])


class XInterfaceBase(threading.Thread):
    """
    Encapsulates the common functionality for the two X interface classes.
    """

    def __init__(self, hotkeys: typing.List[Hotkey], hotkey_listener: HotkeyListener):
        threading.Thread.__init__(self)
        self._hotkeys = hotkeys
        self._hotkey_listener = hotkey_listener
        self.setDaemon(True)
        self.setName("XInterface-thread")
        self.lastChars = [] # QT4 Workaround
        self.__enableQT4Workaround = False # QT4 Workaround
        self.shutdown = False
        
        # Event loop
        self.eventThread = threading.Thread(target=self.__eventLoop)
        self.queue = queue.Queue()
        
        # Event listener
        self.listenerThread = threading.Thread(target=self.__flushEvents)

        self.__initMappings()

        # Set initial lock state
        ledMask = self.localDisplay.get_keyboard_control().led_mask
        self.modifiers = {
            Key.CONTROL: False,
            Key.ALT: False,
            Key.ALT_GR: False,
            Key.SHIFT: False,
            Key.SUPER: False,
            Key.HYPER: False,
            Key.META: False,
            Key.CAPSLOCK: False,
            Key.NUMLOCK: False
        }
        self.modifiers[Key.CAPSLOCK] = (ledMask & CAPSLOCK_LEDMASK) != 0
        self.modifiers[Key.NUMLOCK] = (ledMask & NUMLOCK_LEDMASK) != 0

        # Window name atoms
        self.__NameAtom = self.localDisplay.intern_atom("_NET_WM_NAME", True)
        self.__VisibleNameAtom = self.localDisplay.intern_atom("_NET_WM_VISIBLE_NAME", True)

        self.__ignoreRemap = False
        
        self.eventThread.start()
        self.listenerThread.start()
        
    def __eventLoop(self):
        while True:
            method, args = self.queue.get()
            
            if method is None and args is None:
                break
            elif method is not None and args is None:
                logger.debug("__eventLoop: Got method {} with None arguments!".format(method))
            try:
                method(*args)
            except Exception as e:
                logger.exception("Error in X event loop thread")

            self.queue.task_done()

    def __enqueue(self, method: typing.Callable, *args):
        self.queue.put_nowait((method, args))

    def on_keys_changed(self, data=None):
        if not self.__ignoreRemap:
            logger.debug("Recorded keymap change event")
            self.__ignoreRemap = True
            time.sleep(0.2)
            self.__enqueue(self.__ungrabAllHotkeys)
            self.__enqueue(self.__delayedInitMappings)
        else:
            logger.debug("Ignored keymap change event")

    def __delayedInitMappings(self):        
        self.__initMappings()
        self.__ignoreRemap = False

    def __initMappings(self):
        self.localDisplay = display.Display()
        self.rootWindow = self.localDisplay.screen().root
        self.rootWindow.change_attributes(event_mask=X.SubstructureNotifyMask|X.StructureNotifyMask)
        
        altList = self.localDisplay.keysym_to_keycodes(XK.XK_ISO_Level3_Shift)
        self.__usableOffsets = (0, 1)
        for code, offset in altList:
            if code == 108 and offset == 0:
                self.__usableOffsets += (4, 5)
                logger.debug("Enabling sending using Alt-Grid")
                break

        # Build modifier mask mapping
        self.modMasks = {}
        mapping = self.localDisplay.get_modifier_mapping()

        for keySym, ak in XK_TO_AK_MAP.items():
            if ak in MODIFIERS:
                keyCodeList = self.localDisplay.keysym_to_keycodes(keySym)
                found = False

                for keyCode, lvl in keyCodeList:
                    for index, mask in MASK_INDEXES:
                        if keyCode in mapping[index]:
                            self.modMasks[ak] = mask
                            found = True
                            break

                    if found: break

        logger.debug("Modifier masks: %r", self.modMasks)

        self.__grabHotkeys()
        self.localDisplay.flush()

        # --- get list of keycodes that are unused in the current keyboard mapping

        keyCode = 8
        avail = []
        for keyCodeMapping in self.localDisplay.get_keyboard_mapping(keyCode, 200):
            codeAvail = True
            for offset in keyCodeMapping:
                if offset != 0:
                    codeAvail = False
                    break

            if codeAvail:
                avail.append(keyCode)

            keyCode += 1

        self.__availableKeycodes = avail
        self.remappedChars = {}

        if logging.getLogger().getEffectiveLevel() == logging.DEBUG:
            self.keymap_test()

    def keymap_test(self):
        code = self.localDisplay.keycode_to_keysym(108, 0)
        for attr in XK.__dict__.items():
            if attr[0].startswith("XK"):
                if attr[1] == code:
                    logger.debug("Alt-Grid: %s, %s", attr[0], attr[1])

        logger.debug("X Server Keymap, listing unmapped keys.")
        for char in "\\|`1234567890-=~!@#$%^&*()qwertyuiop[]asdfghjkl;'zxcvbnm,./QWERTYUIOP{}ASDFGHJKL:\"ZXCVBNM<>?":
            keyCodeList = list(self.localDisplay.keysym_to_keycodes(ord(char)))
            if not keyCodeList:
                logger.debug("No mapping for [%s]", char)
                
    def __needsMutterWorkaround(self, hotkey: Hotkey):
        if Key.SUPER not in hotkey.modifiers:
            return False
    
        try:
            output = subprocess.check_output(["ps", "-eo", "command"]).decode()
        except subprocess.CalledProcessError:
            pass # since this is just a nasty workaround, if anything goes wrong just disable it 
        else:
            lines = output.splitlines()
            
            for line in lines:
                if "gnome-shell" in line or "cinnamon" in line or "unity" in line:
                    return True
                
        return False

    def __grabHotkeys(self):
        """
        Run during startup to grab global and specific hotkeys in all open windows
        """
        # Grab global hotkeys in root window
        for hotkey in self._hotkeys:
            self.__enqueue(self.__grabHotkey, hotkey, self.rootWindow)
            if self.__needsMutterWorkaround(hotkey):
                self.__enqueue(self.__grabRecurse, hotkey, self.rootWindow, False)

        self.__enqueue(self.__recurseTree, self.rootWindow, self._hotkeys)

    def __recurseTree(self, parent, hotkeys: typing.List[Hotkey]):
        # Grab matching hotkeys in all open child windows
        try:
            children = parent.query_tree().children
        except:
            return # window has been destroyed
            
        for window in children:
            try:
                window_info = self.get_window_info(window, False)
                
                if window_info.wm_title or window_info.wm_class:
                    for hotkey in hotkeys:
                        self.__grabHotkey(hotkey, window)
                        self.__grabRecurse(hotkey, window, False)
                        
                self.__enqueue(self.__recurseTree, window, hotkeys)
            except:
                logger.exception("grab on window failed")
                
    def __ungrabAllHotkeys(self):
        """
        Ungrab all hotkeys in preparation for keymap change
        """
        # Ungrab global hotkeys in root window, recursively
        for hotkey in self._hotkeys:
            self.__ungrabHotkey(hotkey, self.rootWindow)
            if self.__needsMutterWorkaround(hotkey):
                self.__ungrabRecurse(hotkey, self.rootWindow, False)
        
        self.__recurseTreeUngrab(self.rootWindow, self._hotkeys)
                
    def __recurseTreeUngrab(self, parent, hotkeys: typing.List[Hotkey]):
        # Ungrab matching hotkeys in all open child windows
        try:
            children = parent.query_tree().children
        except:
            return # window has been destroyed
            
        for window in children:
            try:
                window_info = self.get_window_info(window, False)
                
                if window_info.wm_title or window_info.wm_class:
                    for hotkey in hotkeys:
                        self.__ungrabHotkey(hotkey, window)
                        self.__ungrabRecurse(hotkey, window, False)
                        
                self.__enqueue(self.__recurseTreeUngrab, window, hotkeys)
            except:
                logger.exception("ungrab on window failed")

    def __grabHotkeysForWindow(self, window):
        """
        Grab all hotkeys relevant to the window

        Used when a new window is created
        """
        c = self.app.configManager
        hotkeys = c.hotKeys + c.hotKeyFolders
        window_info = self.get_window_info(window)
        for item in hotkeys:
            if item.get_applicable_regex() is not None and item._should_trigger_window_title(window_info):
                self.__enqueue(self.__grabHotkey, item.hotKey, item.modifiers, window)
            elif self.__needsMutterWorkaround(item):
                self.__enqueue(self.__grabHotkey, item.hotKey, item.modifiers, window)

    def __grabHotkey(self, hotkey: Hotkey, window):
        """
        Grab a specific hotkey in the given window
        """
        logger.debug("Grabbing hotkey: %r %r", hotkey.modifiers, hotkey.key)
        try:
            keycode = self.__lookupKeyCode(hotkey.key)
            mask = 0
            for mod in hotkey.modifiers:
                mask |= self.modMasks[mod]

            window.grab_key(keycode, mask, True, X.GrabModeAsync, X.GrabModeAsync)

            if Key.NUMLOCK in self.modMasks:
                window.grab_key(keycode, mask|self.modMasks[Key.NUMLOCK], True, X.GrabModeAsync, X.GrabModeAsync)

            if Key.CAPSLOCK in self.modMasks:
                window.grab_key(keycode, mask|self.modMasks[Key.CAPSLOCK], True, X.GrabModeAsync, X.GrabModeAsync)

            if Key.CAPSLOCK in self.modMasks and Key.NUMLOCK in self.modMasks:
                window.grab_key(keycode, mask|self.modMasks[Key.CAPSLOCK]|self.modMasks[Key.NUMLOCK], True, X.GrabModeAsync, X.GrabModeAsync)

        except Exception as e:
            logger.warning("Failed to grab hotkey %r %r: %s", hotkey.modifiers, hotkey.key, str(e))

    def grab_hotkey(self, item):
        """
        Grab a hotkey.

        If the hotkey has no filter regex, it is global and is grabbed recursively from the root window
        If it has a filter regex, iterate over all children of the root and grab from matching windows
        """
        if item.get_applicable_regex() is None:
            self.__enqueue(self.__grabHotkey, item.hotKey, item.modifiers, self.rootWindow)
            if self.__needsMutterWorkaround(item):
                self.__enqueue(self.__grabRecurse, item, self.rootWindow, False)
        else:
            self.__enqueue(self.__grabRecurse, item, self.rootWindow)

    def __grabRecurse(self, hotkey: Hotkey, parent, checkWinInfo=True):
        try:
            children = parent.query_tree().children
        except:
            return # window has been destroyed
                     
        for window in children:
            if checkWinInfo:
                window_info = self.get_window_info(window, False)

            if not checkWinInfo:
                self.__grabHotkey(hotkey, window)
                self.__grabRecurse(hotkey, window, False)
            else:
                self.__grabRecurse(hotkey, window)

    def ungrab_hotkey(self, item):
        """
        Ungrab a hotkey.

        If the hotkey has no filter regex, it is global and is grabbed recursively from the root window
        If it has a filter regex, iterate over all children of the root and ungrab from matching windows
        """
        import copy
        newItem = copy.copy(item)
        
        if item.get_applicable_regex() is None:
            self.__enqueue(self.__ungrabHotkey, newItem.hotKey, newItem.modifiers, self.rootWindow)
            if self.__needsMutterWorkaround(item):
                self.__enqueue(self.__ungrabRecurse, newItem, self.rootWindow, False)
        else:
            self.__enqueue(self.__ungrabRecurse, newItem, self.rootWindow)

    def __ungrabRecurse(self, hotkey: Hotkey, parent, checkWinInfo=True):
        try:
            children = parent.query_tree().children
        except:
            return # window has been destroyed
                     
        for window in children:
            if checkWinInfo:
                window_info = self.get_window_info(window, False)

            if not checkWinInfo:
                self.__ungrabHotkey(hotkey, window)
                self.__ungrabRecurse(hotkey, window, False)
            else:
                self.__ungrabRecurse(hotkey, window)

    def __ungrabHotkey(self, hotkey: Hotkey, window):
        """
        Ungrab a specific hotkey in the given window
        """
        logger.debug("Ungrabbing hotkey: %r %r", hotkey.modifiers, hotkey.key)
        try:
            keycode = self.__lookupKeyCode(hotkey.key)
            mask = 0
            for mod in hotkey.modifiers:
                mask |= self.modMasks[mod]

            window.ungrab_key(keycode, mask)

            if Key.NUMLOCK in self.modMasks:
                window.ungrab_key(keycode, mask|self.modMasks[Key.NUMLOCK])

            if Key.CAPSLOCK in self.modMasks:
                window.ungrab_key(keycode, mask|self.modMasks[Key.CAPSLOCK])

            if Key.CAPSLOCK in self.modMasks and Key.NUMLOCK in self.modMasks:
                window.ungrab_key(keycode, mask|self.modMasks[Key.CAPSLOCK]|self.modMasks[Key.NUMLOCK])
        except Exception as e:
            logger.warning("Failed to ungrab hotkey %r %r: %s", hotkey.modifiers, hotkey.key, str(e))

    def lookup_string(self, keyCode, shifted, numlock, altGrid):
        if keyCode == 0:
            return "<unknown>"

        keySym = self.localDisplay.keycode_to_keysym(keyCode, 0)

        if keySym in XK_TO_AK_NUMLOCKED and numlock and not (numlock and shifted):
            return XK_TO_AK_NUMLOCKED[keySym]

        elif keySym in XK_TO_AK_MAP:
            return XK_TO_AK_MAP[keySym]
        else:
            index = 0
            if shifted: index += 1
            if altGrid: index += 4
            try:
                return chr(self.localDisplay.keycode_to_keysym(keyCode, index))
            except ValueError:
                return "<code%d>" % keyCode

    def begin_send(self):
        self.__enqueue(self.__grab_keyboard)

    def finish_send(self):
        self.__enqueue(self.__ungrabKeyboard)

    def grab_keyboard(self):
        self.__enqueue(self.__grab_keyboard)

    def __grab_keyboard(self):
        focus = self.localDisplay.get_input_focus().focus
        focus.grab_keyboard(True, X.GrabModeAsync, X.GrabModeAsync, X.CurrentTime)
        self.localDisplay.flush()

    def ungrab_keyboard(self):
        self.__enqueue(self.__ungrabKeyboard)
        
    def __ungrabKeyboard(self):
        self.localDisplay.ungrab_keyboard(X.CurrentTime)
        self.localDisplay.flush()

    def __findUsableKeycode(self, codeList):
        for code, offset in codeList:
            if offset in self.__usableOffsets:
                return code, offset

        return None, None

    def flush(self):
        self.__enqueue(self.__flush)
        
    def __flush(self):
        self.localDisplay.flush()
        self.lastChars = []

    def __flushEvents(self):
        logger.debug("__flushEvents: Entering event loop.")
        while True:
            try:
                readable, w, e = select.select([self.localDisplay], [], [], 1)
                time.sleep(1)
                if self.localDisplay in readable:
                    createdWindows = []
                    destroyedWindows = []
                    
                    for x in range(self.localDisplay.pending_events()):
                        event = self.localDisplay.next_event()
                        if event.type == X.CreateNotify:
                            createdWindows.append(event.window)
                        if event.type == X.DestroyNotify:
                            destroyedWindows.append(event.window)
                            
                    for window in createdWindows:
                        if window not in destroyedWindows:
                            self.__enqueue(self.__grabHotkeysForWindow, window)

                if self.shutdown:
                    break
            except ConnectionClosedError:
                # Autokey does not properly exit on logout. It causes an infinite exception loop, accumulating stack
                # traces along. This acts like a memory leak, filling the system RAM until it hits an OOM condition.
                # TODO: implement a proper exit mechanic that gracefully exits AutoKey in this case.
                # Maybe react to a dbus message that announces the session end, before the X server forcefully closes
                # the connection.
                # See https://github.com/autokey/autokey/issues/198 for details
                logger.exception("__flushEvents: Connection to the X server closed. Forcefully exiting Autokey now.")
                import os
                os._exit(1)
            except Exception:
                logger.exception("__flushEvents: Some exception occured:")
                pass
        logger.debug("__flushEvents: Left event loop.")

    def handle_keypress(self, keyCode):
        self.__enqueue(self.__handleKeyPress, keyCode)
    
    def __handleKeyPress(self, keyCode):
        modifier = self.__decodeModifier(keyCode)
        if modifier is not None:
            self._hotkey_listener.handle_modifier_down(modifier)
        else:
            self._hotkey_listener.handle_keypress(self.lookup_string(keyCode, False, False, False))

    def handle_keyrelease(self, keyCode):
        self.__enqueue(self.__handleKeyrelease, keyCode)
    
    def __handleKeyrelease(self, keyCode):
        modifier = self.__decodeModifier(keyCode)
        if modifier is not None:
            self._hotkey_listener.handle_modifier_up(modifier)

    def __decodeModifier(self, keyCode):
        """
        Checks if the given keyCode is a modifier key. If it is, returns the modifier name
        constant as defined in the iomediator module. If not, returns C{None}
        """
        keyName = self.lookup_string(keyCode, False, False, False)
        if keyName in MODIFIERS:
            return keyName

        return None

    def __checkWorkaroundNeeded(self):
        focus = self.localDisplay.get_input_focus().focus
        window_info = self.get_window_info(focus)
        w = self.app.configManager.workAroundApps
        if w.match(window_info.wm_title) or w.match(window_info.wm_class):
            self.__enableQT4Workaround = True
        else:
            self.__enableQT4Workaround = False

    def __doQT4Workaround(self, keyCode):
        if len(self.lastChars) > 0:
            if keyCode in self.lastChars:
                self.localDisplay.flush()
                time.sleep(0.0125)

        self.lastChars.append(keyCode)

        if len(self.lastChars) > 10:
            self.lastChars.pop(0)

    def __lookupKeyCode(self, char: str) -> int:
        if char in AK_TO_XK_MAP:
            return self.localDisplay.keysym_to_keycode(AK_TO_XK_MAP[char])
        elif char.startswith("<code"):
            return int(char[5:-1])
        else:
            try:
                return self.localDisplay.keysym_to_keycode(ord(char))
            except Exception as e:
                logger.error("Unknown key name: %s", char)
                raise

    def get_window_info(self, window=None, traverse: bool=True) -> WindowInfo:
        try:
            if window is None:
                window = self.localDisplay.get_input_focus().focus
            return self._get_window_info(window, traverse)
        except error.BadWindow:
            logger.exception("Got BadWindow error while requesting window information.")
            return self._create_window_info(window, "", "")

    def _get_window_info(self, window, traverse: bool, wm_title: str=None, wm_class: str=None) -> WindowInfo:
        new_wm_title = self._try_get_window_title(window)
        new_wm_class = self._try_get_window_class(window)

        if not wm_title and new_wm_title:  # Found title, update known information
            wm_title = new_wm_title
        if not wm_class and new_wm_class:  # Found class, update known information
            wm_class = new_wm_class

        if traverse:
            # Recursive operation on the parent window
            if wm_title and wm_class:  # Both known, abort walking the tree and return the data.
                return self._create_window_info(window, wm_title, wm_class)
            else:  # At least one property is still not known. So walk the window tree up.
                parent = window.query_tree().parent
                # Stop traversal, if the parent is not a window. When querying the parent, at some point, an integer
                # is returned. Then just stop following the tree.
                if isinstance(parent, int):
                    # At this point, wm_title or wm_class may still be None. The recursive call with traverse=False
                    # will replace any None with an empty string. See below.
                    return self._get_window_info(window, False, wm_title, wm_class)
                else:
                    return self._get_window_info(parent, traverse, wm_title, wm_class)

        else:
            # No recursion, so fill unknown values with empty strings.
            if wm_title is None:
                wm_title = ""
            if wm_class is None:
                wm_class = ""
            return self._create_window_info(window, wm_title, wm_class)

    def _create_window_info(self, window, wm_title: str, wm_class: str):
        """
        Creates a WindowInfo object from the window title and WM_CLASS.
        Also checks for the Java XFocusProxyWindow workaround and applies it if needed:

        Workaround for Java applications: Java AWT uses a XFocusProxyWindow class, so to get usable information,
        the parent window needs to be queried. Credits: https://github.com/mooz/xkeysnail/pull/32
        https://github.com/JetBrains/jdk8u_jdk/blob/master/src/solaris/classes/sun/awt/X11/XFocusProxyWindow.java#L35
        """
        if "FocusProxy" in wm_class:
            parent = window.query_tree().parent
            # Discard both the already known wm_class and window title, because both are known to be wrong.
            return self._get_window_info(parent, False)
        else:
            return WindowInfo(wm_title=wm_title, wm_class=wm_class)

    def _try_get_window_title(self, window) -> typing.Optional[str]:
        atom = self._try_read_property(window, self.__VisibleNameAtom)
        if atom is None:
            atom = self._try_read_property(window, self.__NameAtom)
        if atom:
            value = atom.value  # type: typing.Union[str, bytes]
            # based on python3-xlib version, atom.value may be a bytes object, then decoding is necessary.
            return value.decode("utf-8") if isinstance(value, bytes) else value
        else:
            return None

    @staticmethod
    def _try_read_property(window, property_name: str):
        """
        Try to read the given property of the given window.
        Returns the atom, if successful, None otherwise.
        """
        try:
            return window.get_property(property_name, 0, 0, 255)
        except error.BadAtom:
            return None

    @staticmethod
    def _try_get_window_class(window) -> typing.Optional[str]:
        wm_class = window.get_wm_class()
        if wm_class:
            return "{}.{}".format(wm_class[0], wm_class[1])
        else:
            return None

    def get_window_title(self, window=None, traverse=True) -> str:
        return self.get_window_info(window, traverse).wm_title

    def get_window_class(self, window=None, traverse=True) -> str:
        return self.get_window_info(window, traverse).wm_class

    def cancel(self):
        logger.debug("XInterfaceBase: Try to exit event thread.")
        self.queue.put_nowait((None, None))
        logger.debug("XInterfaceBase: Event thread exit marker enqueued.")
        self.shutdown = True
        logger.debug("XInterfaceBase: self.shutdown set to True. This should stop the listener thread.")
        self.listenerThread.join()
        self.eventThread.join()
        self.localDisplay.flush()
        self.localDisplay.close()
        self.join()


class XRecordInterface(XInterfaceBase):

    def initialise(self):
        self.recordDisplay = display.Display()
        self.__locksChecked = False

        # Check for record extension
        if not self.recordDisplay.has_extension("RECORD"):
            raise Exception("Your X-Server does not have the RECORD extension available/enabled.")

    def run(self):
        # Create a recording context; we only want key and mouse events
        self.ctx = self.recordDisplay.record_create_context(
                0,
                [record.AllClients],
                [{
                        'core_requests': (0, 0),
                        'core_replies': (0, 0),
                        'ext_requests': (0, 0, 0, 0),
                        'ext_replies': (0, 0, 0, 0),
                        'delivered_events': (0, 0),
                        'device_events': (X.KeyPress, X.KeyRelease), #X.KeyRelease,
                        'errors': (0, 0),
                        'client_started': False,
                        'client_died': False,
                }])

        # Enable the context; this only returns after a call to record_disable_context,
        # while calling the callback function in the meantime
        logger.info("XRecord interface thread starting")
        self.recordDisplay.record_enable_context(self.ctx, self.__processEvent)
        # Finally free the context
        self.recordDisplay.record_free_context(self.ctx)
        self.recordDisplay.close()

    def cancel(self):
        self.localDisplay.record_disable_context(self.ctx)
        XInterfaceBase.cancel(self)

    def __processEvent(self, reply):
        if reply.category != record.FromServer:
            return
        if reply.client_swapped:
            return
        if not len(reply.data) or str_or_bytes_to_bytes(reply.data)[0] < 2:
            # not an event
            return

        data = reply.data
        while len(data):
            event, data = rq.EventField(None).parse_binary_value(data, self.recordDisplay.display, None, None)
            if event.type == X.KeyPress:
                self.handle_keypress(event.detail)
            elif event.type == X.KeyRelease:
                self.handle_keyrelease(event.detail)


class AtSpiInterface(XInterfaceBase):

    def initialise(self):
        self.registry = pyatspi.Registry

    def start(self):
        logger.info("AT-SPI interface thread starting")
        self.registry.registerKeystrokeListener(self.__processKeyEvent, mask=pyatspi.allModifiers())
        self.registry.registerEventListener(self.__processMouseEvent, 'mouse:button')

    def cancel(self):
        self.registry.deregisterKeystrokeListener(self.__processKeyEvent, mask=pyatspi.allModifiers())
        self.registry.deregisterEventListener(self.__processMouseEvent, 'mouse:button')
        self.registry.stop()
        XInterfaceBase.cancel(self)

    def __processKeyEvent(self, event):
        if event.type == pyatspi.KEY_PRESSED_EVENT:
            self.handle_keypress(event.hw_code)
        else:
            self.handle_keyrelease(event.hw_code)

    def __processMouseEvent(self, event):
        if event.type[-1] == 'p':
            button = int(event.type[-2])
            self.handle_mouseclick(button, event.detail1, event.detail2)

    def __pumpEvents(self):
        pyatspi.Registry.pumpQueuedEvents()
        return True


XK.load_keysym_group('xkb')

XK_TO_AK_MAP = {
           XK.XK_Shift_L: Key.SHIFT,
           XK.XK_Shift_R: Key.SHIFT,
           XK.XK_Caps_Lock: Key.CAPSLOCK,
           XK.XK_Control_L: Key.CONTROL,
           XK.XK_Control_R: Key.CONTROL,
           XK.XK_Alt_L: Key.ALT,
           XK.XK_Alt_R: Key.ALT,
           XK.XK_ISO_Level3_Shift: Key.ALT_GR,
           XK.XK_Super_L: Key.SUPER,
           XK.XK_Super_R: Key.SUPER,
           XK.XK_Hyper_L: Key.HYPER,
           XK.XK_Hyper_R: Key.HYPER,
           XK.XK_Meta_L: Key.META,
           XK.XK_Meta_R: Key.META,
           XK.XK_Num_Lock: Key.NUMLOCK,
           #SPACE: Key.SPACE,
           XK.XK_Tab: Key.TAB,
           XK.XK_Left: Key.LEFT,
           XK.XK_Right: Key.RIGHT,
           XK.XK_Up: Key.UP,
           XK.XK_Down: Key.DOWN,
           XK.XK_Return: Key.ENTER,
           XK.XK_BackSpace: Key.BACKSPACE,
           XK.XK_Scroll_Lock: Key.SCROLL_LOCK,
           XK.XK_Print: Key.PRINT_SCREEN,
           XK.XK_Pause: Key.PAUSE,
           XK.XK_Menu: Key.MENU,
           XK.XK_F1: Key.F1,
           XK.XK_F2: Key.F2,
           XK.XK_F3: Key.F3,
           XK.XK_F4: Key.F4,
           XK.XK_F5: Key.F5,
           XK.XK_F6: Key.F6,
           XK.XK_F7: Key.F7,
           XK.XK_F8: Key.F8,
           XK.XK_F9: Key.F9,
           XK.XK_F10: Key.F10,
           XK.XK_F11: Key.F11,
           XK.XK_F12: Key.F12,
           XK.XK_F13: Key.F13,
           XK.XK_F14: Key.F14,
           XK.XK_F15: Key.F15,
           XK.XK_F16: Key.F16,
           XK.XK_F17: Key.F17,
           XK.XK_F18: Key.F18,
           XK.XK_F19: Key.F19,
           XK.XK_F20: Key.F20,
           XK.XK_F21: Key.F21,
           XK.XK_F22: Key.F22,
           XK.XK_F23: Key.F23,
           XK.XK_F24: Key.F24,
           XK.XK_F25: Key.F25,
           XK.XK_F26: Key.F26,
           XK.XK_F27: Key.F27,
           XK.XK_F28: Key.F28,
           XK.XK_F29: Key.F29,
           XK.XK_F30: Key.F30,
           XK.XK_F31: Key.F31,
           XK.XK_F32: Key.F32,
           XK.XK_F33: Key.F33,
           XK.XK_F34: Key.F34,
           XK.XK_F35: Key.F35,
           XK.XK_Escape: Key.ESCAPE,
           XK.XK_Insert: Key.INSERT,
           XK.XK_Delete: Key.DELETE,
           XK.XK_Home: Key.HOME,
           XK.XK_End: Key.END,
           XK.XK_Page_Up: Key.PAGE_UP,
           XK.XK_Page_Down: Key.PAGE_DOWN,
           XK.XK_KP_Insert: Key.NP_INSERT,
           XK.XK_KP_Delete: Key.NP_DELETE,
           XK.XK_KP_End: Key.NP_END,
           XK.XK_KP_Down: Key.NP_DOWN,
           XK.XK_KP_Page_Down: Key.NP_PAGE_DOWN,
           XK.XK_KP_Left: Key.NP_LEFT,
           XK.XK_KP_Begin: Key.NP_5,
           XK.XK_KP_Right: Key.NP_RIGHT,
           XK.XK_KP_Home: Key.NP_HOME,
           XK.XK_KP_Up: Key.NP_UP,
           XK.XK_KP_Page_Up: Key.NP_PAGE_UP,
           XK.XK_KP_Divide: Key.NP_DIVIDE,
           XK.XK_KP_Multiply: Key.NP_MULTIPLY,
           XK.XK_KP_Add: Key.NP_ADD,
           XK.XK_KP_Subtract: Key.NP_SUBTRACT,
           XK.XK_KP_Enter: Key.ENTER,
           XK.XK_space: ' '
           }

AK_TO_XK_MAP = dict((v,k) for k, v in XK_TO_AK_MAP.items())

XK_TO_AK_NUMLOCKED = {
           XK.XK_KP_Insert: "0",
           XK.XK_KP_Delete: ".",
           XK.XK_KP_End: "1",
           XK.XK_KP_Down: "2",
           XK.XK_KP_Page_Down: "3",
           XK.XK_KP_Left: "4",
           XK.XK_KP_Begin: "5",
           XK.XK_KP_Right: "6",
           XK.XK_KP_Home: "7",
           XK.XK_KP_Up: "8",
           XK.XK_KP_Page_Up: "9",
           XK.XK_KP_Divide: "/",
           XK.XK_KP_Multiply: "*",
           XK.XK_KP_Add: "+",
           XK.XK_KP_Subtract: "-",
           XK.XK_KP_Enter: Key.ENTER
           }
