from datetime import datetime
from enum import Enum
from typing import Optional

import gi
import faulthandler
from Xlib import XK

from key_binder import KeyBinder
from window_manager import WindowManager
from windows_switcher import WindowsSwitcher

gi.require_versions({"Gtk": "3.0", "Keybinder": "3.0", "Wnck": "3.0"})
# noinspection PyUnresolvedReferences
from gi.repository import Gtk, Wnck, GdkX11, Gdk, GLib

faulthandler.enable()


class Modifier(Enum):
    HYPER = (XK.XK_Hyper_L, '<Hyper>')
    SUPER = (XK.XK_Super_L, '<Super>')

    def __init__(self, xk_value, string_value):
        self.string_value = string_value
        self.xk_value = xk_value


MODIFIER = Modifier.HYPER
KEY_BINDINGS = {
    'w': 'Google-chrome',
    't': 'Tilix',
    'c': 'jetbrains-pycharm-ce',
    'q': 'okular',
    'o': 'jetbrains-clion',
}


class Sifaka:

    def __init__(self):
        self._screen = Wnck.Screen.get_default()
        self._screen.force_update()

        self._window_manager: WindowManager = WindowManager()
        self._window_manager.start()
        self._windows_switcher: Optional[WindowsSwitcher] = None

    def start(self):
        Gtk.init([])

        keybinder = KeyBinder()

        keybinder.listen_hold(MODIFIER.xk_value, self._mod_down, self._mod_up)

        for key_binding, window_class in KEY_BINDINGS.items():
            hotkey = MODIFIER.string_value + key_binding
            if not keybinder.bind_to_keys(hotkey, self._focus_window, window_class):
                print(f'Failed binding key {key_binding} to open {window_class}')

        keybinder.start()

        Gtk.main()

    def _focus_window(self, keys, window_class_name):
        print(f"{keys} binding pressed")
        if not self._windows_switcher:
            self._create_window_switcher(window_class_name)
        elif self._windows_switcher.get_class_name() != window_class_name:
            self._windows_switcher.close()
            self._create_window_switcher(window_class_name)
        else:
            try:
                self._windows_switcher.select_next()
            except KeyError:
                self._close_windows_switcher()

    def _create_window_switcher(self, window_class_name):
        self._windows_switcher = WindowsSwitcher(self._window_manager)
        self._windows_switcher.open(window_class_name)

    def _get_server_time(self):
        server_time = GdkX11.x11_get_server_time(Gdk.get_default_root_window())
        return server_time

    def _mod_down(self):
        print('_mod_down()')

    def _mod_up(self):
        print('_mod_up()')
        if not self._windows_switcher:
            return

        selected_window = self._windows_switcher.selected_window()
        self._close_windows_switcher()

        if selected_window:
            GLib.idle_add(self._activate_window, selected_window)

    def _activate_window(self, window):
        window.activate(self._get_server_time())
        print(f'\t{str(datetime.now())}: Focus {window.get_class_group_name()}: {window.get_name()}')

    def _close_windows_switcher(self):
        if self._windows_switcher:
            self._windows_switcher.close()
        self._windows_switcher = None


def main():
    Sifaka().start()


if __name__ == '__main__':
    main()
