"""Global constant values."""

from os import path

from gi import require_version

# Re-exported for backward compatibility. Defined in a gi-free module so
# lightweight clients can import them without loading GTK/AT-SPI.
from hints.ipc_constants import SOCKET_MESSAGE_SIZE, UNIX_DOMAIN_SOCKET_FILE

require_version("Gdk", "3.0")
require_version("Atspi", "2.0")
from gi.repository import Atspi, Gdk

CONFIG_PATH = path.join(path.expanduser("~"), ".config/hints/config.json")
# Per-element accessibility detail logging. Below DEBUG so that timing/phase
# logs (-v) are not polluted by the extra D-Bus calls these logs require; only
# enabled at -vv.
ELEMENT_DETAIL_LOG_LEVEL = 5
MOUSE_GRAB_PAUSE = 0.2
DEFAULT_CONFIG = {
    "hints": {
        "hint_height": 30,
        "hint_width_padding": 10,
        "hint_font_size": 15,
        "hint_font_face": "Sans",
        "hint_font_r": 0,
        "hint_font_g": 0,
        "hint_font_b": 0,
        "hint_font_a": 1,
        "hint_pressed_font_r": 0.7,
        "hint_pressed_font_g": 0.7,
        "hint_pressed_font_b": 0.4,
        "hint_pressed_font_a": 1,
        "hint_upercase": True,
        "hint_background_r": 1,
        "hint_background_g": 1,
        "hint_background_b": 0.5,
        "hint_background_a": 0.8,
    },
    "backends": {
        "enable": ["atspi", "opencv"],
        "atspi": {
            "application_rules": {
                "default": {
                    "scale_factor": 1,
                    "states": [
                        Atspi.StateType.SENSITIVE,
                        Atspi.StateType.SHOWING,
                    ],
                    "states_match_type": Atspi.CollectionMatchType.ALL,
                    "attributes": {},
                    "attributes_match_type": Atspi.CollectionMatchType.ALL,
                    "roles": [
                        # containers
                        Atspi.Role.PANEL,
                        Atspi.Role.SECTION,
                        Atspi.Role.HTML_CONTAINER,
                        Atspi.Role.FRAME,
                        Atspi.Role.MENU_BAR,
                        Atspi.Role.TOOL_BAR,
                        Atspi.Role.LIST,
                        Atspi.Role.PAGE_TAB_LIST,
                        Atspi.Role.DESCRIPTION_LIST,
                        Atspi.Role.SCROLL_PANE,
                        Atspi.Role.TABLE,
                        Atspi.Role.GROUPING,
                        # text
                        Atspi.Role.STATIC,
                        Atspi.Role.HEADING,
                        Atspi.Role.PARAGRAPH,
                        Atspi.Role.DESCRIPTION_VALUE,
                        # other
                        Atspi.Role.LANDMARK,
                        Atspi.Role.FILLER,
                        Atspi.Role.DESCRIPTION_TERM,
                    ],
                    "roles_match_type": Atspi.CollectionMatchType.NONE,
                },
            },
        },
        "opencv": {
            "preload": False,
            "application_rules": {
                "default": {
                    "kernel_size": 6,
                    "canny_min_val": 100,
                    "canny_max_val": 200,
                }
            },
        },
    },
    "alphabet": "asdfgqwertzxcvbhjklyuiopnm",
    "mouse_move_left": "h",
    "mouse_move_right": "l",
    "mouse_move_up": "k",
    "mouse_move_down": "j",
    "mouse_scroll_left": "h",
    "mouse_scroll_right": "l",
    "mouse_scroll_up": "k",
    "mouse_scroll_down": "j",
    "mouse_move_pixel": 10,
    "mouse_move_pixel_sensitivity": 10,
    "mouse_move_rampup_time": 0.5,
    "mouse_scroll_pixel": 5,
    "mouse_scroll_pixel_sensitivity": 5,
    "mouse_scroll_rampup_time": 0.5,
    "exit_key": Gdk.KEY_Escape,
    "hover_modifier": Gdk.ModifierType.CONTROL_MASK,
    "grab_modifier": Gdk.ModifierType.MOD1_MASK,  # Alt
    "overlay_x_offset": 0,
    "overlay_y_offset": 0,
    "window_system": "",
}
