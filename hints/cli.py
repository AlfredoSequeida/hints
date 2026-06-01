"""Lean command-line entry point for hints.

At module load this imports only the standard library and the gi-free
``hints.ipc_constants``, so the common hot path -- triggering hint mode in
the already-warm hintsd daemon -- costs interpreter startup plus a socket
round-trip rather than loading GTK/AT-SPI/Wnck (~190ms).

The heavy standalone implementation in ``hints.hints`` is imported lazily
only when needed: the daemon is unreachable, output must go to the user's
terminal (verbose), guided setup, or scroll mode.
"""

from __future__ import annotations

from argparse import ArgumentParser
from pickle import dumps, loads
from socket import AF_UNIX, SOCK_STREAM, socket

from hints import __version__
from hints.ipc_constants import SOCKET_MESSAGE_SIZE, UNIX_DOMAIN_SOCKET_FILE


def trigger_daemon(mode: str, verbose: int) -> dict:
    """Ask the hintsd daemon to show hints.

    :param mode: Hint mode to request.
    :param verbose: Verbosity level to forward to the daemon.
    :return: The daemon's status payload.
    :raises OSError: When the daemon socket is unavailable.
    """
    with socket(AF_UNIX, SOCK_STREAM) as client:
        client.connect(UNIX_DOMAIN_SOCKET_FILE)
        client.sendall(
            dumps(
                {
                    "method": "show_hints",
                    "args": (),
                    "kwargs": {"mode": mode, "verbose": verbose},
                }
            )
        )
        return loads(client.recv(SOCKET_MESSAGE_SIZE))


def _run_standalone():
    """Run the full in-process implementation.

    This pays the GTK/AT-SPI import cost and is used for the daemon-down
    fallback as well as the verbose, scroll, and setup paths.
    """
    from hints.hints import main as standalone_main

    standalone_main()


def main():
    """Hints entry point."""
    parser = ArgumentParser(
        prog="Hints",
        description="Hints lets you navigate GUI applications in Linux without"
        ' your mouse by displaying "hints" you can type on your keyboard to'
        " interact with GUI elements.",
    )
    parser.add_argument(
        "-m",
        "--mode",
        type=str,
        default="hint",
        choices=["hint", "scroll"],
        help="mode to use",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Set verbosity of output. -v shows timing and high-level debug"
        " info; -vv additionally logs per-accessible-element details. Verbose"
        " runs in-process so output reaches this terminal.",
    )
    parser.add_argument(
        "-V",
        "--version",
        action="store_true",
        default=False,
        help="Show the hints version.",
    )
    parser.add_argument(
        "-s", "--setup", action="store_true", default=False, help="Guided hints setup."
    )
    args = parser.parse_args()

    if args.version:
        print(__version__)
        return

    # Fast path: non-verbose hint mode triggers the warm daemon. Any verbose,
    # setup, or scroll invocation runs standalone so its output reaches this
    # terminal and the full feature set is available.
    if args.mode == "hint" and not args.setup and args.verbose == 0:
        try:
            trigger_daemon(args.mode, args.verbose)
            return
        except OSError:
            pass  # Daemon unreachable: fall through to standalone.

    _run_standalone()


if __name__ == "__main__":
    main()
