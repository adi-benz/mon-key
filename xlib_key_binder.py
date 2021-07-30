import threading

import gi
from Xlib import X
from Xlib.display import Display
from Xlib.ext import record
from Xlib.protocol import rq

gi.require_versions({"Gtk": "3.0", "Keybinder": "3.0", "Wnck": "3.0"})
from gi.repository import Keybinder as XlibKeybinder
from gi.repository import GLib


class XlibKeyBinder:

    def __init__(self):
        self._hold_keys = {}
        self._display = Display()
        self._keys_bindings = []
        self._context = None

    def listen_hold(self, key, pressed_callback, released_callback):
        self._hold_keys[key] = (pressed_callback, released_callback)

    def clear_listen_hold(self):
        self._hold_keys.clear()

    def bind_to_keys(self, key_combination, pressed_callback, *args):
        bind_successful = XlibKeybinder.bind(key_combination, pressed_callback, *args)
        if bind_successful:
            self._keys_bindings.append(key_combination)
        return bind_successful

    def clear_bindings(self):
        for key_binding in self._keys_bindings:
            XlibKeybinder.unbind(key_binding)
        self._keys_bindings.clear()

    def start(self):
        XlibKeybinder.init()
        listener_thread = threading.Thread(target=self._start_hold_listen)
        listener_thread.setDaemon(True)
        listener_thread.start()

    def stop(self):
        self.clear_bindings()
        self.clear_listen_hold()
        self._display.record_disable_context(self._context)
        self._display.flush()

    def _start_hold_listen(self):
        self._context = self._display.record_create_context(
            0,
            [record.AllClients],
            [{
                'core_requests': (0, 0),
                'core_replies': (0, 0),
                'ext_requests': (0, 0, 0, 0),
                'ext_replies': (0, 0, 0, 0),
                'delivered_events': (0, 0),
                'device_events': (X.KeyReleaseMask, X.ButtonReleaseMask),
                'errors': (0, 0),
                'client_started': False,
                'client_died': False,
            }])
        self._display.record_enable_context(self._context, self._event_handler)
        self._display.record_free_context(self._context)
        self._display.close()

    def _event_handler(self, reply):
        data = reply.data
        while len(data):
            event, data = rq.EventField(None).parse_binary_value(data, self._display.display, None, None)

            keysym = self._display.keycode_to_keysym(event.detail, 0)

            if keysym in self._hold_keys.keys():
                pressed_callback, released_callback = self._hold_keys[keysym]
                if event.type == X.KeyPress:
                    if pressed_callback:
                        GLib.idle_add(pressed_callback)
                elif event.type == X.KeyRelease:
                    if released_callback:
                        GLib.idle_add(released_callback)
