"""IPC constants shared between hints clients and the hintsd daemon.

This module is intentionally free of GTK/AT-SPI imports so that
lightweight clients (such as the hint trigger) can import it without
paying the cost of loading those libraries.
"""

UNIX_DOMAIN_SOCKET_FILE = "/tmp/hints.socket"
SOCKET_MESSAGE_SIZE = 1024
