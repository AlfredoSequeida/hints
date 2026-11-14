from json import load
from typing import Any

from gi import require_version

from hints.constants import CONFIG_PATH, DEFAULT_CONFIG

require_version("Gdk", "3.0")
from gi.repository import Gdk

HintsConfig = dict[str, Any]


def merge_configs(source: HintsConfig, destination: HintsConfig) -> HintsConfig:
    """Deepmerge configs recursively.

    :param source: Source config.
    :param destination: Destination config.
    :return: Destination config.
    """
    for key, value in source.items():
        if isinstance(value, dict):
            node = destination.setdefault(key, {})
            merge_configs(value, node)
        else:
            destination[key] = value

    return destination


def load_config() -> HintsConfig:
    """Load Json config file.

    :return: config object.
    """
    config = {}

    try:
        with open(CONFIG_PATH, encoding="utf-8") as _f:
            config = load(_f)
    except FileNotFoundError:
        pass

    return merge_configs(config, DEFAULT_CONFIG)


def _lowercase_keyval_char(keyval: int) -> str:
    return chr(Gdk.keyval_to_unicode(Gdk.keyval_to_lower(keyval)))


def keyval_in_any_layout(event: Gdk.EventKey, expected_chars: str) -> int:
    """Resolve a key press in whichever keyboard layout produces an expected character.

    :param event: Key press event.
    :param expected_chars: Expected characters.
    :return: Matching keyval, or the event's keyval.
    """
    if _lowercase_keyval_char(event.keyval) in expected_chars:
        return event.keyval

    keymap = Gdk.Keymap.get_for_display(Gdk.Display.get_default())
    found, keys, _ = keymap.get_entries_for_keycode(event.hardware_keycode)
    if not found:
        return event.keyval

    state_without_caps_lock = Gdk.ModifierType(
        event.state & ~Gdk.ModifierType.LOCK_MASK
    )
    layout_indexes = sorted({key.group for key in keys})
    for layout_index in layout_indexes:
        bound, layout_keyval, *_ = keymap.translate_keyboard_state(
            event.hardware_keycode, state_without_caps_lock, layout_index
        )
        if bound and _lowercase_keyval_char(layout_keyval) in expected_chars:
            return layout_keyval

    return event.keyval
