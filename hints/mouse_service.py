"""Mouse service for hints.

This service is an independent application that hints calls using a Unix
Domain Socket to perform mouse movements by writing to uinput. We use
custom uinput devices to support X11 and Wayland. This is separate from
the main hints application to prevent slowing down the main hints
process when creating virutal devices.
"""

from __future__ import annotations

import logging
import socket
from os import getenv, path, remove
from pickle import dumps, loads
from signal import SIGINT, signal
from time import sleep, time
from typing import Any, Iterable

from evdev import AbsInfo, UInput, ecodes
from gi import require_version

from hints.constants import SOCKET_MESSAGE_SIZE, UNIX_DOMAIN_SOCKET_FILE
from hints.mouse_enums import MouseButton, MouseButtonState, MouseMode
from hints.utils import load_config

require_version("Gdk", "3.0")
require_version("Gtk", "3.0")
require_version("Atspi", "2.0")
from gi.repository import Atspi, Gdk, GLib, Gtk

from hints.hints import create_gtk_window, gather_hints, get_window_system, load_backend
from hints.huds.interceptor import InterceptorWindow
from hints.huds.overlay import OverlayWindow
from hints.window_systems.window_system_type import WindowSystemType

logger = logging.getLogger(__name__)


class _DaemonMouse:
    """In-process adapter exposing the hints.mouse client interface.

    ``InterceptorWindow`` normally drives the mouse over the socket. When it
    runs inside the daemon that would deadlock (the daemon would block waiting
    on its own loop to service the request), so this forwards calls to the
    daemon's ``Mouse`` device directly, converting enums to the raw values
    ``Mouse`` expects.
    """

    def __init__(self, mouse: "Mouse"):
        self._mouse = mouse

    def click(self, x, y, button, button_states, repeat=1, absolute=True):
        self._mouse.click(
            x,
            y,
            button.value,
            [state.value for state in button_states],
            repeat=repeat,
            absolute=absolute,
        )

    def move(self, x, y, absolute=True):
        self._mouse.move(x, y, absolute=absolute)

    def do_mouse_action(self, key_press_state, key, mode):
        return self._mouse.do_mouse_action(key_press_state, key, mode.value)


MOUSE_SERVICE_LOOP_MS_INTERVAL = 10
config = load_config()


