from gi.repository import Gtk
from hints.dbus import DBusHintsProxy
from hints.window_systems.window_system import WindowSystem
from hints.window_systems.gnome import Gnome
from hints.huds.interceptor import InterceptorWindow
from hints.huds.overlay import OverlayWindow

def init_overlay_window(window: Gtk.Window,
                        window_system: WindowSystem,
                        x: int, y: int):
    if window is OverlayWindow:
        title = "Overlay"
    elif window is InterceptorWindow:
        title = "Interceptor"
    else:
        title = "Hints"
    window.set_title(title)
    g_win_sys: Gnome = window_system    # type: ignore
    monitor = g_win_sys.focused_window_monitor
    pid = g_win_sys.focused_window_pid
    dbus_proxy = DBusHintsProxy.get_instance()
    dbus_proxy.position_window(x, y, monitor, pid, title)
