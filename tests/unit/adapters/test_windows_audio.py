import builtins
from typing import Any

import pytest

from wortava.adapters.windows.audio import UnsupportedPlatform, WindowsAudioProbe
from wortava.ports.probes import AudioEndpoint


class FakeDevice:
    def __init__(self, endpoint_id: str, name: str, state: int) -> None:
        self.id = endpoint_id
        self.FriendlyName = name
        self.state = state


class FakeAudioUtilities:
    @staticmethod
    def GetAllDevices() -> list[FakeDevice]:
        return [
            FakeDevice("render-id", "Main Speakers", 1),
            FakeDevice("capture-id", "Room Microphone", 1),
            FakeDevice("disabled-id", "Unused Output", 2),
        ]

    @staticmethod
    def GetEndpointDataFlow(endpoint_id: str, output_type: int) -> int:
        assert output_type == 1
        return {"render-id": 0, "capture-id": 1, "disabled-id": 0}[endpoint_id]

    @staticmethod
    def GetDeviceEnumerator() -> "FakeEnumerator":
        return FakeEnumerator()


class FakeDefaultDevice:
    def __init__(self, endpoint_id: str) -> None:
        self.id = endpoint_id


class FakeEnumerator:
    def GetDefaultAudioEndpoint(self, flow: int, role: int) -> FakeDefaultDevice:
        endpoint_id = {
            (0, 1): "render-id",
            (0, 2): "disabled-id",
            (1, 1): "other-capture",
            (1, 2): "capture-id",
        }[(flow, role)]
        return FakeDefaultDevice(endpoint_id)


class FakeDefaults:
    def endpoint_id(self, direction: str, role: str) -> str | None:
        return {
            ("render", "multimedia"): "render-id",
            ("render", "communications"): "disabled-id",
            ("capture", "multimedia"): "other-capture",
            ("capture", "communications"): "capture-id",
        }[(direction, role)]


async def run_inline(operation: Any) -> Any:
    return operation()


@pytest.mark.asyncio
async def test_maps_endpoint_inventory_and_default_roles() -> None:
    lifecycle: list[str] = []
    probe = WindowsAudioProbe(
        FakeAudioUtilities,
        initialize_com=lambda: lifecycle.append("initialize"),
        uninitialize_com=lambda: lifecycle.append("uninitialize"),
        run_sync=run_inline,
        platform="win32",
    )

    assert await probe.inspect_audio() == (
        AudioEndpoint("render-id", "Main Speakers", "render", True, True, False),
        AudioEndpoint("capture-id", "Room Microphone", "capture", True, False, True),
        AudioEndpoint("disabled-id", "Unused Output", "render", False, False, True),
    )
    assert lifecycle == ["initialize", "uninitialize"]


@pytest.mark.asyncio
async def test_missing_default_role_does_not_abort_inventory() -> None:
    class MissingCaptureDefaults(FakeDefaults):
        def endpoint_id(self, direction: str, role: str) -> str | None:
            if direction == "capture":
                return None
            return super().endpoint_id(direction, role)

    probe = WindowsAudioProbe(
        FakeAudioUtilities,
        default_roles=MissingCaptureDefaults(),
        run_sync=run_inline,
        platform="win32",
    )

    endpoints = await probe.inspect_audio()

    capture = next(item for item in endpoints if item.direction == "capture")
    assert capture.default_multimedia is False
    assert capture.default_communications is False


@pytest.mark.asyncio
async def test_non_windows_rejects_before_importing_pycaw(monkeypatch: pytest.MonkeyPatch) -> None:
    imported: list[str] = []
    real_import = builtins.__import__

    def recording_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name.startswith(("pycaw", "comtypes")):
            imported.append(name)
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", recording_import)
    probe = WindowsAudioProbe(platform="linux", run_sync=run_inline)

    with pytest.raises(UnsupportedPlatform, match="Windows audio inventory is unsupported"):
        await probe.inspect_audio()

    assert imported == []


@pytest.mark.asyncio
async def test_com_cleanup_runs_when_inventory_fails() -> None:
    lifecycle: list[str] = []

    class BrokenUtilities:
        @staticmethod
        def GetAllDevices() -> list[FakeDevice]:
            raise RuntimeError("vendor detail")

    probe = WindowsAudioProbe(
        BrokenUtilities,
        default_roles=FakeDefaults(),
        initialize_com=lambda: lifecycle.append("initialize"),
        uninitialize_com=lambda: lifecycle.append("uninitialize"),
        run_sync=run_inline,
        platform="win32",
    )

    with pytest.raises(RuntimeError, match="vendor detail"):
        await probe.inspect_audio()

    assert lifecycle == ["initialize", "uninitialize"]
