from typing import Optional

import gi

import sifaka
from hotkey import Hotkey

gi.require_versions({"Gtk": "3.0", "Keybinder": "3.0", "Wnck": "3.0"})
from gi.repository import Gtk


class ConfigurationGui:

    def __init__(self):
        builder = Gtk.Builder()
        builder.add_from_file('ui/configuration-window.ui')

        self._window = builder.get_object('window_configuration')
        self._hotkeys_list_box = builder.get_object('listBox_hotkeys')
        self._button_add_hotkey = builder.get_object('button_addHotkey')
        self._button_add_hotkey.connect('clicked', self._button_add_hotkey_clicked)
        for i in range(10):
            for key, window_class_name in sifaka.KEY_BINDINGS.items():
                item = HotkeyListBoxRow(sifaka.MODIFIER, Hotkey(key, window_class_name))
                self._hotkeys_list_box.add(item)

    def show(self):
        self._window.show_all()

    def close(self):
        self._window.close()

    def _button_add_hotkey_clicked(self, _button):
        new_dialog = NewHotkeyDialog.new_hotkey()
        response = new_dialog.run()
        if response is not None:
            new_hotkey = response
            print(f'new hotkey, {new_hotkey.window_class_name}, {new_hotkey.key}')


class HotkeyListBoxRow(Gtk.ListBoxRow):

    def __init__(self, modifier: sifaka.Modifier, hotkey: Hotkey):
        super(Gtk.ListBoxRow, self).__init__()
        self._hotkey = hotkey
        builder = Gtk.Builder()
        builder.add_from_file('ui/configure-hotkey-list-item.ui')

        list_item = builder.get_object('list_item')
        self.add(list_item)
        builder.get_object('label_windowClassName').set_label(hotkey.window_class_name)
        builder.get_object('label_hotkeyDescription').set_label(modifier.string_value + '+' + hotkey.key)
        self._remove_button = builder.get_object('button_removeHotkey')
        self._remove_button.connect('clicked', self._button_remove_hotkey_clicked)
        self._button_edit_hotkey = builder.get_object('button_editHotkey')
        self._button_edit_hotkey.connect('clicked', self._button_edit_hotkey_clicked)

    def _button_edit_hotkey_clicked(self, _button):
        edit_dialog = NewHotkeyDialog.edit_hotkey(self._hotkey)
        response = edit_dialog.run()
        if response is not None:
            updated_hotkey = response
            print(f'new hotkey, {updated_hotkey.window_class_name}, {updated_hotkey.key}')

    def _button_remove_hotkey_clicked(self, button):
        pass


class NewHotkeyDialog:

    @classmethod
    def new_hotkey(cls):
        return NewHotkeyDialog()

    @classmethod
    def edit_hotkey(cls, hotkey: Hotkey):
        dialog = NewHotkeyDialog()
        dialog._entry_window_class_name.set_text(hotkey.window_class_name)
        dialog._entry_key.set_text(hotkey.key)
        dialog._button_confirm.set_label('Edit')
        return dialog

    def __init__(self):
        builder = Gtk.Builder()
        builder.add_from_file('ui/new-hotkey-dialog.ui')

        self._dialog = builder.get_object('dialog_newHotkey')
        self._button_confirm = builder.get_object('button_confirm')
        self._entry_window_class_name = builder.get_object('entry_windowClassName')
        self._entry_key = builder.get_object('entry_key')

        self._entry_window_class_name.connect('changed', self._evaluate_input_validity)
        self._entry_key.connect('changed', self._evaluate_input_validity)

    def run(self) -> Optional[Hotkey]:
        response = self._dialog.run()
        try:
            if response == Gtk.ResponseType.OK:
                return Hotkey(
                    self._entry_window_class_name.get_text(),
                    self._entry_key.get_text()
                )
            elif response == Gtk.ResponseType.CANCEL:
                return None
        finally:
            self._dialog.destroy()

    def _evaluate_input_validity(self, _):
        if len(self._entry_window_class_name.get_text().strip()) > 0 and len(self._entry_key.get_text().strip()) > 0:
            self._button_confirm.set_sensitive(True)
        else:
            self._button_confirm.set_sensitive(False)


if __name__ == '__main__':
    Gtk.init([])
    ConfigurationGui().show()
    Gtk.main()
