"""Linux window manger."""

from gi import require_version

require_version("Wnck", "3.0")

from gi.repository import Wnck

from hints.window_systems.window_system import WindowSystem


class X11(WindowSystem):
    """Linux window manager class."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.screen = Wnck.Screen.get_default()
        self.screen.force_update()
        self.active_window = self.screen.get_active_window()

    @property
    def window_system_name(self) -> str:
        """Get the name of the window syste.

        This is useful for performing logic specific to a window system.

        :return: The window system name
        """
        return "x11"

    @property
    def focused_window_extents(self) -> tuple[int, int, int, int]:
        """Get active window extents.

        :return: Active window extents (x, y, width, height).
        """
        return self.active_window.get_client_window_geometry()

    @property
    def focused_window_pid(self) -> int:
        """Get Process ID corresponding to the focused widnow.

        :return: Process ID of focused window.
        """
        return self.active_window.get_pid()

    @property
    def focused_applicaiton_name(self) -> str:
        """Get focused application name.

        This name is the name used to identify applications for per-
        application rules.

        :return: Focused application name.
        """
        return self.active_window.get_class_instance_name()
