import gi

gi.require_versions({"Gtk": "3.0", "Keybinder": "3.0", "Wnck": "3.0"})
from gi.repository import Gtk, Gdk


class WindowsSwitcherGui:

    def __init__(self):
        self._window = Gtk.Window()
        self._window.set_title('Quick Draw')
        self._window.set_decorated(False)
        self._window.set_resizable(False)
        self._window.stick()
        self._window.set_type_hint(Gdk.WindowTypeHint.DOCK)
        self._window.set_position(Gtk.WindowPosition.CENTER_ALWAYS)

        self._list_box = Gtk.ListBox()
        self._list_box.set_size_request(600, 50)
        self._window.add(self._list_box)

        self._windows = []

    def show(self, windows):
        self._windows = windows
        for window in self._windows:
            self._list_box.add(WindowListBoxRow(window.get_name(), window.get_workspace().get_name()))
        self._window.show_all()

    def close(self):
        for child in self._list_box.get_children()[::-1]:
            self._list_box.remove(child)
        self._window.close()

    def select(self, window):
        index = self._windows.index(window)
        self._list_box.select_row(self._list_box.get_children()[index])

    def remove(self, window):
        index = self._windows.index(window)
        self._windows.remove(window)
        self._list_box.remove(self._list_box.get_children()[index])


class WindowListBoxRow(Gtk.ListBoxRow):

    def __init__(self, window_name, workspace_name):
        super(Gtk.ListBoxRow, self).__init__()
        builder = Gtk.Builder()
        builder.add_from_file('ui/list-item.ui')

        list_item = builder.get_object('list-item')
        self.add(list_item)
        builder.get_object('label-window-name').set_label(window_name)
        builder.get_object('label-workspace-name').set_label(workspace_name)
