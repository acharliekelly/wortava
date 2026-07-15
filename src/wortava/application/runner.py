import asyncio
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from wortava.domain.models import CheckResult, Evidence, Status, Subsystem, ValidationReport
from wortava.ports.probes import (
    AudioEndpoint,
    AudioProbe,
    MixerObservation,
    MixerProbe,
    ObsObservation,
    ObsProbe,
    ProcessObservation,
    ProcessProbe,
)

type Evaluation = tuple[Status, str, tuple[Evidence, ...]]
type CheckOperation = Callable[["ValidationRun"], Awaitable[Evaluation]]


class ValidationRun:
    """Owns lazy subsystem snapshots for exactly one validation run."""

    def __init__(self) -> None:
        self._processes: asyncio.Task[tuple[ProcessObservation, ...]] | None = None
        self._obs: asyncio.Task[ObsObservation] | None = None
        self._mixer: asyncio.Task[MixerObservation] | None = None
        self._audio: asyncio.Task[tuple[AudioEndpoint, ...]] | None = None

    async def processes(self, probe: ProcessProbe) -> tuple[ProcessObservation, ...]:
        if self._processes is None:
            self._processes = asyncio.create_task(probe.inspect_processes())
        return await asyncio.shield(self._processes)

    async def obs(self, probe: ObsProbe) -> ObsObservation:
        if self._obs is None:
            self._obs = asyncio.create_task(probe.inspect_obs())
        return await asyncio.shield(self._obs)

    async def mixer(self, probe: MixerProbe) -> MixerObservation:
        if self._mixer is None:
            self._mixer = asyncio.create_task(probe.inspect_mixer())
        return await asyncio.shield(self._mixer)

    async def audio(self, probe: AudioProbe) -> tuple[AudioEndpoint, ...]:
        if self._audio is None:
            self._audio = asyncio.create_task(probe.inspect_audio())
        return await asyncio.shield(self._audio)


@dataclass(frozen=True, slots=True)
class Check:
    name: str
    subsystem: Subsystem
    timeout_seconds: float
    operation: CheckOperation


async def _run_one(check: Check, run: ValidationRun) -> CheckResult:
    started = time.perf_counter()
    checked_at = datetime.now(UTC)
    try:
        status, summary, evidence = await asyncio.wait_for(
            check.operation(run), check.timeout_seconds
        )
        category = None
    except TimeoutError:
        status, summary, evidence, category = Status.UNKNOWN, "Check timed out", (), "timeout"
    except Exception:
        status = Status.UNKNOWN
        summary = "Check could not determine state"
        evidence = ()
        category = "unexpected"
    return CheckResult(
        check_id=check.name,
        subsystem=check.subsystem,
        status=status,
        summary=summary,
        evidence=evidence,
        remediation=None,
        duration_ms=round((time.perf_counter() - started) * 1000),
        checked_at=checked_at,
        error_category=category,
    )


async def run_validation(checks: tuple[Check, ...], run_id: str) -> ValidationReport:
    started_at = datetime.now(UTC)
    run = ValidationRun()
    results = await asyncio.gather(*(_run_one(check, run) for check in checks))
    return ValidationReport("1.0", run_id, started_at, tuple(results))
