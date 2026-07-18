import asyncio
import socket
from collections.abc import Awaitable, Callable
from typing import Protocol

from pythonosc.osc_message_builder import OscMessageBuilder
from pythonosc.osc_packet import OscPacket

from wortava.config.models import MixerSettings
from wortava.ports.probes import MixerObservation


class DatagramSocket(Protocol):
    def settimeout(self, value: float | None) -> None: ...

    def sendto(self, data: bytes, address: tuple[str, int]) -> int: ...

    def recvfrom(self, bufsize: int) -> tuple[bytes, tuple[str, int]]: ...

    def close(self) -> None: ...


type SocketFactory = Callable[[int, int], DatagramSocket]
type SyncRunner = Callable[[Callable[[], MixerObservation]], Awaitable[MixerObservation]]


async def _run_in_thread(operation: Callable[[], MixerObservation]) -> MixerObservation:
    return await asyncio.to_thread(operation)


class MixerUnavailable(RuntimeError):
    """The configured mixer could not be reached within the bounded exchange."""


class MixerProtocolError(RuntimeError):
    """The mixer returned data that was not a documented OSC /info response."""


class XAirOscProbe:
    def __init__(
        self,
        settings: MixerSettings,
        socket_factory: SocketFactory = socket.socket,
        run_sync: SyncRunner = _run_in_thread,
    ) -> None:
        self._settings = settings
        self._socket_factory = socket_factory
        self._run_sync = run_sync

    async def inspect_mixer(self) -> MixerObservation:
        if self._settings.host is None:
            return MixerObservation(False, None, None, None)
        return await self._run_sync(self._inspect_mixer_sync)

    def _inspect_mixer_sync(self) -> MixerObservation:
        host = self._settings.host
        if host is None:
            return MixerObservation(False, None, None, None)

        udp_socket: DatagramSocket | None = None
        response: bytes | None = None
        unavailable = False
        try:
            udp_socket = self._socket_factory(socket.AF_INET, socket.SOCK_DGRAM)
            udp_socket.settimeout(self._settings.timeout_seconds)
            request = OscMessageBuilder(address="/info").build().dgram
            udp_socket.sendto(request, (host, self._settings.port))
            response, _sender = udp_socket.recvfrom(4096)
        except (OSError, TimeoutError):
            unavailable = True
        finally:
            if udp_socket is not None:
                try:
                    udp_socket.close()
                except OSError:
                    pass
        if unavailable or response is None:
            raise MixerUnavailable("Unable to read mixer status")

        model: str | None = None
        invalid_response = False
        try:
            packet = OscPacket(response)
            info_messages = [
                timed.message
                for timed in packet.messages
                if timed.message.address == "/info"
            ]
            if not info_messages:
                raise ValueError("missing /info response")
            arguments = info_messages[0].params
            if len(arguments) < 3 or not isinstance(arguments[2], str):
                raise ValueError("invalid /info response")
            model = arguments[2]
        except Exception:
            invalid_response = True
        if invalid_response or model is None:
            raise MixerProtocolError("Invalid mixer status response")

        return MixerObservation(True, True, model, host)
