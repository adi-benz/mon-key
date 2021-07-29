import keys
from configuration import Configuration
from keylistener import KeyListener
from xlib_key_binder import XlibKeyBinder


class KeyBinder:
    def __init__(self, configuration: Configuration, key_listener: KeyListener):
        self._configuration = configuration
        self._key_listener = key_listener
        self._xkey_binder = XlibKeyBinder()

    def start(self):
        self._xkey_binder.start()
        self.reload_bindings()

    def stop(self):
        self._xkey_binder.stop()

    def reload_bindings(self):
        self._xkey_binder.clear_listen_hold()
        self._xkey_binder.clear_bindings()

        modifier = self._configuration.modifier()
        self._xkey_binder.listen_hold(modifier.xk_value,
                                      self._key_listener.modifier_down, self._key_listener.modifier_up)
        self._xkey_binder.listen_hold(keys.ESC_KEY, self._key_listener.escape_pressed, lambda: None)

        for hotkey in self._configuration.hotkeys():
            hotkey_string = modifier.string_value + hotkey.key
            print(f'Binding key {hotkey_string} to open {hotkey.window_class_name}')
            if not self._xkey_binder.bind_to_keys(hotkey_string, self._key_listener.hotkey_pressed,
                                                  hotkey.window_class_name):
                print(f'Failed binding key {hotkey_string} to open {hotkey.window_class_name}')

