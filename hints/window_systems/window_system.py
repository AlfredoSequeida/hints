"""Linux window system."""

from __future__ import annotations

from typing import TYPE_CHECKING

from hints.window_systems.window_system_type import get_window_system_type

if TYPE_CHECKING:
    from hints.window_systems.window_system_type import WindowSystemType


class WindowSystem:
    """Linux base window system class."""

    @property
    def window_system_type(self) -> WindowSystemType:
        """Get window_sysetm_type.

        :return: The window system type.
        """
        return get_window_system_type()

    @property
    def window_system_name(self) -> str:
        """Get the name of the window syste.

        This is useful for performing logic specific to a window system.

        :return: The window system name
        """
        raise NotImplementedError()

    @property
    def focused_window_extents(self) -> tuple[int, int, int, int]:
        """Get active window extents.

        :return: Active window extents (x, y, width, height).
        """
        raise NotImplementedError()

    @property
    def focused_window_pid(self) -> int:
        """Get Process ID corresponding to the focused widnow.

        :return: Process ID of focused window.
        """
        raise NotImplementedError()

    @property
    def focused_applicaiton_name(self) -> str:
        """Get focused application name.

        This name is the name used to identify applications for per-
        application rules.

        :return: Focused application name.
        """
        raise NotImplementedError()