class Mouse:
    """Mouse class for performing mouse actions (click, hover, move, etc).

    This uses uinput to support both X11 and Wayland.
    """

    def __init__(self, abs_max_width=10000, abs_max_height=10000, write_pause=0.03):

        keys = [button.value for button in MouseButton]
        self.write_pause = write_pause

        self.relative_mouse = UInput(
            {
                ecodes.EV_KEY: keys,
                ecodes.EV_REL: [
                    ecodes.REL_X,
                    ecodes.REL_Y,
                    ecodes.REL_HWHEEL,
                    ecodes.REL_WHEEL,
                ],
            },
            name="Hints relative mouse",
        )

        self.absolute_mouse = UInput(
            {
                ecodes.EV_KEY: keys,
                ecodes.EV_ABS: [
                    (
                        ecodes.ABS_X,
                        AbsInfo(
                            value=0,
                            min=0,
                            max=abs_max_width,
                            fuzz=0,
                            flat=0,
                            resolution=0,
                        ),
                    ),
                    (
                        ecodes.ABS_Y,
                        AbsInfo(
                            value=0,
                            min=0,
                            max=abs_max_height,
                            fuzz=0,
                            flat=0,
                            resolution=0,
                        ),
                    ),
                ],
            },
            name="Hints absolute mouse",
        )

    def scroll(self, x: int, y: int, *_args, **_kwargs):
        """Scroll event.

        :param x: X scroll direction.
        :param y: Y scroll direction. :param *_args: Extra args to use
            the same interface as move. :param **_kwargs: Extra kwargs
            to use the same interface as move.
        """
        self.relative_mouse.write(ecodes.EV_REL, ecodes.REL_HWHEEL, int(x))
        self.relative_mouse.write(ecodes.EV_REL, ecodes.REL_WHEEL, int(y))
        self.relative_mouse.syn()

    def move(self, x: int, y: int, absolute: bool = True):
        """Move event.

        :param X: X move direction.
        :param y: Y move direction.
        :param absolute: Whether to move the mouse using an absolute
            position.
        """

        if absolute:
            self.absolute_mouse.write(ecodes.EV_ABS, ecodes.ABS_X, int(x))
            self.absolute_mouse.write(ecodes.EV_ABS, ecodes.ABS_Y, int(y))
            self.absolute_mouse.syn()

        else:
            self.relative_mouse.write(ecodes.EV_REL, ecodes.REL_X, int(x))
            self.relative_mouse.write(ecodes.EV_REL, ecodes.REL_Y, int(y))
            self.relative_mouse.syn()

        sleep(self.write_pause)

    def click(
        self,
        x: int,
        y: int,
        button: MouseButton,
        button_states: Iterable[MouseButtonState],
        repeat: int = 1,
        absolute: bool = True,
    ):
        """Click event.

        :param x: X position to click.
        :param y: Y position to click.
        :param button: Button to use for click.
        :param actions: Actions to use for the click button (button down
            / button up).
        :param repeat: Times to repeat a click.
        :param absolute: Whether the click position is absolute.
        """
        self.move(x, y, absolute=absolute)

        for _ in range(repeat):
            for button_state in button_states:
                self.relative_mouse.write(ecodes.EV_KEY, button, button_state)
                self.relative_mouse.syn()
                sleep(self.write_pause)

        if absolute:
            # small move to clear previous write incase the previous move wants
            # to be repeated
            self.move(x + 1, y, absolute=True)
            self.move(x - 1, y, absolute=True)

    def do_mouse_action(
        self,
        key_press_state: dict[str, Any],
        key: str,
        mode: MouseMode,
    ):
        """Perform mouse action.

        :param key_press_state: State containing key press event data
            used for ramping up speeds.
        :param key: The key to perform a mouse action for.
        :param mode: The mouse mode.
        """
        key_press_state.setdefault("start_time", time())

        sensitivity = 1
        rampup_time = 1
        mouse_navigation_action = self.move
        left = "h"
        right = "l"
        up = "k"
        down = "j"

        if mode == MouseMode.MOVE.value:
            sensitivity = config["mouse_move_pixel_sensitivity"]
            rampup_time = config["mouse_move_rampup_time"]
            left = config["mouse_move_left"]
            right = config["mouse_move_right"]

            # up and down are intentionally switched to keep the logic the same
            # as scrol
            up = config["mouse_move_down"]
            down = config["mouse_move_up"]

            mouse_navigation_action = self.move

        elif mode == MouseMode.SCROLL.value:
            sensitivity = config["mouse_scroll_pixel_sensitivity"]
            rampup_time = config["mouse_scroll_rampup_time"]
            left = config["mouse_scroll_left"]
            right = config["mouse_scroll_right"]
            up = config["mouse_scroll_up"]
            down = config["mouse_scroll_down"]
            mouse_navigation_action = self.scroll

        key_press_state.setdefault("sensitivity", sensitivity)

        if time() - key_press_state["start_time"] >= rampup_time:
            key_press_state["sensitivity"] += sensitivity

        if key == left:
            mouse_navigation_action(-key_press_state["sensitivity"], 0, absolute=False)
        if key == right:
            mouse_navigation_action(key_press_state["sensitivity"], 0, absolute=False)
        if key == up:
            mouse_navigation_action(0, key_press_state["sensitivity"], absolute=False)
        if key == down:
            mouse_navigation_action(0, -key_press_state["sensitivity"], absolute=False)

        return key_press_state


