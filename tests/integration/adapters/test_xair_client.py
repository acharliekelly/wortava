import socket
import threading
from collections.abc import Callable
from typing import Any

import pytest
from pythonosc.osc_message_builder import OscMessageBuilder
from pythonosc.osc_packet import OscPacket

from wortava.adapters.xair.client import (
    MixerProtocolError,
    MixerUnavailable,
    XAirOscProbe,
)
from wortava.config.models import MixerSettings
from wortava.ports.probes import MixerObservation


async def run_inline(operation: Any) -> Any:
    return operation()


class LocalOscDevice:
    def __init__(self, response: Callable[[], bytes] | None) -> None:
        self._response = response
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._socket.bind(("127.0.0.1", 0))
        self.port = self._socket.getsockname()[1]
        self.requests: list[str] = []
        self._thread = threading.Thread(target=self._serve_once)

    def __enter__(self) -> "LocalOscDevice":
        self._thread.start()
        return self

    def __exit__(self, *_args: object) -> None:
        self._thread.join(timeout=1)
        self._socket.close()

    def _serve_once(self) -> None:
        request, sender = self._socket.recvfrom(4096)
        packet = OscPacket(request)
        self.requests.extend(message.message.address for message in packet.messages)
        if self._response is not None:
            self._socket.sendto(self._response(), sender)


def info_response() -> bytes:
    builder = OscMessageBuilder(address="/info")
    for value in ("V1.23", "Wortava Fake Mixer", "XR18", "1.20"):
        builder.add_arg(value)
    return builder.build().dgram


@pytest.mark.asyncio
async def test_probe_discovers_xr18_from_read_only_info_response() -> None:
    with LocalOscDevice(info_response) as device:
        probe = XAirOscProbe(
            MixerSettings(host="127.0.0.1", port=device.port, timeout_seconds=0.2),
            run_sync=run_inline,
        )

        observation = await probe.inspect_mixer()

    assert observation == MixerObservation(True, True, "XR18", "127.0.0.1")
    assert device.requests == ["/info"]


@pytest.mark.asyncio
async def test_probe_returns_typed_sanitized_error_when_info_times_out() -> None:
    host = "127.0.0.1"
    with LocalOscDevice(None) as device:
        probe = XAirOscProbe(
            MixerSettings(host=host, port=device.port, timeout_seconds=0.01),
            run_sync=run_inline,
        )

        with pytest.raises(MixerUnavailable) as caught:
            await probe.inspect_mixer()

    assert host not in str(caught.value)
    assert caught.value.__cause__ is None
    assert caught.value.__context__ is None
    assert device.requests == ["/info"]


@pytest.mark.asyncio
async def test_probe_returns_typed_sanitized_error_for_malformed_response() -> None:
    with LocalOscDevice(lambda: b"not-an-osc-packet") as device:
        probe = XAirOscProbe(
            MixerSettings(host="127.0.0.1", port=device.port, timeout_seconds=0.2),
            run_sync=run_inline,
        )

        with pytest.raises(MixerProtocolError) as caught:
            await probe.inspect_mixer()

    assert "not-an-osc-packet" not in str(caught.value)
    assert caught.value.__cause__ is None
    assert caught.value.__context__ is None
    assert device.requests == ["/info"]


@pytest.mark.asyncio
async def test_probe_with_no_host_is_unconfigured_without_opening_socket() -> None:
    def forbidden_socket_factory(*_args: object) -> socket.socket:
        raise AssertionError("socket factory must not be called")

    probe = XAirOscProbe(
        MixerSettings(host=None),
        socket_factory=forbidden_socket_factory,
        run_sync=run_inline,
    )

    assert await probe.inspect_mixer() == MixerObservation(False, None, None, None)
