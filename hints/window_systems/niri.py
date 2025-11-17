"""Niri window system."""

from json import loads
from subprocess import run

from hints.window_systems.window_system import WindowSystem


class Niri(WindowSystem):
    """Niri Window system class."""

    def __init__(self):
        super().__init__()
        self.focused_window = self._get_focused_window_from_niri_msg()
        self.focused_output = self._get_focused_output_from_niri_msg()
        self.windows = None

    def _get_focused_window_from_niri_msg(self):
        focused_window = run(
            ["niri", "msg", "--json", "focused-window"], capture_output=True, check=True
        )
        return loads(focused_window.stdout.decode("utf-8"))

    def _get_focused_output_from_niri_msg(self):
        focused_window = run(
            ["niri", "msg", "--json", "focused-output"], capture_output=True, check=True
        )
        return loads(focused_window.stdout.decode("utf-8"))

    def _get_windows_from_niri_msg(self):
        focused_window = run(
            ["niri", "msg", "--json", "windows"], capture_output=True, check=True
        )
        return loads(focused_window.stdout.decode("utf-8"))

    @property
    def window_system_name(self) -> str:
        """Get the name of the window syste.

        This is useful for performing logic specific to a window system.

        :return: The window system name
        """
        return "Niri"

    @property
    def focused_window_extents(self) -> tuple[int, int, int, int]:
        """Get active window extents.

        :return: Active window extents (x, y, width, height).
        """
        window_layout = self.focused_window["layout"]
        output_logical = self.focused_output["logical"]

        # handling of tiled windows, since niri doesn't provide window position for them
        pos = window_layout["tile_pos_in_workspace_view"]
        gaps = 16 # TODO: get it properly
        strut_left = 25 # TODO: get it properly
        strut_top = 0 # TODO: get it properly
        x = 0
        y = 0
        left_side = False # TODO: get it properly
        if pos is None:
            x_gap = gaps + strut_left
            if left_side:
                x = x_gap
            else:
                x = output_logical["width"] - x_gap - window_layout["tile_size"][0]
            y = gaps + strut_top
        else:
            x, y = pos

        tile_offset_x, tile_offset_y = window_layout["window_offset_in_tile"]
        x += output_logical["x"] + tile_offset_x
        y += output_logical["y"] + tile_offset_y
        width, height = window_layout["window_size"]
        return (x, y, width, height)

    @property
    def focused_window_pid(self) -> int:
        """Get Process ID corresponding to the focused widnow.

        :return: Process ID of focused window.
        """
        return self.focused_window["pid"]

    @property
    def focused_applicaiton_name(self) -> str:
        """Get focused application name.

        This name is the name used to identify applications for per-
        application rules.

        :return: Focused application name.
        """
        return self.focused_window["app_id"]
