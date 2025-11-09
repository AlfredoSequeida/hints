"""Mouse service for hints.

This service is an independent application that hints calls using a Unix
Domain Socket to perform mouse movements by writing to uinput. We use
custom uinput devices to support X11 and Wayland. This is separate from
the main hints application to prevent slowing down the main hints
process when creating virutal devices.
"""

from __future__ import annotations

import socket
from os import path, remove
from pickle import dumps, loads
from signal import SIGINT, signal
from time import sleep, time
from typing import TYPE_CHECKING, Any, Iterable

from evdev import AbsInfo, UInput, ecodes
from gi import require_version

from hints.constants import SOCKET_MESSAGE_SIZE, UNIX_DOMAIN_SOCKET_FILE
from hints.mouse_enums import MouseButton, MouseMode
from hints.utils import load_config

require_version("Gdk", "3.0")
require_version("Gtk", "3.0")
from gi.repository import Gdk, GLib, Gtk

if TYPE_CHECKING:
    from hints.mouse_enums import MouseButtonState

MOUSE_SERVICE_LOOP_MS_INTERVAL = 10
config = load_config()


class Mouse:
    """Mouse class for performing mouse actions (click, hover, move, etc).

    This uses uinput to support both X11 and Wayland.
    """

    @staticmethod
    def _get_visible_screen_rect(screen: Gdk.Screen) -> tuple[int, int, int, int]:
        """Get the current screen size. See Issue #48

        :return: The current screen size (min_x, min_y, max_x, max_y).
        """
        min_x, min_y, max_x, max_y = None, None, None, None
        for monitor_index in range(screen.get_n_monitors()):
            geometry = screen.get_monitor_geometry(monitor_index)
            if min_x is None or geometry.x < min_x:
                min_x = geometry.x
            if min_y is None or geometry.y < min_y:
                min_y = geometry.y
            if max_x is None or geometry.x + geometry.width > max_x:
                max_x = geometry.x + geometry.width
            if max_y is None or geometry.y + geometry.height > max_y:
                max_y = geometry.y + geometry.height

        if min_x is None or min_y is None or max_x is None or max_y is None:
            return (0, 0, 0, 0)
        return (min_x, min_y, max_x, max_y)

    def __init__(self, screen: Gdk.Screen, write_pause=0.03):

        min_x, min_y, max_x, max_y = self._get_visible_screen_rect(screen)

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
                            min=min_x,
                            max=max_x,
                            fuzz=0,
                            flat=0,
                            resolution=0,
                        ),
                    ),
                    (
                        ecodes.ABS_Y,
                        AbsInfo(
                            value=0,
                            min=min_y,
                            max=max_y,
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
        self.mouse = Mouse(screen=self.screen)

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
        self.mouse = Mouse(screen=self.screen)

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
                    }[method](*args, **kwargs)
                )
            )
        except BlockingIOError:
            pass

        return GLib.SOURCE_CONTINUE

    def run(self):
        """Run the mouse service."""
        Gtk.main()


def main():
    """Mouse service entry point."""
    MouseService().run()


if __name__ == "__main__":
    main()
