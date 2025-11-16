from gi.repository import Gtk
from hints.dbus import DBusHintsProxy
from hints.window_systems.window_system import WindowSystem
from hints.window_systems.gnome import Gnome
import os

def init_overlay_window(window: Gtk.Window,
                        window_system: WindowSystem,
                        x: int, y: int):
    g_win_sys: Gnome = window_system    # type: ignore
    monitor = g_win_sys.focused_window_monitor
    pid = os.getpid()
    dbus_proxy = DBusHintsProxy.get_instance()
    dbus_proxy.position_window(x, y, monitor, pid)
