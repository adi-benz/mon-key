import faulthandler
from datetime import datetime
from typing import Optional

import gi

from configuration import Configuration
from ui.main_window import MainWindow
from desktop_entry import DesktopEntry
from key_binder import KeyBinder
from keylistener import KeyListener
from window_manager import WindowManager
from windows_switcher import WindowsSwitcher

gi.require_versions({"Gtk": "3.0", "Keybinder": "3.0", "Wnck": "3.0", "AppIndicator3": "0.1"})
# noinspection PyUnresolvedReferences
from gi.repository import Gtk, Wnck, GdkX11, Gdk, GLib
from gi.repository import AppIndicator3 as appindicator

faulthandler.enable()


class MonKey(KeyListener):

    def __init__(self):
        self._screen = Wnck.Screen.get_default()
        self._screen.force_update()

        self._window_manager: WindowManager = WindowManager()
        self._window_manager.start()
        self._windows_switcher: Optional[WindowsSwitcher] = None
        self._configuration = Configuration()
        self._key_binder = KeyBinder(self._configuration, self)

    def start(self):
        self._build_app_indicator()
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

    def _build_app_indicator(self):
        self._indicator = appindicator.Indicator.new('MonKey', str(DesktopEntry.ICON_PATH),
                                                     appindicator.IndicatorCategory.SYSTEM_SERVICES)
        self._indicator.set_status(appindicator.IndicatorStatus.ACTIVE)
        self._indicator.set_menu(self._build_app_indicator_menu())

    def _build_app_indicator_menu(self):
        menu = Gtk.Menu()
        configuration_item = Gtk.MenuItem(label='Configure hotkeys')
        configuration_item.connect('activate', self._open_configuration_window)
        menu.append(configuration_item)
        menu.append(Gtk.SeparatorMenuItem())
        quit_item = Gtk.MenuItem(label='Quit')
        quit_item.connect('activate', self._quit_app)
        menu.append(quit_item)
        menu.show_all()
        return menu

    def _quit_app(self, _):
        Gtk.main_quit()

    def _open_configuration_window(self, _):
        MainWindow(self._configuration, self._key_binder).show()


def main():
    MonKey().start()


if __name__ == '__main__':
    main()
