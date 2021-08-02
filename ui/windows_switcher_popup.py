import gi

gi.require_versions({"Gtk": "3.0", "Keybinder": "3.0", "Wnck": "3.0"})
from gi.repository import Gtk, Gdk


class WindowsSwitcherPopup:

    def __init__(self):
        provider = Gtk.CssProvider()
        provider.load_from_path("ui/style.css")
        Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), provider,
                                                 Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        builder = Gtk.Builder()
        builder.add_from_file('ui/window-switcher-popup.glade')

        self._window = builder.get_object('popup-window')
        self._list_box = builder.get_object('windows-list')
        self._app_icon_image = builder.get_object('app-icon')
        self._app_name_label = builder.get_object('app-name')
        self._windows = []
        self._window.hide()

    def show(self, windows):
        self._windows = windows
        for window in self._windows:
            self._list_box.add(WindowListBoxRow(window.get_name(), window.get_workspace().get_name()))
        if any(self._windows):
            self._app_name_label.set_label(self._windows[0].get_class_group_name())
            app_icon = self._windows[0].get_icon()
            if app_icon:
                self._app_icon_image.set_from_pixbuf(app_icon)
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
        builder.add_from_file('ui/list-item.glade')

        list_item = builder.get_object('list-item')
        self.add(list_item)
        builder.get_object('label-window-name').set_label(window_name)
        builder.get_object('label-workspace-name').set_label(workspace_name)
