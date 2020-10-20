from window_manager import WindowManager
from windows_switcher_gui import WindowsSwitcherGui


class WindowsSwitcher:

    def __init__(self, window_manager: WindowManager):
        self._window_manager = window_manager
        self._windows_switcher_gui = WindowsSwitcherGui()
        self._class_name = None

    def start(self, class_name: str):
        self._class_name = class_name
        self._windows = list(self._window_manager.get_windows(self._class_name))
        for window in self._windows:
            print(f'\t{window.get_name()}')
        active_window = self._window_manager.get_active_window()
        if active_window and active_window.get_class_group_name() == class_name:
            self._index = 1
        else:
            self._index = 0
        self._windows_switcher_gui.show(self._windows)

    def stop(self):
        pass
        self._windows_switcher_gui.close()

    def get_class_name(self):
        return self._class_name

    def __iter__(self):
        return self

    def __next__(self):
        try:
            # Some window might have been closed while switching windows
            self.refresh_windows()
            next_window = self._windows[self._index]
            has_reached_the_end = self._index + 1 >= len(self._windows)
            self._index = 0 if has_reached_the_end else self._index + 1
            self._windows_switcher_gui.select(next_window)
            return next_window
        except IndexError:
            raise StopIteration

    def refresh_windows(self):
        new_windows = [window for window in self._windows if self._window_manager.contains(window)]
        removed_windows = set(self._windows) - set(new_windows)
        for window in removed_windows:
            self._windows_switcher_gui.remove(window)
        self._windows = new_windows
