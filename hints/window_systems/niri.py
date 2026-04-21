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

        tile_pos = layout.get("tile_pos_in_workspace_view")
        if tile_pos is not None:
            # Floating windows: niri populates tile_pos_in_workspace_view
            x = output_logical["x"] + int(tile_pos[0])
            y = output_logical["y"] + int(tile_pos[1])
            width = layout["window_size"][0]
            height = layout["window_size"][1]
        else:
            # Tiled windows: niri IPC does not expose the screen position
            # (https://github.com/niri-wm/niri/issues/2381). Fall back to
            # the full output geometry so hints still scans the screen.
            x = output_logical["x"]
            y = output_logical["y"]
            width = output_logical["width"]
            height = output_logical["height"]

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
