import socket

import pytest

from tests.conftest import NetworkBlockedError


def test_create_connection_is_refused() -> None:
    with pytest.raises(NetworkBlockedError):
        socket.create_connection(("example.com", 80))


def test_raw_socket_connect_is_refused() -> None:
    with socket.socket() as sock, pytest.raises(NetworkBlockedError):
        sock.connect(("93.184.216.34", 80))
