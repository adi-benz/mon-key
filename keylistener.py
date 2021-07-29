import abc
from abc import ABC


class KeyListener(ABC):

    @abc.abstractmethod
    def modifier_down(self):
        pass

    @abc.abstractmethod
    def modifier_up(self):
        pass

    @abc.abstractmethod
    def escape_pressed(self):
        pass

    @abc.abstractmethod
    def hotkey_pressed(self, keys: str, window_class_name: str):
        pass
