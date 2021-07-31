from gi.overrides import Gtk

from configuration import Configuration
from desktop_entry import DesktopEntry
from keys import Modifier


class PreferencesDialog:

    def __init__(self, configuration: Configuration):
        self._configuration = configuration
        self._desktop_entry = DesktopEntry()
        builder = Gtk.Builder()
        builder.add_from_file('ui/preferences-dialog.glade')

        self._dialog = builder.get_object('dialog')
        self._box_modifier_buttons = builder.get_object('box_modifierButtons')
        self._checkbox_startAtLogin = builder.get_object('checkbox_startAtLogin')
        self._checkbox_startAtLogin.connect('toggled', self._checkbox_startAtLogin_toggled)
        for modifier_button in self._box_modifier_buttons.get_children():
            modifier_button.connect('toggled', self._button_modifier_toggled)

        self._refresh_widgets()

    def _refresh_widgets(self):
        for modifier_button in self._box_modifier_buttons.get_children():
            if modifier_button.get_label().lower() == self._configuration.modifier().name.lower():
                modifier_button.set_active(True)
            else:
                modifier_button.set_active(False)

        self._box_modifier_buttons.show_all()

        self._checkbox_startAtLogin.set_active(self._desktop_entry.is_installed())

    def _checkbox_startAtLogin_toggled(self, _):
        if self._checkbox_startAtLogin.get_active():
            if not self._desktop_entry.is_installed():
                self._desktop_entry.install()
        else:
            if self._desktop_entry.is_installed():
                self._desktop_entry.uninstall()

    def _button_modifier_toggled(self, button):
        if self._count_active_modifier_buttons() == 0:
            button.set_active(True)

        if not button.get_active():
            return

        current_modifier = self._configuration.modifier()
        modifier = Modifier[button.get_label().upper()]
        if current_modifier == modifier:
            return

        print(f'modified {modifier.name}')
        self._configuration.set_modifier(modifier)

        self._refresh_widgets()

    def _count_active_modifier_buttons(self):
        return len([button for button in self._box_modifier_buttons.get_children() if button.get_active()])

    def run(self):
        self._dialog.run()
        self._dialog.destroy()
