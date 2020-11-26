from window_manager import WindowManager
from windows_switcher_gui import WindowsSwitcherGui


class WindowsSwitcher:

    def __init__(self, window_manager: WindowManager):
        self._window_manager = window_manager
        self._class_name = None
        self._windows_switcher_gui = None
        self._index = 0
        self._windows = []

    def open(self, class_name: str):
        self._class_name = class_name
        self._windows = list(self._window_manager.get_windows(self._class_name))
        for window in self._windows:
            print(f'\t{window.get_name()}')
        active_window = self._window_manager.get_active_window()
        if any(self._windows):
            self._windows_switcher_gui = WindowsSwitcherGui()
            self._windows_switcher_gui.show(self._windows)
            self._index = 0
            if active_window and active_window.get_class_group_name() == class_name:
                self.select_next()

    def close(self):
        if self._windows_switcher_gui:
            self._windows_switcher_gui.close()

    def get_class_name(self):
        return self._class_name

    def select_next(self):
        # Some window might have been closed while switching windows
        self._refresh_windows()
        if not any(self._windows):
            raise KeyError('No more windows')
        has_reached_the_end = self._index + 1 >= len(self._windows)
        self._index = 0 if has_reached_the_end else self._index + 1
        self._select_current_window()

    def _select_current_window(self):
        next_window = self._windows[self._index]
        self._windows_switcher_gui.select(next_window)

    def selected_window(self):
        self._refresh_windows()
        if not any(self._windows):
            # All the windows were closed while we were active
            return None
        return self._windows[self._index]

    def _refresh_windows(self):
        new_windows = [window for window in self._windows if self._window_manager.contains(window)]
        removed_windows = set(self._windows) - set(new_windows)
        for window in removed_windows:
            self._windows_switcher_gui.remove(window)
        self._windows = new_windows
