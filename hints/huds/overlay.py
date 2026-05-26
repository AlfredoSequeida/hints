"""Overlay to display hints over an application window."""

from __future__ import annotations

import logging
from time import time
from typing import TYPE_CHECKING, Any, Callable

from gi import require_foreign, require_version

from hints.mouse_enums import MouseButton
from hints.utils import HintsConfig

require_version("Gdk", "3.0")
require_version("Gtk", "3.0")
require_foreign("cairo")
from cairo import FONT_SLANT_NORMAL, FONT_WEIGHT_BOLD
from gi.repository import Gdk, Gtk

if TYPE_CHECKING:
    from cairo import Context

    from hints.child import Child

logger = logging.getLogger(__name__)


class OverlayWindow(Gtk.Window):
    """Composite widget to overlay hints over a window."""

    def __init__(
        self,
        x_pos: float,
        y_pos: float,
        width: float,
        height: float,
        config: HintsConfig,
        hints: dict[str, Child],
        mouse_action: dict[str, Any],
        is_wayland: bool = False,
        launch_time: float | None = None,
        on_complete: Callable[[], None] | None = None,
    ):
        """Hint overlay constructor.

        :param x_pos: X window position.
        :param y_pos: Y window position.
        :param width: Window width.
        :param height: Window height.
        :param config: Hints config.
        :param hints: Hints to draw.
        :param mouse_action: Mouse action information.
        :param on_complete: Called once the overlay is done (a hint was
            selected or the user exited). When omitted, the window quits
            the GTK main loop, preserving the standalone behavior.
        """
        super().__init__(Gtk.WindowType.POPUP)

        self.width = width
        self.height = height
        self.hints = hints
        self.hint_selector_state = ""
        self.mouse_action = mouse_action
        self.is_wayland = is_wayland
        self.launch_time = launch_time
        self.on_complete = on_complete

        # hint settings
        hints_config = config["hints"]
        self.hint_height = hints_config["hint_height"]
        self.hint_width_padding = hints_config["hint_width_padding"]

        self.hint_font_size = hints_config["hint_font_size"]
        self.hint_font_face = hints_config["hint_font_face"]
        self.hint_font_r = hints_config["hint_font_r"]
        self.hint_font_g = hints_config["hint_font_g"]
        self.hint_font_b = hints_config["hint_font_b"]
        self.hint_font_a = hints_config["hint_font_a"]

        self.hint_pressed_font_r = hints_config["hint_pressed_font_r"]
        self.hint_pressed_font_g = hints_config["hint_pressed_font_g"]
        self.hint_pressed_font_b = hints_config["hint_pressed_font_b"]
        self.hint_pressed_font_a = hints_config["hint_pressed_font_a"]
        self.hint_upercase = hints_config["hint_upercase"]

        self.hint_background_r = hints_config["hint_background_r"]
        self.hint_background_g = hints_config["hint_background_g"]
        self.hint_background_b = hints_config["hint_background_b"]
        self.hint_background_a = hints_config["hint_background_a"]

        # key settings
        self.exit_key = config["exit_key"]
        self.hover_modifier = config["hover_modifier"]
        self.grab_modifier = config["grab_modifier"]

        self.hints_drawn_offsets: dict[str, tuple[float, float]] = {}

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

        self.drawing_area = Gtk.DrawingArea()

        self.connect("destroy", self._on_destroy)
        self.connect("key-press-event", self.on_key_press)
        self.connect("show", self.on_show)
        self.drawing_area.connect("draw", self.on_draw)

        def put_in_frame(widget):
            frame = Gtk.Frame(label=None)
            frame.set_property("shadow_type", Gtk.ShadowType.IN)
            frame.add(widget)
            return frame

        self.current_snippet = None

        vpaned = Gtk.VPaned()
        self.add(vpaned)
        vpaned.pack1(put_in_frame(self.drawing_area), True, True)

    def reset(
        self,
        x_pos: float,
        y_pos: float,
        width: float,
        height: float,
        config: HintsConfig,
        hints: dict,
        mouse_action: dict,
        launch_time: float | None = None,
    ):
        """Reset per-trigger state so the window can be reused without recreating it.

        :param x_pos: New X window position.
        :param y_pos: New Y window position.
        :param width: New window width.
        :param height: New window height.
        :param config: Hints config (re-read so user edits apply without daemon restart).
        :param hints: New hints to display.
        :param mouse_action: Fresh mouse action dict for this trigger.
        :param launch_time: Trigger timestamp for paint-latency logging.
        """
        self.width = width
        self.height = height
        self.hints = hints
        self.hint_selector_state = ""
        self.mouse_action = mouse_action
        self.launch_time = launch_time
        self.hints_drawn_offsets = {}

        hints_config = config["hints"]
        self.hint_height = hints_config["hint_height"]
        self.hint_width_padding = hints_config["hint_width_padding"]
        self.hint_font_size = hints_config["hint_font_size"]
        self.hint_font_face = hints_config["hint_font_face"]
        self.hint_font_r = hints_config["hint_font_r"]
        self.hint_font_g = hints_config["hint_font_g"]
        self.hint_font_b = hints_config["hint_font_b"]
        self.hint_font_a = hints_config["hint_font_a"]
        self.hint_pressed_font_r = hints_config["hint_pressed_font_r"]
        self.hint_pressed_font_g = hints_config["hint_pressed_font_g"]
        self.hint_pressed_font_b = hints_config["hint_pressed_font_b"]
        self.hint_pressed_font_a = hints_config["hint_pressed_font_a"]
        self.hint_upercase = hints_config["hint_upercase"]
        self.hint_background_r = hints_config["hint_background_r"]
        self.hint_background_g = hints_config["hint_background_g"]
        self.hint_background_b = hints_config["hint_background_b"]
        self.hint_background_a = hints_config["hint_background_a"]
        self.exit_key = config["exit_key"]
        self.hover_modifier = config["hover_modifier"]
        self.grab_modifier = config["grab_modifier"]

        self.set_default_size(width, height)
        self.move(x_pos, y_pos)
        self.drawing_area.queue_draw()

    def _finish(self):
        """Complete overlay interaction: ungrab, notify caller, then hide or destroy.

        In daemon mode (on_complete set) the window is hidden rather than destroyed
        so it can be reused on the next trigger. In standalone mode the window is
        destroyed so _on_destroy fires and quits the GTK main loop.
        """
        if not self.is_wayland:
            Gdk.Display.get_default().get_default_seat().ungrab()
        if self.on_complete is not None:
            self.on_complete()
            self.hide()
        else:
            self.destroy()

    def _on_destroy(self, *_):
        """Handle window teardown.

        Invokes the completion callback when one was provided (daemon
        mode), otherwise quits the GTK main loop (standalone mode).
        """
        if self.on_complete is not None:
            self.on_complete()
        else:
            Gtk.main_quit()

    def on_draw(self, _, cr: Context):
        """Draw hints.

        :param cr: Cairo Context.
        """
        if self.launch_time is not None:
            logger.debug(
                "Time from launch to first hint paint: %f seconds",
                time() - self.launch_time,
            )
            self.launch_time = None

        hint_height = self.hint_height

        cr.select_font_face(self.hint_font_face, FONT_SLANT_NORMAL, FONT_WEIGHT_BOLD)
        cr.set_font_size(self.hint_font_size)

        for hint_value, child in self.hints.items():
            x_loc, y_loc = child.relative_position
            if x_loc >= 0 and y_loc >= 0:
                cr.save()
                utf8 = hint_value.upper() if self.hint_upercase else hint_value
                hint_state = (
                    self.hint_selector_state.upper()
                    if self.hint_upercase
                    else self.hint_selector_state
                )

                x_bearing, y_bearing, width, height, _, _ = cr.text_extents(utf8)
                hint_width = width + self.hint_width_padding

                cr.new_path()
                # offset to bring top left corner of a hint to the correct possition
                # so that the hint is centered on the object
                hint_x_offset = child.width / 2 - hint_width / 2
                hint_y_offset = child.height / 2 - hint_height / 2

                hint_x = x_loc + hint_x_offset
                hint_y = y_loc + hint_y_offset

                cr.translate(hint_x, hint_y)
                # adding offsets so that clicks sent happen in center of hints
                # (matching the position of hints on elements)
                self.hints_drawn_offsets[hint_value] = (
                    hint_x_offset + hint_width / 2,
                    hint_y_offset + hint_height / 2,
                )

                cr.rectangle(0, 0, hint_width, hint_height)
                cr.set_source_rgba(
                    self.hint_background_r,
                    self.hint_background_g,
                    self.hint_background_b,
                    self.hint_background_a,
                )
                cr.fill()

                hint_text_position = (
                    (hint_width / 2) - (width / 2 + x_bearing),
                    (hint_height / 2) - (height / 2 + y_bearing),
                )

                # draw hint
                cr.move_to(*hint_text_position)
                cr.set_source_rgba(
                    self.hint_font_r,
                    self.hint_font_g,
                    self.hint_font_b,
                    self.hint_font_a,
                )
                cr.show_text(utf8)

                cr.move_to(*hint_text_position)
                cr.set_source_rgba(
                    self.hint_pressed_font_r,
                    self.hint_pressed_font_g,
                    self.hint_pressed_font_b,
                    self.hint_pressed_font_a,
                )
                cr.show_text(hint_state)

                cr.close_path()
                cr.restore()

    def update_hints(self, next_char: str):
        """Update hints on screen to eliminate options.

        :param next_char: Next character for hint_selector_state.
        """

        updated_hints = {
            hint: child
            for hint, child in self.hints.items()
            if hint.startswith(self.hint_selector_state + next_char)
        }

        if updated_hints:
            self.hints = updated_hints
            self.hint_selector_state += next_char

        self.drawing_area.queue_draw()

    def on_key_press(self, _, event):
        """Handle key presses :param event: Event object."""
        keymap = Gdk.Keymap.get_for_display(Gdk.Display.get_default())

        # if keyval is bound, keyval, effective_group, level, consumed_modifiers
        *_, consumed_modifiers = keymap.translate_keyboard_state(
            event.hardware_keycode,
            Gdk.ModifierType(event.state & ~Gdk.ModifierType.LOCK_MASK),
            1,
        )

        modifiers = (
            # current state, default mod mask, consumed modifiers
            event.state
            & Gtk.accelerator_get_default_mod_mask()
            & ~consumed_modifiers
        )

        keyval_lower = Gdk.keyval_to_lower(event.keyval)

        if keyval_lower == self.exit_key:
            self._finish()
            return

        if modifiers == self.hover_modifier:
            self.mouse_action.update({"action": "hover"})

        if modifiers == self.grab_modifier:
            self.mouse_action.update({"action": "grab"})

        if keyval_lower != event.keyval:
            self.mouse_action.update({"action": "click", "button": MouseButton.RIGHT})

        hint_chr = chr(keyval_lower)

        if hint_chr.isdigit():
            self.mouse_action.update(
                {"repeat": int(f"{self.mouse_action.get('repeat', '')}{hint_chr}")}
            )

        self.update_hints(hint_chr)

        if len(self.hints) == 1:
            x, y = self.hints[self.hint_selector_state].absolute_position
            x_offset, y_offset = self.hints_drawn_offsets[self.hint_selector_state]
            self.mouse_action.update(
                {
                    "action": self.mouse_action.get("action", "click"),
                    "x": x + x_offset,
                    "y": y + y_offset,
                    "repeat": self.mouse_action.get("repeat", 1),
                    "button": self.mouse_action.get("button", MouseButton.LEFT),
                }
            )
            # Finish last so the completion callback runs with a fully populated mouse_action.
            self._finish()

    def on_show(self, window):
        """Setup window on show.

        Force keyboard grab to listen for keybaord events. Hide mouse so
        it does not block hints.

        :param window: Gtk Window object.
        """

        if not self.is_wayland:
            seat = Gdk.Display.get_default().get_default_seat()
            gdk_window = window.get_window()
            while (
                seat.grab(
                    gdk_window,
                    Gdk.SeatCapabilities.KEYBOARD,
                    False,
                    None,
                    None,
                    None,
                )
                != Gdk.GrabStatus.SUCCESS
            ):
                pass

        Gdk.Window.set_cursor(
            self.get_window(),  # Gdk Window object
            Gdk.Cursor.new_from_name(Gdk.Display.get_default(), "none"),
        )
