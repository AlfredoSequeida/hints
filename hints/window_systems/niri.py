"""Niri window system."""

from json import loads
from subprocess import run

from hints.window_systems.window_system import WindowSystem


class Niri(WindowSystem):
    """Niri Window system class."""

    def __init__(self):
        super().__init__()
        self._focused_window = self._get_focused_window()
        self._focused_output = self._get_focused_output()

    def _get_focused_window(self):
        result = run(
            ["niri", "msg", "-j", "focused-window"],
            capture_output=True,
            check=True,
        )
        return loads(result.stdout.decode("utf-8"))

    def _get_focused_output(self):
        result = run(
            ["niri", "msg", "-j", "focused-output"],
            capture_output=True,
            check=True,
        )
        return loads(result.stdout.decode("utf-8"))

    @property
    def window_system_name(self) -> str:
        """Get the name of the window system.

        :return: The window system name
        """
        return "niri"

    @property
    def focused_window_extents(self) -> tuple[int, int, int, int]:
        """Get active window extents.

        :return: Active window extents (x, y, width, height).
        """
        output_logical = self._focused_output["logical"]
        layout = self._focused_window["layout"]

        width = layout["window_size"][0]
        height = layout["window_size"][1]

        tile_pos = layout.get("tile_pos_in_workspace_view")
        if tile_pos is not None:
            x = output_logical["x"] + int(tile_pos[0])
            y = output_logical["y"] + int(tile_pos[1])
        else:
            # tile_pos_in_workspace_view can be null when the window is
            # the only visible column. Derive position from the output
            # geometry and tile/window offsets.
            tile_w = layout["tile_size"][0]
            offset_x = layout["window_offset_in_tile"][0]
            offset_y = layout["window_offset_in_tile"][1]

            # Center the tile horizontally within the output (niri's default
            # behavior for a single focused column).
            x = output_logical["x"] + int(
                (output_logical["width"] - tile_w) / 2 + offset_x
            )

            # Vertical: the bar (if any) takes the space that the tile
            # doesn't occupy. Assume the strut is at the top.
            bar_height = output_logical["height"] - int(layout["tile_size"][1])
            y = output_logical["y"] + bar_height + int(offset_y)

        return (x, y, width, height)

    @property
    def focused_window_pid(self) -> int:
        """Get Process ID corresponding to the focused window.

        :return: Process ID of focused window.
        """
        return self._focused_window["pid"]

    @property
    def focused_applicaiton_name(self) -> str:
        """Get focused application name.

        This name is the name used to identify applications for per-
        application rules.

        :return: Focused application name.
        """
        return self._focused_window["app_id"]
