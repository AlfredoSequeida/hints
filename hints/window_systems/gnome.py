"""Linux window manger."""

# from gi import require_version
#
# require_version("Wnck", "3.0")
#
# from gi.repository import Wnck

from hints.window_systems.window_system import WindowSystem
from hints.dbus import DBusHintsProxy


class Gnome(WindowSystem):
    """GNOME (on Wayland)."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        dbus_proxy = DBusHintsProxy.get_instance()
        self.window_info: tuple[int, int, int, int, int, str, int] = \
                dbus_proxy.get_focused_window_info()

    @property
    def window_system_name(self) -> str:
        """Get the name of the window system.

        This is useful for performing logic specific to a window system.

        :return: The window system name
        """
        return "gnome"

    @property
    def focused_window_extents(self) -> tuple[int, int, int, int]:
        """Get active window extents.

        :return: Active window extents (x, y, width, height).
        """
        return self.window_info[:4]

    @property
    def focused_window_pid(self) -> int:
        """Get Process ID corresponding to the focused widnow.

        :return: Process ID of focused window.
        """
        return self.window_info[4]

    @property
    def focused_applicaiton_name(self) -> str:
        """Get focused application name.

        This name is the name used to identify applications for per-
        application rules.

        :return: Focused application name.
        """
        return self.window_info[5]

    @property
    def focused_window_monitor(self) -> int:
        """Get the index of the monitor the focused window occupies.

        :return: Monitor of focused window.
        """
        return self.window_info[6]

