from window_manager import WindowManager


class WindowsSwitcher:

    def __init__(self, window_manager: WindowManager):
        self._window_manager = window_manager
        self._class_name = None

    def start(self, class_name: str):
        self._class_name = class_name
        self._windows = list(self._window_manager.get_windows(self._class_name))
        for window in self._windows:
            print(f'\t{window.get_name()}')
        active_window = self._window_manager.get_active_window()
        if active_window.get_class_group_name() == class_name:
            self._index = 1
        else:
            self._index = 0

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
            return next_window
        except IndexError:
            raise StopIteration

    def refresh_windows(self):
        self._windows = [window for window in self._windows if self._window_manager.contains(window)]
