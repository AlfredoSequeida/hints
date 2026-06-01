"""Mouse functions.

This module is a skeleton and does not contain any of the mouse logic.
The mouse logic lives in service.py. This module communicates with
the hintsd service via a Unix Domain Socket for Interprocess
Communication.
"""

from __future__ import annotations

from pickle import dumps, loads
from socket import AF_UNIX, SOCK_STREAM, socket
from typing import TYPE_CHECKING, Any

from hints.constants import SOCKET_MESSAGE_SIZE, UNIX_DOMAIN_SOCKET_FILE

KEY_PRESS_STATE: dict[str, Any] = {}

if TYPE_CHECKING:
    from hints.mouse_enums import MouseButton, MouseButtonState, MouseMode


class CouldNotCommunicateWithTheHintsService(Exception):
    """Exception to raise when the hintsd service could not be reached."""

    def __str__(self):
        return "Could not communicate with the hintsd service. Is it running?"


def send_message(method: str, *args, **kwargs) -> Any:
    """Send message to the hintsd service.

    :param method: The name of the method to call.
    :param args: args for the method.
    :param kwargs: kwargs for the method.
    :param return: The payload sent back from the hintsd service.
    :raises CouldNotCommunicateWithTheHintsService: When the sock file
        does not exist (the hintsd service creates this file).
    """
    with socket(AF_UNIX, SOCK_STREAM) as client:
        client.connect(UNIX_DOMAIN_SOCKET_FILE)
        client.sendall(
            dumps(
                {
                    "method": method,
                    "args": args,
                    "kwargs": kwargs,
                }
            )
        )
        return loads(client.recv(SOCKET_MESSAGE_SIZE))


def scroll(x: int, y: int, *_args, **_kwargs):
    """Scroll event.

    :param x: X scroll direction.
    :param y: Y scroll direction. :param *_args: Extra args to use the
        same interface as move. :param **_kwargs: Extra kwargs to use
        the same interface as move.
    """
    send_message("scroll", x, y, *_args, **_kwargs)


def move(x: int, y: int, absolute: bool = True):
    """Move event.

    :param X: X move direction.
    :param y: Y move direction.
    :param absolute: Whether to move the mouse using an absolute
        position.
    """

    send_message("move", x, y, absolute=absolute)


def click(
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
    :param actions: Actions to use for the click button (button down /
        button up).
    :param repeat: Times to repeat a click.
    :param absolute: Whether the click position is absolute.
    """
    send_message(
        "click",
        x,
        y,
        button.value,
        [button_state.value for button_state in button_states],
        repeat=repeat,
        absolute=absolute,
    )


def do_mouse_action(
    key_press_state: dict[str, Any],
    key: str,
    mode: MouseMode,
):
    """Perform mouse action.

    :param key_press_state: State containing key press event data used
        for ramping up speeds.
    :param key: The key to perform a mouse action for.
    :param mode: The mouse mode.
    """
    return send_message("do_mouse_action", key_press_state, key, mode.value)
