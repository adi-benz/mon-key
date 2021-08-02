import faulthandler
import logging
import logging.handlers
import os
import sys
from datetime import datetime
from pathlib import Path
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
    _XDG_DATA_HOME = Path(os.environ.get('XDG_DATA_HOME', os.path.expanduser("~/.local/share"))) / 'MonKey'
    _LOG_PATH = _XDG_DATA_HOME / 'monkey.log'
    _LOG_FORMAT = "%(asctime)s %(levelname)s - %(name)s - %(message)s"

    def __init__(self):
        self._window_manager: WindowManager = WindowManager()
        self._window_manager.start()
        self._windows_switcher: Optional[WindowsSwitcher] = None
        self._configuration = Configuration()
        self._key_binder = KeyBinder(self._configuration, self)
        self._tray_icon = TrayIcon(self._configuration, self._key_binder)

    def start(self):
        self._initialize_logging()
        self._tray_icon.show()
        Gtk.init([])

        self._key_binder.start()

        Gtk.main()
        self._key_binder.stop()

    def _initialize_logging(self):
        logger = logging.getLogger()
        logger.setLevel(logging.NOTSET)

        self._LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(self._LOG_PATH,
                                                            maxBytes=5 * 1024 * 1024, backupCount=3)
        file_handler.setFormatter(logging.Formatter(self._LOG_FORMAT))
        file_handler.setLevel(logging.INFO)
        logger.addHandler(file_handler)

        stdout_handler = logging.StreamHandler(sys.stdout)
        stdout_handler.setFormatter(logging.Formatter(self._LOG_FORMAT))
        stdout_handler.setLevel(logging.DEBUG)
        logger.addHandler(stdout_handler)

    def hotkey_pressed(self, keys: str, window_class_name: str):
        logging.debug(f"{keys} binding pressed")
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
        pass

    def modifier_up(self):
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
