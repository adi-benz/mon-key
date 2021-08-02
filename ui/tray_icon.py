import gi

from configuration import Configuration
from desktop_entry import DesktopEntry
from key_binder import KeyBinder
from ui.main_window import MainWindow

gi.require_versions({"Gtk": "3.0", "AppIndicator3": "0.1"})
from gi.repository import Gtk, AppIndicator3


class TrayIcon:

    def __init__(self, configuration: Configuration, key_binder: KeyBinder):
        self._configuration = configuration
        self._key_binder = key_binder

    def show(self):
        self._indicator = AppIndicator3.Indicator.new('MonKey', str(DesktopEntry.ICON_PATH),
                                                      AppIndicator3.IndicatorCategory.SYSTEM_SERVICES)
        self._indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
        self._indicator.set_menu(self._build_app_indicator_menu())

    def _build_app_indicator_menu(self):
        menu = Gtk.Menu()
        configuration_item = Gtk.MenuItem(label='Configure hotkeys')
        configuration_item.connect('activate', self._open_main_window)
        menu.append(configuration_item)
        menu.append(Gtk.SeparatorMenuItem())
        quit_item = Gtk.MenuItem(label='Quit')
        quit_item.connect('activate', self._quit_app)
        menu.append(quit_item)
        menu.show_all()
        return menu

    def _open_main_window(self, _):
        MainWindow(self._configuration, self._key_binder).show()

    def _quit_app(self, _):
        Gtk.main_quit()
