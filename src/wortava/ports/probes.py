from dataclasses import dataclass
from typing import Protocol


class UnsupportedPlatform(RuntimeError):
    """The requested probe is unavailable on the current operating system."""


@dataclass(frozen=True, slots=True)
class ProcessObservation:
    name: str
    installed: bool | None
    running: bool
    pid: int | None
    executable: str | None
    version: str | None


@dataclass(frozen=True, slots=True)
class ObsObservation:
    connected: bool
    current_scene: str | None
    virtual_camera_active: bool | None


@dataclass(frozen=True, slots=True)
class MixerObservation:
    configured: bool
    reachable: bool | None
    model: str | None
    address: str | None


@dataclass(frozen=True, slots=True)
class AudioEndpoint:
    endpoint_id: str
    name: str
    direction: str
    active: bool
    default_multimedia: bool
    default_communications: bool


class ProcessProbe(Protocol):
    async def inspect_processes(self) -> tuple[ProcessObservation, ...]: ...


class ObsProbe(Protocol):
    async def inspect_obs(self) -> ObsObservation: ...


class MixerProbe(Protocol):
    async def inspect_mixer(self) -> MixerObservation: ...


class AudioProbe(Protocol):
    async def inspect_audio(self) -> tuple[AudioEndpoint, ...]: ...
