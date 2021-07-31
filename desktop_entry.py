import os
from pathlib import Path
import importlib.resources as pkg_resources
import files


class DesktopEntry:
    _XDG_CONFIG_HOME = Path(os.environ.get('XDG_CONFIG_HOME', os.path.expanduser('~/.config')))
    _ENTRY_PATH = _XDG_CONFIG_HOME / 'autostart' / 'sifaka.desktop'

    def is_installed(self) -> bool:
        return self._ENTRY_PATH.exists()

    def install(self):
        desktop_entry_data = pkg_resources.read_binary(files, 'sifaka.desktop')
        self._ENTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
        with self._ENTRY_PATH.open('wb') as entry_file:
            entry_file.write(desktop_entry_data)

    def uninstall(self):
        self._ENTRY_PATH.unlink(missing_ok=True)
