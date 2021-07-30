from Xlib import X, Xcursorfont
from Xlib.display import Display


def is_window_viewable(window):
    return window.get_attributes().win_class == X.InputOutput \
           and window.get_attributes().map_state == X.IsViewable


def is_window_has_state(window):
    return window.get_wm_state() is not None


def find_client_in_children(window):
    children = window.query_tree().children
    for window_child in children:
        if is_window_viewable(window) and is_window_has_state(window):
            return window_child

    for window_child in children:
        return find_client_in_children(window_child)

    return None


def find_client(window):
    if is_window_has_state(window):
        return window
    else:
        return find_client_in_children(window)


def choose_window_by_cursor():
    # Code taken from xprop source code:
    #   * https://github.com/tmathmeyer/xprop/blob/master/xprop.c
    #   * https://github.com/tmathmeyer/xprop/blob/b550e6eb074b6beb8817439f1e469175be5dc0d0/dsimple.c
    #   * https://github.com/tmathmeyer/xprop/blob/b550e6eb074b6beb8817439f1e469175be5dc0d0/clientwin.c
    d = Display()
    root = d.screen().root

    font = d.open_font('cursor')
    cursor = font.create_glyph_cursor(font, Xcursorfont.crosshair, Xcursorfont.crosshair + 1, (65535, 65535, 65535),
                                      (0, 0, 0))

    root.grab_pointer(False, X.ButtonPressMask | X.ButtonReleaseMask, X.GrabModeSync, X.GrabModeAsync, root, cursor,
                      X.CurrentTime)
    d.allow_events(X.SyncPointer, X.CurrentTime)
    event = root.display.next_event()

    d.ungrab_pointer(X.CurrentTime)
    d.flush()

    return find_client(event.child)
