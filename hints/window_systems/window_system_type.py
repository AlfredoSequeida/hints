"""Window System Type module."""

from enum import Enum
from os import getenv
from typing import Literal

from hints.window_systems.exceptions import CouldNotIdentifyWindowSystemType


class WindowSystemType(Enum):
    """Window System types."""

    X11 = "x11"
    WAYLAND = "wayland"


SupportedWindowSystems = Literal["x11", "sway", "hyprland", "niri"]


def get_window_system_type() -> WindowSystemType:
    """Get the type of window system.

    :return: the type of window system.
    """

    xdg_session_type = getenv("XDG_SESSION_TYPE")

    if not xdg_session_type:
        raise CouldNotIdentifyWindowSystemType()

    # x11 does not always report as "x11", so if it's not wayland, we assume x11.
    return (
        WindowSystemType.WAYLAND
        if xdg_session_type == "wayland"
        else WindowSystemType.X11
    )
