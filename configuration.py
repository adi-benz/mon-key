import json
import os
from pathlib import Path
from typing import List

from hotkey import Hotkey
from keys import Modifier

DEFAULT_MODIFIER = Modifier.SUPER


class Configuration:
    _XDG_CONFIG_HOME = Path(os.environ.get('XDG_CONFIG_HOME', os.path.expanduser('~/.config')))
    _CONFIG_DIR = _XDG_CONFIG_HOME / "monkey"
    _HOTKEYS_FILE = _CONFIG_DIR / "hotkeys.json"

    def __init__(self):
        if not self._CONFIG_DIR.exists():
            self._CONFIG_DIR.mkdir(parents=True)

        if not self._HOTKEYS_FILE.exists():
            with self._HOTKEYS_FILE.open('w') as hotkeys_file:
                json.dump({
                    'modifier': DEFAULT_MODIFIER.name,
                    'hotkeys': []
                }, hotkeys_file)

    def modifier(self) -> Modifier:
        return Modifier[self._read_configuration()['modifier']]

    def hotkeys(self) -> List[Hotkey]:
        return [Hotkey(*x) for x in self._read_configuration()['hotkeys']]

    def set_modifier(self, new_modifier: Modifier):
        new_configuration = self._read_configuration()
        new_configuration['modifier'] = new_modifier.name
        with self._HOTKEYS_FILE.open('w') as hotkeys_file:
            json.dump(new_configuration, hotkeys_file)

    def add_hotkey(self, hotkey: Hotkey):
        updated_hotkeys = self.hotkeys()
        updated_hotkeys.append(hotkey)

        self._write_hotkeys(updated_hotkeys)

    def remove_hotkey(self, hotkey: Hotkey):
        updated_hotkeys = self.hotkeys()
        updated_hotkeys.remove(hotkey)

        self._write_hotkeys(updated_hotkeys)

    def edit_hotkey(self, hotkey: Hotkey, updated_hotkey: Hotkey):
        updated_hotkeys = self.hotkeys()
        updated_hotkeys[updated_hotkeys.index(hotkey)] = updated_hotkey

        self._write_hotkeys(updated_hotkeys)

    def _write_hotkeys(self, hotkeys: List[Hotkey]):
        updated_configuration = self._read_configuration()
        updated_configuration['hotkeys'] = [
            (x.key, x.window_class_name) for x in hotkeys
        ]

        with self._HOTKEYS_FILE.open('w') as hotkeys_file:
            json.dump(updated_configuration, hotkeys_file)

    def _read_configuration(self):
        with self._HOTKEYS_FILE.open('r') as hotkeys_file:
            return json.load(hotkeys_file)
