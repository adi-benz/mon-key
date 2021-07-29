from enum import Enum

from Xlib import XK

ESC_KEY = XK.XK_Escape


class Modifier(Enum):
    HYPER = (XK.XK_Hyper_L, '<Hyper>')
    SUPER = (XK.XK_Super_L, '<Super>')

    def __init__(self, xk_value, string_value):
        self.string_value = string_value
        self.xk_value = xk_value

