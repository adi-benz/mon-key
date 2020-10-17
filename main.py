from collections import defaultdict
from datetime import datetime

import gi

gi.require_versions({"Gtk": "3.0", "Keybinder": "3.0", "Wnck": "3.0"})
from gi.repository import Gtk, Wnck, Keybinder, GdkX11, Gdk


KEY_BINDINGS = {
    '<Hyper>w': 'google-chrome',
    '<Hyper>t': 'tilix',
    '<Hyper>c': 'jetbrains-pycharm-ce'
}


windows = defaultdict(list)


screen = Wnck.Screen.get_default()
screen.force_update()

my_window = Gtk.Window(title="Hello World")


def focus_window(keys, window_class_name):
    my_window.show()
    active_window = screen.get_active_window()
    for window in windows[window_class_name]:
        if window != active_window:
            window.activate(get_server_time())
            break

    print(f'{str(datetime.now())}: Focus {window_class_name}')


def get_windows_by_class_ordered(window_class_name):
    active_workspace = screen.get_active_workspace()
    all_windows = [window for window in screen.get_windows() if window.get_class_instance_name() == window_class_name]
    all_windows.sort(key=lambda window: window.get_workspace().get_number() == active_workspace.get_number(), reverse=True)

    return all_windows


def get_server_time():
    server_time = GdkX11.x11_get_server_time(Gdk.get_default_root_window())
    return server_time


def active_window_changed(_, active_window):
    print(active_window.get_name())
    class_name = active_window.get_class_instance_name()
    try:
        windows[class_name].remove(active_window)
    except ValueError:
        pass
    windows[class_name].insert(0, active_window)


def main():
    Gtk.init([])
    for window in screen.get_windows():
        active_window_changed(screen, window)

    screen.connect('active-window-changed', active_window_changed)
    for key_binding, window_class in KEY_BINDINGS.items():
        if not Keybinder.bind(key_binding, focus_window, window_class):
            print(f'Failed binding key {key_binding} to open {window_class}')
    Keybinder.init()

    Gtk.main()


if __name__ == '__main__':
    main()
