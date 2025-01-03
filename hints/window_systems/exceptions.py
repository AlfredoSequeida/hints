"""Window system exceptions."""

from typing import Iterable


class CouldNotIdentifyWindowSystemType(Exception):
    """Could not identify window sytem type exception."""

    def __str__(self):
        """String representation of exception."""
        return (
            "Could not identify Window System Type. Is the XDG_SESSION_TYPE"
            " environment variable set?"
        )


class WindowSystemNotSupported(Exception):
    """Window System not supported exception."""

    def __init__(self, supported_wms: Iterable[str]):
        """Exception constructor.

        :param window_system_name: The name of the window system that is
            not supported.
        """
        super().__init__()
        self.supported_wms = supported_wms

    def __str__(self) -> str:
        """String representation of exception."""
        return (
            "This window system is not supported, hints only supports one of: "
            f" {", ".join(self.supported_wms)}. To request support open an"
            " issue: https://github.com/AlfredoSequeida/hints/issues."
        )
