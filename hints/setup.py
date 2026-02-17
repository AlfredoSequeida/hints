from importlib.resources import as_file, files
from os import getenv, getuid
from pathlib import Path
from subprocess import run
from sys import exit as sys_exit
from typing import Callable

from rich import print
from rich.tree import Tree

from hints.window_systems.window_system_type import (
    WindowSystemType,
    get_window_system_type,
)

ENVIRONMENT_VARIABLES_FILE = Path("/etc/environment")
UDEV_RULES_FILE = Path("/etc/udev/rules.d/80-hints.rules")
USER = getenv("SUDO_USER", "$SUDO_USER")

Changes = list[str] | None
SetupFunction = Callable[..., Changes]

tree = Tree("\nChanges")


def setup_function(setup_description: str, post_setup_instruction: str = ""):
    def decorator(func: SetupFunction):
        def wrapper():
            # tree_root = tree.add(func.__name__.replace("_", " ").title())
            print(f":white_heavy_check_mark: {func.__name__.replace('_', ' ').title()}")

            if changes := func():
                for change in changes:
                    # tree_root.add(change)
                    print(f"   {change}")
            else:
                # tree_root.add("No changes made.")
                print("   No changes made.")

        wrapper.setup_description = setup_description
        wrapper.post_setup_instruction = post_setup_instruction

        return wrapper

    return decorator


@setup_function(
    f"Add any missing accessibility environment variables to {ENVIRONMENT_VARIABLES_FILE}."
)
def setup_accessibility_variables() -> Changes:
    changes = []
    expected_env_vars = {
        "ACCESSIBILITY_ENABLED": "1",
        "GTK_MODULES": "gail:atk-bridge",
        "OOO_FORCE_DESKTOP": "gnome",
        "GNOME_ACCESSIBILITY": "1",
        "QT_ACCESSIBILITY": "1",
        "QT_LINUX_ACCESSIBILITY_ALWAYS_ON": "1",
    }

    ENVIRONMENT_VARIABLES_FILE.touch(exist_ok=True)
    env_vars_to_add = ""

    for expected_key, expected_val in expected_env_vars.items():
        if getenv(expected_key) != expected_val:
            env_vars_to_add += f"{expected_key}={expected_val}\n"
            changes.append(
                f"Added {expected_key}={expected_val} to {ENVIRONMENT_VARIABLES_FILE}"
            )

    if env_vars_to_add:
        with open(ENVIRONMENT_VARIABLES_FILE, "a") as _f:
            _f.write("# Added by `hints --setup`\n" + env_vars_to_add)

        return changes


@setup_function("Load the uinput module and set it to load on boot.")
def setup_uinput_module() -> Changes:
    run(
        [
            'sudo modprobe uinput && echo "uinput" | '
            "sudo tee /etc/modules-load.d/uinput.conf > /dev/null",
        ],
        shell=True,
        check=True,
    )

    return ["Loaded the uninput module and set it to load on boot."]


@setup_function(
    f"Create udev rules in {UDEV_RULES_FILE}, add [bold]{USER}[/bold] to the "
    "[bold]input[/bold] group."
)
def setup_udev_rules() -> Changes:
    UDEV_RULES_FILE.parent.mkdir(parents=True, exist_ok=True)

    changes = []

    with open(UDEV_RULES_FILE, "w") as _f:
        _f.write('KERNEL=="uinput", GROUP="input", MODE:="0660"')

    changes.append(f"Added {UDEV_RULES_FILE}")

    run(["sudo", "usermod", "-a", "-G", "input", USER], check=True)

    changes.append(f"Added [bold]{USER}[/bold] to the [bold]input[/bold] group.")

    return changes


@setup_function("Reload services, enable and start the hintsd daemon.")
def setup_hintsd() -> Changes:
    changes = []
    systemctl_cmds = [["daemon-reload"], ["enable", "hintsd"], ["start", "hintsd"]]

    for cmd in systemctl_cmds:
        run(["systemctl", f"--machine={USER}@.host", "--user"] + cmd, check=True)
        changes.append(f"systemctl {(" ").join(cmd)}")

    return changes


@setup_function(
    "Install the Gnome hints plugin.",
    "Run: 'gnome-extensions enable hints@realh.co.uk'",
)
def setup_gnome_plugin() -> Changes:
    changes = []
    gnome_extensions_dir = Path(f"/home/{USER}/.local/share/gnome-shell/extensions")
    gnome_extensions_dir.mkdir(exist_ok=True, parents=True)

    with as_file(
        files("hints") / "extensions/gnome/hints@realh.co.uk"
    ) as hints_extension_path:
        run(
            ["ln", "-sf", str(hints_extension_path), str(gnome_extensions_dir)],
            check=True,
        )
        changes.append(f"Symlinked hints Gnome extension to {gnome_extensions_dir}")

    return changes


def is_super_user() -> bool:
    """Check if user is super user.
    :return: If user is super use.
    """
    return getuid() == 0


def is_wayland_gnome() -> bool:
    """Check if desktop session is Wayland Gnome.
    :return: If desktop session is Wayland Gnome.
    """

    return get_window_system_type() == WindowSystemType.WAYLAND and "GNOME" in getenv(
        "XDG_CURRENT_DESKTOP", ""
    )


def should_continue(setup_functions: list[SetupFunction]):
    """Prompt user to continue based on changes that will take place.
    :param setup_functions: setup functions.
    """

    print("\nThis command will do the following:")

    for _setup_function in setup_functions:
        print(f"- {_setup_function.setup_description}")

    return input("\nDo you want to continue? (y/n): ").lower() in {"yes", "y"}


def show_post_setup_instructions(setup_functions: list[SetupFunction]):
    """Show post setup instructions and prompt for reboot.
    :param setup_functions: setup functions.
    """

    print("\n:glowing_star: All done, A reboot is recommended.")

    post_setup_instructions = ""

    for _setup_function in setup_functions:
        post_setup_instruction = _setup_function.post_setup_instruction
        if post_setup_instruction:
            post_setup_instructions += f"- {post_setup_instruction}\n"

    if post_setup_instructions:
        print("\nAfter rebooting:\n")
        print(post_setup_instructions)

    reboot()


def execute_setup_functions(setup_functions: list[SetupFunction]):
    """Execute setup functions.
    :param setup_functions: setup functions.
    """

    for _setup_function in setup_functions:
        _setup_function()


def reboot():
    """Prompt user to reboot and reboot."""
    if input(
        "\nYou should save any work before rebooting."
        " Do you want to reboot now? (y/n): "
    ).lower() in {
        "yes",
        "y",
    }:
        run(["sudo", "reboot"], check=True)


def run_guided_setup():
    """Guided setup to setup hints."""
    if not is_super_user():
        print(
            "This command needs to run as super user. Try again with:\n\n"
            + run(
                [
                    'echo "sudo env XDG_SESSION_TYPE=$XDG_SESSION_TYPE'
                    " env XDG_CURRENT_DESKTOP=$XDG_CURRENT_DESKTOP"
                    " $(whereis hints | awk '{print $2}') --setup\""
                ],
                shell=True,
                capture_output=True,
                check=True,
            ).stdout.decode("utf-8")
        )
        sys_exit(1)
    else:
        setup_functions = [
            setup_accessibility_variables,
            setup_uinput_module,
            setup_udev_rules,
            setup_hintsd,
        ]
        if is_wayland_gnome():
            setup_functions.append(setup_gnome_plugin)
        if should_continue(setup_functions):
            print()
            execute_setup_functions(setup_functions)
            show_post_setup_instructions(setup_functions)
