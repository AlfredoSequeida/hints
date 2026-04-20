"""Mango window system."""

from subprocess import run

from hints.window_systems.window_system import WindowSystem


def _parse_mmsg(output: str) -> dict[str, str]:
    result = {}
    for line in output.strip().splitlines():
        parts = line.split(None, 2)
        if len(parts) == 3:
            result[parts[1]] = parts[2]
    return result


class Mango(WindowSystem):
    """Mango (MangoWM) window system class."""

    def __init__(self):
        super().__init__()
        self._state = self._query()

    def _query(self) -> dict[str, str]:
        result = run(
            ["mmsg", "-g", "-c", "-x"],
            capture_output=True,
            check=True,
        )
        return _parse_mmsg(result.stdout.decode("utf-8"))

    @property
    def window_system_name(self) -> str:
        return "mango"

    @property
    def focused_window_extents(self) -> tuple[int, int, int, int]:
        return (
            int(self._state["x"]),
            int(self._state["y"]),
            int(self._state["width"]),
            int(self._state["height"]),
        )

    @property
    def focused_window_pid(self) -> int:
        appid = self._state.get("appid", "")
        result = run(
            ["pgrep", "-n", appid],
            capture_output=True,
        )
        return int(result.stdout.strip()) if result.returncode == 0 else -1

    @property
    def focused_applicaiton_name(self) -> str:
        return self._state.get("appid", "")
