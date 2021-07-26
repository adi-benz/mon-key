import abc


class HotkeyListener(abc.ABC):

    def handle_modifier_down(self, modifier: str):
        pass

    def handle_modifier_up(self, modifier: str):
        pass

    def handle_keypress(self, key):
        pass
