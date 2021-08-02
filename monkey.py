import faulthandler
from datetime import datetime
from typing import Optional

import gi

from configuration import Configuration
from key_binder import KeyBinder
from keylistener import KeyListener
from ui.tray_icon import TrayIcon
from window_manager import WindowManager
from windows_switcher import WindowsSwitcher

gi.require_versions({"Gtk": "3.0", "Wnck": "3.0"})
# noinspection PyUnresolvedReferences
from gi.repository import Gtk, Wnck, GdkX11, Gdk, GLib

faulthandler.enable()


class MonKey(KeyListener):

    def __init__(self):
        self._window_manager: WindowManager = WindowManager()
        self._window_manager.start()
        self._windows_switcher: Optional[WindowsSwitcher] = None
        self._configuration = Configuration()
        self._key_binder = KeyBinder(self._configuration, self)
        self._tray_icon = TrayIcon(self._configuration, self._key_binder)

    def start(self):
        self._tray_icon.show()
        Gtk.init([])

        self._key_binder.start()

        Gtk.main()
        self._key_binder.stop()

    def hotkey_pressed(self, keys: str, window_class_name: str):
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

    def modifier_down(self):
        print('_mod_down()')

    def modifier_up(self):
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

    def escape_pressed(self):
        if self._windows_switcher:
            self._windows_switcher.close()
            self._windows_switcher = None


def main():
    MonKey().start()


if __name__ == '__main__':
    main()
