"""Popup window to intercept keyboard events.

This is a way to work around applications that listen for keyboard
events, which interfere with the keyboard events to perform mouse
movements.

By creting a small window (like 1x1 pixel) over the corner of the taget
application, we can grab keyboard focus thus preventing the target
application from grabbing focus and interfering with the events we are
listening for.
"""

from __future__ import annotations

from typing import Any, Callable

from gi import require_foreign, require_version

from hints import mouse as default_mouse_client
from hints.mouse_enums import MouseButton, MouseButtonState, MouseMode
from hints.utils import HintsConfig

require_version("Gdk", "3.0")
require_version("Gtk", "3.0")
require_foreign("cairo")

from gi.repository import Gdk, Gtk


class InterceptorWindow(Gtk.Window):
    """Composite widget to overlay hints over a window."""

    def __init__(
        self,
        x_pos: float,
        y_pos: float,
        width: float,
        height: float,
        mouse_action: dict[str, Any],
        config: HintsConfig,
        is_wayland=False,
        mouse=None,
        on_complete: Callable[[], None] | None = None,
    ):
        """Hint overlay constructor.

        :param x_pos: X window position.
        :param y_pos: Y window position.
        :param width: Window width.
        :param height: Window height.
        :param mouse_action: Mouse action information.
        :param config: Hints config.
        :param mouse: Object exposing the hints.mouse client interface
            (click/move/do_mouse_action taking enums). Defaults to the
            socket client. The daemon injects an in-process adapter so the
            interceptor does not deadlock talking to the daemon's own socket.
        :param on_complete: Called once the interceptor is done. When
            omitted, the window quits the GTK main loop (standalone).
        """
        super().__init__(Gtk.WindowType.POPUP)

        self.width = width
        self.height = height
        self.mouse_action = mouse_action
        self.config = config
        self.key_press_state: dict[str, Any] = {}
        self.is_wayland = is_wayland
        self.first_move = True
        self._mouse = mouse if mouse is not None else default_mouse_client
        self.on_complete = on_complete

        # composite setup
        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        self.set_visual(visual)

        # window setup
        self.set_app_paintable(True)
        self.set_decorated(False)
        self.set_accept_focus(True)
        self.set_sensitive(True)
        self.set_default_size(self.width, self.height)
        self.move(x_pos, y_pos)

        self.connect("destroy", self._on_destroy)
        self.connect("key-press-event", self.on_key_press)
        self.connect("key-release-event", self.on_key_release)
        self.connect("show", self.on_grab)

    def _on_destroy(self, *_):
        """Handle window teardown.

        Invokes the completion callback when one was provided (daemon
        mode), otherwise quits the GTK main loop (standalone mode).
        """
        if self.on_complete is not None:
            self.on_complete()
        else:
            Gtk.main_quit()

    def on_key_release(self, *_):
        """Handle key releases."""
        self.key_press_state.clear()

    def on_key_press(self, _, event):
        """Handle key presses :param event: Event object."""

        keyval_lower = Gdk.keyval_to_lower(event.keyval)

        if keyval_lower == self.config["exit_key"]:
            self._mouse.click(
                0, 0, MouseButton.LEFT, (MouseButtonState.UP,), absolute=False
            )
            self.destroy()
            return

        if self.first_move:
            # Some window system like Hyprland require mouse movemovement to
            # focus the window being interacted with. So we do a very small move to
            # refocus the window
            self._mouse.move(0, 1, absolute=False)
            self._mouse.move(0, -1, absolute=False)
            self.first_move = False

        if keyval_lower:
            match self.mouse_action["action"]:
                case "grab":
                    self.key_press_state = self._mouse.do_mouse_action(
                        self.key_press_state,
                        chr(keyval_lower),
                        MouseMode.MOVE,
                    )
                case "scroll":
                    self.key_press_state = self._mouse.do_mouse_action(
                        self.key_press_state,
                        chr(keyval_lower),
                        MouseMode.SCROLL,
                    )

    def on_grab(self, window):
        """Force keyboard grab to listen for keybaord events.

        :param window: Window object.
        """
        if not self.is_wayland:
            seat = Gdk.Display.get_default().get_default_seat()
            seat.grab(
                window.get_window(),
                Gdk.SeatCapabilities.KEYBOARD,
                False,
                None,
                None,
                None,
            )
