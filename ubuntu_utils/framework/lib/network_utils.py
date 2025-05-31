import errno
import socket
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .other_utils import is_sys
from .serialization_utils import Serializer


def _find(
    func: Callable,
    try_ports: list[int] = None,
    exclude_ports: list[int] = None,
    try_range: tuple[int, int] = None,
) -> int | None:
    ports = (try_ports or []) + list(range(*try_range))
    exclude_ports = exclude_ports or []
    for port in ports:
        if port not in exclude_ports:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    result = func(s, port)
                    if result is not None:
                        return result
            except OSError:
                continue


def find_running_port(
    host: str = "127.0.0.1",
    try_ports: list[int] = None,
    exclude_ports: list[int] = None,
    try_range: tuple[int, int] = None,
    timeout: float = 0.5,
) -> int | None:
    def _test(s: socket.socket, port: int):
        s.settimeout(timeout)
        result = s.connect_ex((host, port))
        if result == 0:
            return port

    return _find(_test, try_ports, exclude_ports, try_range)


def find_free_port(
    host: str = "127.0.0.1",
    try_ports: list[int] = None,
    exclude_ports: list[int] = None,
    try_range: tuple[int, int] = (1024, 65536),
) -> int | None:
    def _test(s: socket.socket, port: int):
        s.bind((host, port))
        return port

    return _find(_test, try_ports, exclude_ports, try_range)


class ClientSocket:
    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 12345,
        client_socket: socket.socket = None,
        client_host: str = None,
        client_port: int = 12345,
    ):
        self.host = host
        self.port = port
        self._serializer = Serializer()
        self.client_host = client_host
        self.client_port = client_port
        self.client_socket = client_socket

        self._length_bytes = 5

        if self.client_socket:
            if is_sys(is_sys.WINDOWS):
                self.client_socket.setblocking(True)
            self.client_socket.setsockopt(
                socket.SOL_SOCKET, socket.SO_RCVBUF, 32 * 1024 * 1024
            )

    def connect(self) -> None:
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.setsockopt(
            socket.SOL_SOCKET, socket.SO_RCVBUF, 32 * 1024 * 1024
        )
        # use the certain address of the client to connect the server
        if self.client_host and self.client_port:
            self.client_socket.bind((self.client_host, self.client_port))
        self.client_socket.connect((self.host, self.port))

    def _get_length(self, data: bytes) -> bytes:
        # for 5 bytes unsigned int, the max data length is 2**40 - 1, namely about 1tb
        bytes_result = len(data).to_bytes(self._length_bytes, byteorder="big")
        return bytes_result

    def _recv_length(self) -> int:
        byte_result = self.client_socket.recv(self._length_bytes)
        return int.from_bytes(byte_result, byteorder="big")

    def send(self, data: bytes):
        return self.client_socket.sendall(self._get_length(data) + data)

    def recv(self) -> bytes:
        length = self._recv_length()
        data = bytearray()
        while len(data) < length:
            new_data = self.client_socket.recv(length - len(data))
            data += new_data
            if (
                len(new_data) == 0
            ):  # avoid the sender ended by accident, lead to get into the infinite loop
                return bytes(data)
        return bytes(data)

    def recvf(self, output_path: str | Path, bufsize: int = 1024 * 1024 * 16) -> None:
        with open(output_path, "wb") as f:
            while True:
                data = self.client_socket.recv(bufsize)
                if not data:
                    break
                f.write(data)

    def sendf(self, input_path: str | Path, bufsize: int = 1024 * 1024 * 16) -> None:
        with open(input_path, "rb") as f:
            while True:
                data = f.read(bufsize)
                if not data:
                    break
                self.client_socket.send(data)

    def send_pickle(self, data: Any) -> None:
        return self.send(self._serializer.dump_pickle(data))

    def recv_pickle(self) -> Any | None:
        if data := self.recv():
            return self._serializer.load_pickle(data)

    def close(self) -> None:
        return self.client_socket.close()


class ServerSocket:
    def __init__(self, host: str = "127.0.0.1", port: int = 12345, backlog: int = 64):
        self.host = host
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(backlog)
        self.server_socket.setblocking(False)

    def accept(self) -> tuple[ClientSocket, Any] | tuple[None, None]:
        while True:
            try:
                client_socket, addr = self.server_socket.accept()
                return ClientSocket(client_socket=client_socket), addr
            except OSError as e:
                if e.errno == errno.EWOULDBLOCK or e.errno == errno.EAGAIN:
                    time.sleep(0.01)
                    continue
                elif e.errno == errno.EBADF:
                    return None, None
                elif is_sys(is_sys.WINDOWS):
                    if e.errno == errno.WSAENOTSOCK:
                        return None, None
                raise e

    def handle(self, handler: Callable, *args, **kwargs) -> None:
        def _handle():
            while True:
                client_socket, addr = self.accept()
                if not client_socket:
                    break

                def wrapped_handler(sock, address, *a, **kw):
                    try:
                        handler(sock, address, *a, **kw)
                    finally:
                        sock.close()  # make sure to close the socket

                handle_thread = threading.Thread(
                    target=wrapped_handler,
                    args=(client_socket, addr, *args),
                    kwargs=kwargs,
                )
                handle_thread.daemon = True
                handle_thread.start()

        threading.Thread(target=_handle, daemon=True).start()

    def close(self) -> None:
        self.server_socket.close()
