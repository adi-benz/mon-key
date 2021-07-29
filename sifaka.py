import faulthandler
from datetime import datetime
from typing import Optional

import gi

import keys
from configuration import Configuration
from configuration_gui import ConfigurationGui
from key_binder import KeyBinder
from window_manager import WindowManager
from windows_switcher import WindowsSwitcher

gi.require_versions({"Gtk": "3.0", "Keybinder": "3.0", "Wnck": "3.0", "AppIndicator3": "0.1"})
# noinspection PyUnresolvedReferences
from gi.repository import Gtk, Wnck, GdkX11, Gdk, GLib
from gi.repository import AppIndicator3 as appindicator

faulthandler.enable()


class Sifaka:

    def __init__(self):
        self._screen = Wnck.Screen.get_default()
        self._screen.force_update()

        self._window_manager: WindowManager = WindowManager()
        self._window_manager.start()
        self._windows_switcher: Optional[WindowsSwitcher] = None

    def start(self):
        self._build_app_indicator()
        Gtk.init([])

        configuration = Configuration()
        self._keybinder = KeyBinder()
        self._keybinder.listen_hold(configuration.modifier().xk_value, self._mod_down, self._mod_up)
        self._keybinder.listen_hold(keys.ESC_KEY, self._esc_down, self._esc_up)

        for hotkey in configuration.hotkeys():
            hotkey_string = configuration.modifier().string_value + hotkey.key
            if not self._keybinder.bind_to_keys(hotkey_string, self._focus_window, hotkey.window_class_name):
                print(f'Failed binding key {hotkey_string} to open {hotkey.window_class_name}')

        self._keybinder.start()

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

    def _esc_down(self):
        if self._windows_switcher:
            self._windows_switcher.close()
            self._windows_switcher = None

    def _esc_up(self):
        pass

    def _build_app_indicator(self):
        self._indicator = appindicator.Indicator.new('sifaka', Gtk.STOCK_INFO,
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
        self._keybinder.stop()
        Gtk.main_quit()

    def _open_configuration_window(self, _):
        ConfigurationGui().show()


def main():
    Sifaka().start()


if __name__ == '__main__':
    main()
