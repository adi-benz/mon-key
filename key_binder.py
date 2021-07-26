import threading

import gi
from Xlib import X
from Xlib.display import Display
from Xlib.ext import record
from Xlib.protocol import rq

from autokey.hotkey import Hotkey
from autokey.hotkey_listener import HotkeyListener
from autokey.interface import XRecordInterface
from autokey.key import Key

gi.require_versions({"Gtk": "3.0", "Keybinder": "3.0", "Wnck": "3.0"})
from gi.repository import GLib, Gdk


class Listener(HotkeyListener):
    def __init__(self, modifiers, keys, mod_down, mod_up, key_press):
        self._modifiers = set(modifiers)
        self._keys = keys
        self._mod_down = mod_down
        self._mod_up = mod_up
        self._key_press = key_press

        self._active_modifiers = set()

    def handle_modifier_down(self, modifier: Key):
        modifier = modifier.value
        if modifier not in self._active_modifiers:
            self._active_modifiers.add(modifier)
        self._mod_down(modifier)

    def handle_modifier_up(self, modifier: Key):
        modifier = modifier.value
        self._mod_up(modifier)
        if modifier in self._active_modifiers:
            self._active_modifiers.remove(modifier)
        print(f'modifier up: {modifier}')

    def handle_keypress(self, key):
        if key in self._keys and self._modifiers == self._active_modifiers:
            print(f'keypress: {key}')
            GLib.idle_add(self._key_press, key)


class KeyBinder:

    def __init__(self, modifiers, keys, mod_down, mod_up, key_press):
        self._modifiers = modifiers
        self._keys = keys
        self._display = Display()
        self._listener = Listener(modifiers, keys, mod_down, mod_up, key_press)
        hotkeys = [Hotkey(self._modifiers, key) for key in self._keys]
        self._interface = XRecordInterface(hotkeys, self._listener)

    def start(self):
        self._interface.initialise()
        self._interface.start()

