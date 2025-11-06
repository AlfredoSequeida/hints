from __future__ import annotations

import logging
from argparse import ArgumentParser
from itertools import product
from math import ceil, log
from subprocess import run
from time import time
from typing import TYPE_CHECKING, Any, Iterable, Type, get_args

from gi import require_version

from hints.backends.atspi import AtspiBackend
from hints.backends.exceptions import AccessibleChildrenNotFoundError
from hints.backends.opencv import OpenCV
from hints.huds.interceptor import InterceptorWindow
from hints.huds.overlay import OverlayWindow
from hints.mouse import click
from hints.mouse_enums import MouseButton, MouseButtonState
from hints.utils import HintsConfig, load_config
from hints.window_systems.exceptions import WindowSystemNotSupported
from hints.window_systems.window_system import WindowSystem
from hints.window_systems.window_system_type import (
    SupportedWindowSystems,
    WindowSystemType,
    get_window_system_type,
)

if TYPE_CHECKING:
    from hints.child import Child
    from hints.window_systems.window_system import WindowSystem


logger = logging.getLogger(__name__)


require_version("Gtk", "3.0")
require_version("Gdk", "3.0")
from gi.repository import Gdk, Gtk


def display_gtk_window(
    window_system: WindowSystem,
    gtk_window: Gtk.Window,
    x: int,
    y: int,
    width: int,
    height: int,
    gkt_window_args: Iterable[Any] | None = None,
    gtk_window_kwargs: dict[str, Any] | None = None,
    overlay_x_offset: int = 0,
    overlay_y_offset: int = 0,
):
    """Setup and Display gtk window.

    :param window_system: The window system.
    :param gtk_window: The Gtk Window class to display.
    :param x: X position for window.
    :param y: Y position for window.
    :param width: Width for window.
    :param height: Height for window.
    :param gkt_window_args: The positional argument for the window
        instance.
    :param gtk_widnow_kwargs: The keyword arguments for the window
        instance.
    :param overlay_x_offset: X offset position for the window.
    :param overlay_y_offset: Y offset position for the window.
    """

    window_x_pos = x + overlay_x_offset
    window_y_pos = y + overlay_y_offset

    window = gtk_window(
        window_x_pos,
        window_y_pos,
        width,
        height,
        *(gkt_window_args or []),
        **(gtk_window_kwargs or {}),
    )

    if window_system.window_system_name == "gnome":
        from hints.gnome_overlay import init_overlay_window
        init_overlay_window(window, window_system, window_x_pos, window_y_pos)
    if window_system.window_system_type == WindowSystemType.WAYLAND:
        require_version("GtkLayerShell", "0.1")
        from gi.repository import GtkLayerShell

        GtkLayerShell.init_for_window(window)

        # On sway (unknow about other wayland compositors as of now), the
        # compositor cannot be relied on to put a window on the correct monitor,
        # so we are setting the monitor and treating the window as relative to
        # that monitor to position hints.
        expected_monitor = Gdk.Display.get_monitor_at_point(
            Gdk.Display.get_default(), window_x_pos, window_y_pos
        )
        expected_monitor_geometry = expected_monitor.get_geometry()
        GtkLayerShell.set_monitor(window, expected_monitor)

        GtkLayerShell.set_margin(
            window, GtkLayerShell.Edge.LEFT, window_x_pos - expected_monitor_geometry.x
        )
        GtkLayerShell.set_margin(
            window, GtkLayerShell.Edge.TOP, window_y_pos - expected_monitor_geometry.y
        )
        GtkLayerShell.set_anchor(window, GtkLayerShell.Edge.TOP, True)
        GtkLayerShell.set_anchor(window, GtkLayerShell.Edge.LEFT, True)
        GtkLayerShell.set_layer(window, GtkLayerShell.Layer.OVERLAY)
        GtkLayerShell.set_keyboard_mode(window, GtkLayerShell.KeyboardMode.EXCLUSIVE)
        GtkLayerShell.set_namespace(
            window, "hints"
        )  # Allows for compositor layer rules

    window.show_all()
    Gtk.main()


def get_hints(children: list[Child], alphabet: str) -> dict[str, Child]:
    """Get hints.

    :param children: The children elements of windown that indicate the
        absolute position of those elements.
    :param alphabet: The alphabet used to create hints
    :return: The hints. Ex {"ab": Child, "ac": Child}
    """
    hints: dict[str, Child] = {}

    if len(children) == 0:
        return hints

    for child, hint in zip(
        children,
        product(alphabet, repeat=ceil(log(len(children)) / log(len(alphabet)))),
    ):
        hints["".join(hint)] = child

    return hints


