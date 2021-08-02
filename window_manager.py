import logging
from collections import defaultdict

import gi
gi.require_versions({"Gtk": "3.0", "Keybinder": "3.0", "Wnck": "3.0"})
from gi.repository import Gtk, Wnck, Keybinder, GdkX11, Gdk


class WindowManager:

    def __init__(self):
        self._windows = defaultdict(list)
        self._screen = Wnck.Screen.get_default()
        self._screen.force_update()

    def start(self):
        self._screen.connect('active-window-changed', self._active_window_changed)
        self._screen.connect('window-opened', self._window_opened)
        self._screen.connect('window-closed', self._window_closed)

        for window in self._screen.get_windows():
            self._add_window(window)

    def get_active_window(self):
        return self._screen.get_active_window()

    def _window_opened(self, _, window):
        self._windows[window.get_class_group_name()].append(window)

    def _window_closed(self, _, window):
        try:
            self._windows[window.get_class_group_name()].remove(window)
        except ValueError:
            pass

    def _active_window_changed(self, screen, _):
        active_window = screen.get_active_window()
        if active_window:
            logging.debug(f'Focus changed to {active_window.get_name()}')
            self._add_window(active_window)

    def _add_window(self, window):
        class_name = window.get_class_group_name()
        try:
            self._windows[class_name].remove(window)
        except ValueError:
            pass
        self._windows[class_name].insert(0, window)

    def get_windows(self, class_name):
        return self._windows[class_name]

    def contains(self, window):
        return window in self._windows[window.get_class_group_name()]
