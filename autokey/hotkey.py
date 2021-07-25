import dataclasses
from typing import List


@dataclasses.dataclass
class Hotkey:
    modifiers: List[str]
    key: str