def hint_mode(config: HintsConfig, window_system: WindowSystem):
    """Hint mode to interact with hints on screen.

    :param config: Hints config.
    :param window_system: Window System for the session.
    :param mouse: Mouse device for mouse actions.
    """
    window_extents = None
    hints = {}

    backends_map = {"atspi": AtspiBackend, "opencv": OpenCV}
    backends = config["backends"]["enable"]

    for backend in backends:

        start = time()
        current_backend = backends_map[backend](config, window_system)
        logger.debug(
            "Attempting to get accessible children using the '%s' backend.",
            backend,
        )
        try:
            children = current_backend.get_children()

            logger.debug("Gathering hints took %f seconds", time() - start)
            logger.debug("Gathered %d hints", len(children))

            hints = get_hints(
                children,
                alphabet=config["alphabet"],
            )

            window_extents = current_backend.window_system.focused_window_extents

        except AccessibleChildrenNotFoundError:
            logger.debug(
                "No acceessible children found with the '%s' backend.",
                backend,
            )

        if window_extents and hints:
            mouse_action: dict[str, Any] = {}
            x, y, width, height = window_extents

            display_gtk_window(
                window_system,
                OverlayWindow,
                x,
                y,
                width,
                height,
                gkt_window_args=(
                    config,
                    hints,
                    mouse_action,
                ),
                gtk_window_kwargs={
                    "is_wayland": window_system.window_system_type
                    == WindowSystemType.WAYLAND,
                },
                overlay_x_offset=config["overlay_x_offset"],
                overlay_y_offset=config["overlay_y_offset"],
            )

            if mouse_action:

                mouse_x_offset = 0
                mouse_y_offset = 0

                match window_system.window_system_name:
                    case "sway":
                        mouse_y_offset = window_system.bar_height

                logger.debug("performing '%s'", mouse_action)

                match mouse_action["action"]:
                    case "click":
                        click(
                            mouse_action["x"] + mouse_x_offset,
                            mouse_action["y"] + mouse_y_offset,
                            mouse_action["button"],
                            (MouseButtonState.DOWN, MouseButtonState.UP),
                            mouse_action["repeat"],
                        )
                    case "hover":
                        click(
                            mouse_action["x"] + mouse_x_offset,
                            mouse_action["y"] + mouse_y_offset,
                            MouseButton.LEFT,
                            (),
                        )
                    case "grab":
                        click(
                            mouse_action["x"] + mouse_x_offset,
                            mouse_action["y"] + mouse_y_offset,
                            MouseButton.LEFT,
                            (MouseButtonState.DOWN,),
                        )

                        display_gtk_window(
                            window_system,
                            InterceptorWindow,
                            x,
                            y,
                            1,
                            1,
                            gkt_window_args=({"action": "grab"}, config),
                            gtk_window_kwargs={
                                "is_wayland": window_system.window_system_type
                                == WindowSystemType.WAYLAND,
                            },
                        )

            # no need to use the next backend if the current one succeeded
            break


def get_window_system_class(
    window_system_id: SupportedWindowSystems | str,
) -> Type[WindowSystem] | None:
    """Get the window system class for the window system id.

    :param window_system_id: A string identifying the supported window
        system.
    :return: The window system class.
    """

    window_system: Type[WindowSystem] | None = None

    match window_system_id:
        case "x11":
            from hints.window_systems.x11 import X11 as window_system
        case "sway":
            from hints.window_systems.sway import Sway as window_system
        case "hyprland":
            from hints.window_systems.hyprland import Hyprland as window_system
        case "plasmashell":
            from hints.window_systems.plasmashell import Plasmashell as window_system
        case "gnome-shell":
            from hints.window_systems.gnome import Gnome as window_system

    return window_system


def get_window_system(window_system_id: str = "") -> Type[WindowSystem]:
    """Get window system.

    :param window_system_id: The window system id to use (see
        get_window_system_class), otherwise, try to find the best match.
    :return: The window system for the current system.
    """

    if not window_system_id:

        window_system_type = get_window_system_type()

        if window_system_type == WindowSystemType.X11:
            window_system_id = "x11"
        if window_system_type == WindowSystemType.WAYLAND:

            # add new waland wms here, then add a match case below to import the class
            supported_wayland_wms = {"sway", "Hyprland", "plasmashell", "gnome-shell"}

            # Check if there is a process running that matches the supported_wayland_wms
            window_system_id = (
                run(
                    "ps -e -o comm | grep -m 1 -o -E "
                    + " ".join([f"-e '^{wm}$'" for wm in supported_wayland_wms]),
                    capture_output=True,
                    shell=True,
                )
                .stdout.decode("utf-8")
                .strip()
            ).lower()

    window_system = get_window_system_class(window_system_id)

    if not window_system:
        raise WindowSystemNotSupported(get_args(SupportedWindowSystems))

    return window_system


def main():
    """Hints entry point."""

    config = load_config()

    parser = ArgumentParser(
        prog="Hints",
        description="Hints lets you navigate GUI applications in Linux without"
        ' your mouse by displaying "hints" you can type on your keyboard to'
        " interact with GUI elements.",
    )
    parser.add_argument(
        "-m",
        "--mode",
        type=str,
        default="hint",
        choices=["hint", "scroll"],
        help="mode to use",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Set verbosity of output. Useful for debugging and seeing the"
        " output of accessible elements (roles, states, application name, ect)"
        " for setting up configuration.",
    )

    args = parser.parse_args()

    custom_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    if args.verbose >= 1:
        logging.basicConfig(level=logging.DEBUG, format=custom_format)
    else:
        logging.basicConfig(level=logging.INFO, format=custom_format)

    window_system = get_window_system(config["window_system"])()

    match args.mode:
        case "hint":
            hint_mode(config, window_system)
        case "scroll":
            display_gtk_window(
                window_system,
                InterceptorWindow,
                0,
                0,
                1,
                1,
                gkt_window_args=({"action": "scroll"}, config),
                gtk_window_kwargs={
                    "is_wayland": window_system.window_system_type
                    == WindowSystemType.WAYLAND,
                },
            )

if __name__ == "__main__":
    main()
