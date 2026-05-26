from __future__ import annotations

import logging
from argparse import ArgumentParser
from itertools import product
from math import ceil, log
from subprocess import run
from time import time
from typing import TYPE_CHECKING, Any, Iterable, Type, get_args

from gi import require_version

from hints.backends.exceptions import AccessibleChildrenNotFoundError
from hints.constants import ELEMENT_DETAIL_LOG_LEVEL
from hints.huds.interceptor import InterceptorWindow
from hints.huds.overlay import OverlayWindow
from hints.mouse import click
from hints.mouse_enums import MouseButton, MouseButtonState
from hints.setup import run_guided_setup
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


def create_gtk_window(
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
) -> Gtk.Window:
    """Build, position, and show a gtk window (without running a main loop).

    Applies the platform-specific setup (GNOME shell positioning, Wayland
    layer-shell, or plain X11). Returns the shown window so the caller can
    drive it: standalone runs its own ``Gtk.main()`` (see
    :func:`display_gtk_window`), while the daemon shows it inside its
    existing main loop.

    :param window_system: The window system.
    :param gtk_window: The Gtk Window class to display.
    :param x: X position for window.
    :param y: Y position for window.
    :param width: Width for window.
    :param height: Height for window.
    :param gkt_window_args: The positional argument for the window
        instance.
    :param gtk_window_kwargs: The keyword arguments for the window
        instance.
    :param overlay_x_offset: X offset position for the window.
    :param overlay_y_offset: Y offset position for the window.
    :return: The shown Gtk window.
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
    elif window_system.window_system_type == WindowSystemType.WAYLAND:
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
    return window


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
    """Build, show, and run a gtk window standalone (blocks on Gtk.main).

    See :func:`create_gtk_window` for parameter details.
    """
    create_gtk_window(
        window_system,
        gtk_window,
        x,
        y,
        width,
        height,
        gkt_window_args=gkt_window_args,
        gtk_window_kwargs=gtk_window_kwargs,
        overlay_x_offset=overlay_x_offset,
        overlay_y_offset=overlay_y_offset,
    )
    Gtk.main()


def load_backend(backend: str):
    """Lazily import and return a backend class.

    The opencv backend pulls in cv2/numpy/pyscreenshot, which add roughly a
    second to a cold import. Since atspi is the default first backend and
    opencv is only a fallback, importing on demand keeps the common launch
    path fast.

    :param backend: The backend name to load.
    :return: The backend class.
    """
    if backend == "atspi":
        from hints.backends.atspi import AtspiBackend

        return AtspiBackend
    if backend == "opencv":
        from hints.backends.opencv import OpenCV

        return OpenCV
    raise KeyError(backend)


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


def gather_hints(
    config: HintsConfig, window_system: WindowSystem
) -> tuple[dict[str, Child], tuple[int, int, int, int] | None]:
    """Run the enabled backends until one yields hints.

    :param config: Hints config.
    :param window_system: Window system for the session.
    :return: A (hints, window_extents) tuple. window_extents is None
        when no backend produced hints.
    """
    for backend in config["backends"]["enable"]:

        start = time()
        current_backend = load_backend(backend)(config, window_system)
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

            if window_extents and hints:
                return hints, window_extents

        except AccessibleChildrenNotFoundError:
            logger.debug(
                "No acceessible children found with the '%s' backend.",
                backend,
            )

    return {}, None


def hint_mode(
    config: HintsConfig, window_system: WindowSystem, launch_time: float | None = None
):
    """Hint mode to interact with hints on screen.

    :param config: Hints config.
    :param window_system: Window System for the session.
    :param launch_time: Process launch timestamp, used to log the total
        time from launch until hints are first painted.
    """
    hints, window_extents = gather_hints(config, window_system)

    if not (window_extents and hints):
        return

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
            "is_wayland": window_system.window_system_type == WindowSystemType.WAYLAND,
            "launch_time": launch_time,
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
        case "niri":
            from hints.window_systems.niri import Niri as window_system
        case "mango":
            from hints.window_systems.mango import Mango as window_system

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
            supported_wayland_wms = {
                "sway",
                "Hyprland",
                "plasmashell",
                "gnome-shell",
                "niri",
                "mango",
            }

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

    launch_time = time()
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
        help="Set verbosity of output. -v shows timing and high-level debug"
        " info; -vv additionally logs per-accessible-element details (roles,"
        " states, application name, etc) for setting up configuration. Note"
        " that -vv adds extra accessibility queries, so use -v for timing.",
    )
    parser.add_argument(
        "-s", "--setup", action="store_true", default=False, help="Guided hints setup."
    )

    args = parser.parse_args()

    if args.setup:
        run_guided_setup()
        exit()

    custom_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    if args.verbose >= 2:
        log_level = ELEMENT_DETAIL_LOG_LEVEL
    elif args.verbose == 1:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO

    logging.basicConfig(level=log_level, format=custom_format)

    start = time()
    window_system = get_window_system(config["window_system"])()
    logger.debug("Window system init took %f seconds", time() - start)

    match args.mode:
        case "hint":
            hint_mode(config, window_system, launch_time)
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
