import os
from pathlib import Path
import importlib.resources as pkg_resources
import files


class DesktopEntry:
    _DESKTOP_ENTRY_NAME = 'mon-key.desktop'

    _XDG_CONFIG_HOME = Path(os.environ.get('XDG_CONFIG_HOME', os.path.expanduser('~/.config')))
    _ENTRY_PATH = _XDG_CONFIG_HOME / 'autostart' / _DESKTOP_ENTRY_NAME

    _FILES_PATH = Path(__file__).parent / 'files'
    ICON_PATH = _FILES_PATH / 'monkey-head.png'
    _SCRIPT_PATH = _FILES_PATH / 'monkey_run.sh'

    def is_installed(self) -> bool:
        return self._ENTRY_PATH.exists()

    def install(self):
        desktop_entry_data = pkg_resources.read_text(files, self._DESKTOP_ENTRY_NAME)
        desktop_entry_data = desktop_entry_data.format(exec=str(self._SCRIPT_PATH), icon=str(self.ICON_PATH))
        self._ENTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
        with self._ENTRY_PATH.open('w') as entry_file:
            entry_file.write(desktop_entry_data)

    def uninstall(self):
        self._ENTRY_PATH.unlink(missing_ok=True)
