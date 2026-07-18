import asyncio
import sys
from collections.abc import Awaitable, Callable, Iterable
from typing import Any, Protocol

from wortava.adapters.windows.worker import run_in_spawned_process
from wortava.ports.probes import AudioEndpoint, UnsupportedPlatform


class AudioUtilitiesProtocol(Protocol):
    @staticmethod
    def GetAllDevices() -> Iterable[Any]: ...

    @staticmethod
    def GetEndpointDataFlow(endpoint_id: str, output_type: int) -> Any: ...


class DefaultRoleResolver(Protocol):
    def endpoint_id(self, direction: str, role: str) -> str | None: ...


type AudioEndpoints = tuple[AudioEndpoint, ...]
type SyncRunner = Callable[[Callable[[], AudioEndpoints]], Awaitable[AudioEndpoints]]


async def _run_in_thread(operation: Callable[[], AudioEndpoints]) -> AudioEndpoints:
    return await asyncio.to_thread(operation)


class _CoreAudioDefaultRoles:
    """Narrow, read-only wrapper around IMMDeviceEnumerator default-role queries."""

    def __init__(
        self,
        audio_utilities: Any,
        render_flow: Any,
        capture_flow: Any,
        multimedia_role: Any,
        communications_role: Any,
    ) -> None:
        self._audio_utilities = audio_utilities
        self._flows = {"render": render_flow, "capture": capture_flow}
        self._roles = {
            "multimedia": multimedia_role,
            "communications": communications_role,
        }

    def endpoint_id(self, direction: str, role: str) -> str | None:
        try:
            enumerator = self._audio_utilities.GetDeviceEnumerator()
            device = enumerator.GetDefaultAudioEndpoint(
                self._flows[direction], self._roles[role]
            )
        except Exception:
            return None
        endpoint_id = getattr(device, "id", None)
        if endpoint_id is None:
            endpoint_id = device.GetId()
        return str(endpoint_id)


class WindowsAudioProbe:
    def __init__(
        self,
        audio_utilities: AudioUtilitiesProtocol | None = None,
        *,
        default_roles: DefaultRoleResolver | None = None,
        data_flow_render: Any = None,
        data_flow_capture: Any = None,
        device_state_active: Any = None,
        initialize_com: Callable[[], Any] | None = None,
        uninitialize_com: Callable[[], Any] | None = None,
        run_sync: SyncRunner = _run_in_thread,
        platform: str | None = None,
        worker_timeout_seconds: float = 1.5,
    ) -> None:
        self._audio_utilities = audio_utilities
        self._default_roles = default_roles
        self._data_flow_render = data_flow_render
        self._data_flow_capture = data_flow_capture
        self._device_state_active = device_state_active
        self._initialize_com = initialize_com
        self._uninitialize_com = uninitialize_com
        self._run_sync = run_sync
        self._platform = platform
        self._worker_timeout_seconds = worker_timeout_seconds
        self._uses_default_worker = (
            audio_utilities is None
            and default_roles is None
            and initialize_com is None
            and uninitialize_com is None
            and run_sync is _run_in_thread
        )

    async def inspect_audio(self) -> AudioEndpoints:
        if (self._platform or sys.platform) != "win32":
            raise UnsupportedPlatform("Windows audio inventory is unsupported on this platform")
        if self._uses_default_worker:
            result = await run_in_spawned_process(
                _inspect_audio_worker,
                (),
                timeout_seconds=self._worker_timeout_seconds,
            )
            return tuple(result)
        return await self._run_sync(self._inspect_audio_sync)

    def _inspect_audio_sync(self) -> AudioEndpoints:
        utilities, defaults, render, capture, active, initialize, uninitialize = (
            self._dependencies()
        )
        initialize()
        try:
            multimedia = {
                direction: defaults.endpoint_id(direction, "multimedia")
                for direction in ("render", "capture")
            }
            communications = {
                direction: defaults.endpoint_id(direction, "communications")
                for direction in ("render", "capture")
            }
            directions = {render: "render", capture: "capture"}
            endpoints = []
            for device in utilities.GetAllDevices():
                flow = utilities.GetEndpointDataFlow(str(device.id), 1)
                direction = directions[_enum_value(flow)]
                endpoints.append(
                    AudioEndpoint(
                        endpoint_id=str(device.id),
                        name=str(device.FriendlyName),
                        direction=direction,
                        active=_enum_value(device.state) == active,
                        default_multimedia=str(device.id) == multimedia[direction],
                        default_communications=str(device.id) == communications[direction],
                    )
                )
            return tuple(endpoints)
        finally:
            uninitialize()

    def _dependencies(
        self,
    ) -> tuple[
        AudioUtilitiesProtocol,
        DefaultRoleResolver,
        Any,
        Any,
        Any,
        Callable[[], Any],
        Callable[[], Any],
    ]:
        if self._audio_utilities is not None:
            defaults = self._default_roles or _CoreAudioDefaultRoles(
                self._audio_utilities, 0, 1, 1, 2
            )
            return (
                self._audio_utilities,
                defaults,
                0 if self._data_flow_render is None else self._data_flow_render,
                1 if self._data_flow_capture is None else self._data_flow_capture,
                1 if self._device_state_active is None else self._device_state_active,
                self._initialize_com or (lambda: None),
                self._uninitialize_com or (lambda: None),
            )

        from comtypes import CoInitialize, CoUninitialize  # type: ignore[import-not-found]
        from pycaw.constants import (  # type: ignore[import-not-found]
            DEVICE_STATE,
            EDataFlow,
            ERole,
        )
        from pycaw.pycaw import AudioUtilities  # type: ignore[import-not-found]

        defaults = _CoreAudioDefaultRoles(
            AudioUtilities,
            EDataFlow.eRender.value,
            EDataFlow.eCapture.value,
            ERole.eMultimedia.value,
            ERole.eCommunications.value,
        )
        return (
            AudioUtilities,
            defaults,
            EDataFlow.eRender.value,
            EDataFlow.eCapture.value,
            DEVICE_STATE.ACTIVE.value,
            CoInitialize,
            CoUninitialize,
        )


def _enum_value(value: Any) -> Any:
    return getattr(value, "value", value)


def _inspect_audio_worker() -> AudioEndpoints:
    return WindowsAudioProbe(platform="win32", run_sync=_run_in_thread)._inspect_audio_sync()
