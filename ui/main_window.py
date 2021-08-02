from typing import Optional


import xlocate_window
from configuration import Configuration
from .preferences_dialog import PreferencesDialog
from hotkey import Hotkey
from key_binder import KeyBinder

import gi
gi.require_versions({"Gtk": "3.0"})
from gi.repository import Gtk


class MainWindow:

    def __init__(self, configuration: Configuration, key_binder: KeyBinder):
        self._configuration = configuration
        self._key_binder = key_binder
        builder = Gtk.Builder()
        builder.add_from_file('ui/glade_files/main-window.glade')

        self._window = builder.get_object('main_window')
        self._button_preferences = builder.get_object('button_preferences')
        self._button_preferences.connect('clicked', self._open_preferences)
        self._hotkeys_list_box = builder.get_object('listBox_hotkeys')
        self._button_add_hotkey = builder.get_object('button_addHotkey')
        self._button_add_hotkey.connect('clicked', self._button_add_hotkey_clicked)
        self._menu_item_about = builder.get_object('menuItem_about')
        self._menu_item_about.connect('activate', self._menu_item_about_activate)
        self._menu_item_quit = builder.get_object('menuItem_quit')
        self._menu_item_quit.connect('activate', self._menu_item_quit_activate)

        self._reload_hotkeys_listbox()

    def _show_hotkey(self, hotkey):
        item = HotkeyListBoxRow(self._configuration, hotkey, self._hotkey_updated, self._hotkey_removed)
        self._hotkeys_list_box.add(item)
        item.show_all()

    def show(self):
        self._window.show_all()

    def close(self):
        self._window.close()

    def _open_preferences(self, _):
        dialog = PreferencesDialog(self._configuration, self._key_binder)
        dialog.run()

    def _button_add_hotkey_clicked(self, _button):
        new_dialog = EditHotkeyDialog.new_hotkey()
        response = new_dialog.run()
        if response is not None:
            new_hotkey = response
            print(f'New hotkey, {new_hotkey.window_class_name}, {new_hotkey.key}')
            self._configuration.add_hotkey(new_hotkey)
            self._reload_hotkeys()

    def _hotkey_updated(self, hotkey: Hotkey, updated_hotkey: Hotkey):
        self._configuration.edit_hotkey(hotkey, updated_hotkey)
        self._reload_hotkeys()

    def _hotkey_removed(self, hotkey: Hotkey):
        self._configuration.remove_hotkey(hotkey)
        self._reload_hotkeys()

    def _reload_hotkeys(self):
        self._reload_hotkeys_listbox()
        self._key_binder.reload_bindings()

    def _reload_hotkeys_listbox(self):
        self._clear_hotkeys_list()
        for hotkey in self._configuration.hotkeys():
            self._show_hotkey(hotkey)
        self._hotkeys_list_box.show_all()

    def _clear_hotkeys_list(self):
        for child in self._hotkeys_list_box.get_children():
            self._hotkeys_list_box.remove(child)

    def _menu_item_about_activate(self, _):
        builder = Gtk.Builder()
        builder.add_from_file('ui/glade_files/about-dialog.glade')
        dialog = builder.get_object("dialog")
        dialog.run()
        dialog.destroy()

    def _menu_item_quit_activate(self, _):
        Gtk.main_quit()


class HotkeyListBoxRow(Gtk.ListBoxRow):

    def __init__(self, configuration, hotkey: Hotkey, edit_callback, remove_callback):
        super(Gtk.ListBoxRow, self).__init__()
        self._configuration = configuration
        self._hotkey = hotkey
        self._remove_callback = remove_callback
        self._edit_callback = edit_callback
        builder = Gtk.Builder()
        builder.add_from_file('ui/glade_files/configure-hotkey-list-item.glade')

        list_item = builder.get_object('list_item')
        self.add(list_item)

        self._label_windowClassName = builder.get_object('label_windowClassName')
        self._label_hotkeyDescription = builder.get_object('label_hotkeyDescription')
        self._remove_button = builder.get_object('button_removeHotkey')
        self._remove_button.connect('clicked', self._button_remove_hotkey_clicked)
        self._button_edit_hotkey = builder.get_object('button_editHotkey')
        self._button_edit_hotkey.connect('clicked', self._button_edit_hotkey_clicked)

        self._change_hotkey(hotkey)

    def _change_hotkey(self, hotkey):
        self._hotkey = hotkey
        self._label_windowClassName.set_label(self._hotkey.window_class_name)
        self._label_hotkeyDescription.set_label(self._configuration.modifier().string_value + '+' + hotkey.key)

    def _button_edit_hotkey_clicked(self, _button):
        edit_dialog = EditHotkeyDialog.edit_hotkey(self._hotkey)
        response = edit_dialog.run()
        if response is not None:
            updated_hotkey = response
            print(f'Hotkey edit, {updated_hotkey.window_class_name}, {updated_hotkey.key}')
            self._edit_callback(self._hotkey, updated_hotkey)

    def _button_remove_hotkey_clicked(self, _button):
        self._remove_callback(self._hotkey)


class EditHotkeyDialog:

    @classmethod
    def new_hotkey(cls):
        dialog = EditHotkeyDialog()
        dialog._dialog.set_title('New hotkey')
        dialog._button_confirm.set_label('Create')
        return dialog

    @classmethod
    def edit_hotkey(cls, hotkey: Hotkey):
        dialog = EditHotkeyDialog()
        dialog._dialog.set_title('Edit hotkey')
        dialog._entry_window_class_name.set_text(hotkey.window_class_name)
        dialog._entry_key.set_text(hotkey.key)
        dialog._button_confirm.set_label('Save')
        return dialog

    def __init__(self):
        builder = Gtk.Builder()
        builder.add_from_file('ui/glade_files/edit-hotkey-dialog.glade')

        self._dialog = builder.get_object('dialog_editHotkey')
        self._button_confirm = builder.get_object('button_confirm')
        self._button_locate = builder.get_object('button_locate')
        self._button_locate.connect('clicked', self._locate_window)
        self._entry_window_class_name = builder.get_object('entry_windowClassName')
        self._entry_key = builder.get_object('entry_key')

        self._entry_window_class_name.connect('changed', self._evaluate_input_validity)
        self._entry_key.connect('changed', self._evaluate_input_validity)

    def run(self) -> Optional[Hotkey]:
        response = self._dialog.run()
        try:
            if response == Gtk.ResponseType.OK:
                return Hotkey(
                    self._entry_key.get_text(),
                    self._entry_window_class_name.get_text()
                )
            elif response == Gtk.ResponseType.CANCEL:
                return None
        finally:
            self._dialog.destroy()

    def _locate_window(self, _):
        chosen_window = xlocate_window.choose_window_by_cursor()

        chosen_window_class_name = chosen_window.get_wm_class()
        if chosen_window_class_name:
            self._entry_window_class_name.set_text(chosen_window_class_name[0])
            self._entry_window_class_name.show_all()

    def _evaluate_input_validity(self, _):
        if len(self._entry_window_class_name.get_text().strip()) > 0 and len(self._entry_key.get_text().strip()) > 0:
            self._button_confirm.set_sensitive(True)
        else:
            self._button_confirm.set_sensitive(False)
