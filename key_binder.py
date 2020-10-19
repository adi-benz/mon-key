import threading

from Xlib.display import Display
from Xlib import X
from Xlib.ext import record
from Xlib.protocol import rq


class KeyBinder:

    def __init__(self):
        self._hold_keys = {}
        self._display = Display()

    def listen_hold(self, key, pressed_callback, released_callback):
        self._hold_keys[key] = (pressed_callback, released_callback)

    def listen_key_press(self, key, pressed_callback):
        self._hold_keys[ord(key)] = (pressed_callback, None)

    def start(self):
        threading.Thread(target=self.run).start()

    def run(self):
        context = self._display.record_create_context(
            0,
            [record.AllClients],
            [{
                'core_requests': (0, 0),
                'core_replies': (0, 0),
                'ext_requests': (0, 0, 0, 0),
                'ext_replies': (0, 0, 0, 0),
                'delivered_events': (0, 0),
                'device_events': (X.KeyReleaseMask, X.ButtonReleaseMask),
                'errors': (0, 0),
                'client_started': False,
                'client_died': False,
            }])
        self._display.record_enable_context(context, self._event_handler)
        self._display.record_free_context(context)

    def _event_handler(self, reply):
        data = reply.data
        while len(data):
            event, data = rq.EventField(None).parse_binary_value(data, self._display.display, None, None)

            keysym = self._display.keycode_to_keysym(event.detail, 0)
            # print(event.detail, keysym)
            if keysym in self._hold_keys.keys():
                pressed_callback, released_callback = self._hold_keys[keysym]
                if event.type == X.KeyPress:
                    if pressed_callback:
                        pressed_callback()
                elif event.type == X.KeyRelease:
                    if released_callback:
                        released_callback()
