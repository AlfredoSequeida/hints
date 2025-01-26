"""Plasma 6/Kwin window system."""

from datetime import datetime
from importlib.resources import as_file, files
from json import loads
from subprocess import run
from typing import Any

import dbus
from hints.window_systems.window_system import WindowSystem


class Plasmashell(WindowSystem):
    """Sway Window system class."""

    def __init__(self):
        super().__init__()

        with as_file(
            files("hints") / "scripts/kwin/active_window_information.mjs"
        ) as path:
            self._active_window = self._run_kwin_script(str(path))
            print(self._active_window)

    def _run_kwin_script(self, kwin_script_path: str) -> Any:
        """Run KWin script at the given path that returns output in JSON format
        and return the script output converted to a Python datastructure.

        :param kwin_script_path: Path to Kwin script.
        """
        # load the script, the method returns the script number/ID
        session_bus = dbus.SessionBus()
        scripting_dbus_object = session_bus.get_object("org.kde.KWin", "/Scripting")
        scripting_interface = dbus.Interface(
            scripting_dbus_object, "org.kde.kwin.Scripting"
        )
        script_id = scripting_interface.loadScript(kwin_script_path)

        # remember time before running the script, for retrieving relevant journal content below
        start_time = datetime.now()

        # run the script
        script_object_path = "/Scripting/Script" + str(script_id)

        script_dbus_object = session_bus.get_object("org.kde.KWin", script_object_path)
        script_interface = dbus.Interface(script_dbus_object, "org.kde.kwin.Script")
        script_interface.run()

        comm = "kwin_wayland"
        journalctl_output = (
            run(
                "journalctl _COMM="
                + comm
                + ' --output=cat --since "'
                + str(start_time)
                + '"',
                capture_output=True,
                shell=True,
                check=True,
            )
            .stdout.decode()
            .rstrip()
            .split("\n")
        )
        lines = [line.lstrip("js: ") for line in journalctl_output]
        data_json = "\n".join(lines)
        data = loads(data_json)

        # unload/unregister script again
        script_interface.stop()

        return data

    @property
    def window_system_name(self) -> str:
        """Get the name of the window system.

        This is useful for performing logic specific to a window system.

        :return: The window system name
        """
        return "plasmashell"

    @property
    def focused_window_extents(self) -> tuple[int, int, int, int]:
        """Get active window extents.

        :return: Active window extents (x, y, width, height).
        """
        return tuple(self._active_window["extents"])

    @property
    def focused_window_pid(self) -> int:
        """Get Process ID corresponding to the focused widnow.

        :return: Process ID of focused window.
        """
        return self._active_window["pid"]

    @property
    def focused_applicaiton_name(self) -> str:
        """Get focused application name.

        This name is the name used to identify applications for per-
        application rules.

        :return: Focused application name.
        """
        return self._active_window["name"]
