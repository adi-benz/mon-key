from dataclasses import dataclass


@dataclass
class Hotkey:
    key: str
    window_class_name: str