class MouseService:
    """Mouse Service.

    This is responsible for running the mouse service and detecting
    events requring the mouse devices to reload / be updated.
    """

    def __init__(self):
        """Mouse Service Constructor."""
        Gtk.init()

        self.screen = Gdk.Screen.get_default()
        self.mouse = Mouse(self.screen.get_width(), self.screen.get_height())

        # Hint overlay state. Only one overlay may be active at a time.
        self._overlay_active = False
        self._mouse_action: dict[str, Any] = {}
        self._overlay_window: OverlayWindow | None = None
        self._interceptor_window: InterceptorWindow | None = None
        self._window_system = None
        self._window_extents: tuple[int, int, int, int] | None = None
        self._config: dict[str, Any] | None = None
        # In-process mouse interface for the interceptor (avoids socket deadlock).
        self._mouse_adapter = _DaemonMouse(self.mouse)

        # Warm the AT-SPI connection so the first hint trigger does not pay
        # the registry/connection setup cost.
        try:
            Atspi.get_desktop(0)
        except Exception:  # pylint: disable=broad-except
            logger.debug("AT-SPI warm-up failed", exc_info=True)

        # Optionally preload the opencv fallback backend so the first
        # opencv-backed hint does not pay the heavy cv2/numpy/pyscreenshot
        # import. Off by default: opencv is a fallback many users never
        # trigger, and the imports are large to keep resident in a long-lived
        # service. Opt in (config: backends.opencv.preload) for setups where
        # opencv is the primary backend.
        if (
            "opencv" in config["backends"]["enable"]
            and config["backends"]["opencv"]["preload"]
        ):
            try:
                load_backend("opencv")
                logger.debug("Preloaded opencv backend")
            except Exception:  # pylint: disable=broad-except
                logger.debug("opencv preload failed", exc_info=True)

        if path.exists(UNIX_DOMAIN_SOCKET_FILE):
            remove(UNIX_DOMAIN_SOCKET_FILE)

        self.socket = socket.socket(
            socket.AF_UNIX, socket.SOCK_STREAM | socket.SOCK_NONBLOCK
        )
        self.socket.bind(UNIX_DOMAIN_SOCKET_FILE)
        self.socket.listen(1)
        GLib.timeout_add(MOUSE_SERVICE_LOOP_MS_INTERVAL, self.socket_connection)

        self.screen.connect("size-changed", self.on_size_changed)
        signal(SIGINT, self.on_interrupt)

    def on_interrupt(self, *_):
        """Interrupt handler to clean up."""
        self.socket.close()
        Gtk.main_quit()

    def on_size_changed(self, screen: Gdk.Screen):
        """Screen size change event handler to update the mouse device min/max
        values for correct absolute position movement.

        :param screen: The screen object for the event.
        """
        self.mouse = Mouse(screen.get_width(), screen.get_height())

    def socket_connection(self):
        """Handle socket connection events.

        This is how the main hints process and the mouse service
        communicate.
        """
        try:
            connection, _ = self.socket.accept()
            payload = loads(connection.recv(SOCKET_MESSAGE_SIZE))
            method = payload.get("method", "")
            args = payload.get("args", ())
            kwargs = payload.get("kwargs", {})
            connection.send(
                dumps(
                    {
                        "click": self.mouse.click,
                        "move": self.mouse.move,
                        "scoll": self.mouse.scroll,
                        "do_mouse_action": self.mouse.do_mouse_action,
                        "show_hints": self.show_hints,
                    }[method](*args, **kwargs)
                )
            )
        except BlockingIOError:
            pass

        return GLib.SOURCE_CONTINUE

    def show_hints(self, mode: str = "hint", verbose: int = 0) -> dict[str, Any]:
        """Gather and display hints over the focused window.

        Runs inside the daemon's existing GTK main loop: the overlay is
        shown (not blocking) and key handling plus the resulting mouse
        action are driven by signal handlers / the completion callback.

        :param mode: Hint mode (currently only "hint").
        :param verbose: Client verbosity level (reserved; daemon logs to
            its own handler).
        :return: Status payload sent back to the triggering client.
        """
        if self._overlay_active:
            return {"status": "busy"}

        launch_time = time()

        try:
            # Reload config each trigger so user edits apply without
            # restarting the daemon.
            current_config = load_config()
            window_system = get_window_system(current_config["window_system"])()
            hints, window_extents = gather_hints(current_config, window_system)
        except Exception:  # pylint: disable=broad-except
            logger.debug("Failed to gather hints", exc_info=True)
            return {"status": "error"}

        if not (window_extents and hints):
            return {"status": "no_hints"}

        x, y, width, height = window_extents
        is_wayland = window_system.window_system_type == WindowSystemType.WAYLAND
        self._overlay_active = True
        self._mouse_action = {}
        self._window_system = window_system
        self._window_extents = window_extents
        self._config = current_config

        try:
            self._overlay_window = create_gtk_window(
                window_system,
                OverlayWindow,
                x,
                y,
                width,
                height,
                gkt_window_args=(current_config, hints, self._mouse_action),
                gtk_window_kwargs={
                    "is_wayland": is_wayland,
                    "launch_time": launch_time,
                    "on_complete": self._on_hints_complete,
                },
                overlay_x_offset=current_config["overlay_x_offset"],
                overlay_y_offset=current_config["overlay_y_offset"],
            )
        except Exception:  # pylint: disable=broad-except
            # Never leave the guard stuck on if the overlay fails to build or
            # show, otherwise no further hints could be triggered.
            self._overlay_active = False
            self._overlay_window = None
            logger.debug("Failed to display hint overlay", exc_info=True)
            return {"status": "error"}

        return {"status": "ok"}

    def _on_hints_complete(self):
        """Tear down the overlay and schedule the selected mouse action.

        Called from the overlay's destroy handler. The mouse action is NOT
        performed here: doing so synchronously fires the click while the
        overlay surface is still mapped over the target window (on Wayland
        the click then lands on the layer-shell surface, not the app). It is
        instead deferred so it runs after the surface is torn down, mirroring
        the standalone path where the click happens once the overlay is gone.
        """
        mouse_action = self._mouse_action
        window_system = self._window_system
        self._overlay_window = None

        # On X11 the overlay grabbed the keyboard via Gdk.keyboard_grab; release
        # it defensively in case the overlay exited without selecting a hint. On
        # Wayland the grab is owned by GtkLayerShell (KeyboardMode.EXCLUSIVE) and
        # is released when the surface is destroyed, so no explicit ungrab.
        if (
            window_system is not None
            and window_system.window_system_type != WindowSystemType.WAYLAND
        ):
            Gdk.keyboard_ungrab(Gdk.CURRENT_TIME)

        if not mouse_action:
            self._overlay_active = False
            return

        # Defer until the overlay surface has been torn down. The interval
        # matches the socket poll cadence the standalone path effectively waits
        # on. The overlay guard stays set until the action completes so a new
        # trigger can't race an in-flight action.
        GLib.timeout_add(
            MOUSE_SERVICE_LOOP_MS_INTERVAL,
            self._perform_mouse_action,
            mouse_action,
            window_system,
        )

    def _perform_mouse_action(self, mouse_action: dict[str, Any], window_system):
        """Perform a deferred hint mouse action in-process.

        :param mouse_action: The action payload populated by the overlay.
        :param window_system: The window system the overlay ran against.
        :return: GLib.SOURCE_REMOVE so the timeout fires only once.
        """
        try:
            logger.debug("performing '%s'", mouse_action)

            # Match the per-window-system mouse offsets that standalone
            # hint_mode applies (e.g. sway excludes the top bar from extents).
            mouse_x_offset = 0
            mouse_y_offset = 0
            if window_system is not None and window_system.window_system_name == "sway":
                mouse_y_offset = window_system.bar_height

            x = mouse_action["x"] + mouse_x_offset
            y = mouse_action["y"] + mouse_y_offset

            match mouse_action["action"]:
                case "click":
                    self.mouse.click(
                        x,
                        y,
                        mouse_action["button"].value,
                        [MouseButtonState.DOWN.value, MouseButtonState.UP.value],
                        repeat=mouse_action["repeat"],
                    )
                case "hover":
                    self.mouse.click(x, y, MouseButton.LEFT.value, [])
                case "grab":
                    # Grab keeps the session alive via the interceptor window;
                    # the guard is released in _on_interceptor_complete.
                    self._start_grab(x, y, window_system)
                    return GLib.SOURCE_REMOVE
                case _:
                    logger.debug(
                        "Action '%s' is not yet supported in daemon mode",
                        mouse_action["action"],
                    )
        except Exception:  # pylint: disable=broad-except
            logger.debug("Failed to perform mouse action", exc_info=True)

        self._overlay_active = False
        return GLib.SOURCE_REMOVE

    def _start_grab(self, x: int, y: int, window_system):
        """Begin a drag: press-and-hold then open the keyboard interceptor.

        The button is held down at the hint location and a tiny
        keyboard-grabbing window is shown so h/j/k/l move the cursor. Mouse
        actions run in-process via the adapter (see :class:`_DaemonMouse`) to
        avoid the daemon deadlocking on its own socket. The overlay guard stays
        set until the interceptor closes (:meth:`_on_interceptor_complete`).
        """
        self.mouse.click(x, y, MouseButton.LEFT.value, [MouseButtonState.DOWN.value])

        origin_x, origin_y, _w, _h = self._window_extents
        is_wayland = (
            window_system is not None
            and window_system.window_system_type == WindowSystemType.WAYLAND
        )

        self._interceptor_window = create_gtk_window(
            window_system,
            InterceptorWindow,
            origin_x,
            origin_y,
            1,
            1,
            gkt_window_args=({"action": "grab"}, self._config),
            gtk_window_kwargs={
                "is_wayland": is_wayland,
                "mouse": self._mouse_adapter,
                "on_complete": self._on_interceptor_complete,
            },
        )

    def _on_interceptor_complete(self):
        """Release grab state once the interceptor window is done."""
        self._interceptor_window = None
        self._overlay_active = False

    def run(self):
        """Run the mouse service."""
        Gtk.main()


def main():
    """Mouse service entry point."""
    # Quiet by default; set HINTS_DEBUG=1 to surface hint timing and debug
    # logs in the journal for troubleshooting.
    logging.basicConfig(
        level=logging.DEBUG if getenv("HINTS_DEBUG") else logging.WARNING,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    MouseService().run()


if __name__ == "__main__":
    main()
