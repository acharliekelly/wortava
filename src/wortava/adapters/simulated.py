import asyncio
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from wortava.ports.probes import (
    AudioEndpoint,
    MixerObservation,
    ObsObservation,
    ProcessObservation,
)


@dataclass(slots=True)
class SimulatedProbes:
    data: dict[str, Any]

    @classmethod
    def from_path(cls, path: Path) -> "SimulatedProbes":
        return cls(json.loads(path.read_text(encoding="utf-8")))

    async def _delay(self, section: str) -> None:
        await asyncio.sleep(float(self.data.get(section, {}).get("delay_seconds", 0)))

    async def inspect_processes(self) -> tuple[ProcessObservation, ...]:
        await self._delay("processes")
        return tuple(ProcessObservation(**item) for item in self.data["processes"]["items"])

    async def inspect_obs(self) -> ObsObservation:
        await self._delay("obs")
        return ObsObservation(**self.data["obs"]["observation"])

    async def inspect_mixer(self) -> MixerObservation:
        await self._delay("mixer")
        return MixerObservation(**self.data["mixer"]["observation"])

    async def inspect_audio(self) -> tuple[AudioEndpoint, ...]:
        await self._delay("audio")
        return tuple(AudioEndpoint(**item) for item in self.data["audio"]["items"])
