from gi.repository import Gio, GLib
from typing import Optional

class DBusHintsProxy:
    _instance = None
    _proxy : Optional[Gio.DBusProxy] = None

    def __init__(self):
        if DBusHintsProxy._proxy is None:
            proxy = Gio.DBusProxy.new_for_bus_sync(
                    bus_type = Gio.BusType.SESSION,
                    flags = Gio.DBusProxyFlags.NONE,
                    info = None,
                    name = "uk.co.realh.Hints",
                    object_path = "/uk/co/realh/Hints",
                    interface_name = "uk.co.realh.Hints"
                )
            DBusHintsProxy._proxy = proxy   # type: ignore
        else:
            proxy = DBusHintsProxy._proxy
        self.proxy: Gio.DBusProxy = proxy   # type: ignore

    def get_focused_window_info(self) \
            -> tuple[int, int, int, int, int, str, int]:
        """ Returns x, y, width, height, pid, name, monitor. """
        return self.proxy.call_sync(
                    method_name = "FocusedWindowInfo",
                    parameters = None,
                    flags = Gio.DBusCallFlags.NONE,
                    timeout_msec = -1,
                    cancellable = None
                )   # type: ignore

    def position_window(self, x, y, monitor, pid):
        self.proxy.call_sync(
                    method_name = "PositionWindow",
                    parameters = GLib.Variant.new_tuple(
                        GLib.Variant.new_int32(x),
                        GLib.Variant.new_int32(y),
                        GLib.Variant.new_int32(monitor),
                        GLib.Variant.new_int32(pid),
                    ),
                    flags = Gio.DBusCallFlags.NONE,
                    timeout_msec = 5,
                    cancellable = None
                )

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = DBusHintsProxy()
        return cls._instance
