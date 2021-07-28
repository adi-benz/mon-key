import gi

import sifaka

gi.require_versions({"Gtk": "3.0", "Keybinder": "3.0", "Wnck": "3.0"})
from gi.repository import Gtk


class ConfigurationGui:

    def __init__(self):
        builder = Gtk.Builder()
        builder.add_from_file('ui/configuration-window.ui')

        self._window = builder.get_object('window_configuration')
        self._hotkeys_list_box = builder.get_object('listBox_hotkeys')
        for i in range(10):
            for hotkey, window_class_name in sifaka.KEY_BINDINGS.items():
                item = HotkeyListBoxRow(hotkey, window_class_name)
                self._hotkeys_list_box.add(item)

    def show(self):
        self._window.show_all()

    def close(self):
        self._window.close()


class HotkeyListBoxRow(Gtk.ListBoxRow):

    def __init__(self, hotkey: str, window_class_name: str):
        super(Gtk.ListBoxRow, self).__init__()
        builder = Gtk.Builder()
        builder.add_from_file('ui/configure-hotkey-list-item.ui')

        list_item = builder.get_object('list_item')
        self.add(list_item)
        builder.get_object('label_windowClassName').set_label(window_class_name)
        builder.get_object('label_hotkeyDescription').set_label(hotkey)


if __name__ == '__main__':
    Gtk.init([])
    ConfigurationGui().show()
    Gtk.main()
