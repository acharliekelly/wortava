import asyncio
import logging
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
    UnsupportedPlatform,
)

type Evaluation = tuple[Status, str, tuple[Evidence, ...]]
type CheckOperation = Callable[["ValidationRun"], Awaitable[Evaluation]]


def _null_logger() -> logging.Logger:
    logger = logging.getLogger("wortava.null")
    logger.setLevel(logging.CRITICAL + 1)
    logger.propagate = False
    for handler in tuple(logger.handlers):
        handler.close()
        logger.removeHandler(handler)
    logger.addHandler(logging.NullHandler())
    return logger


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

    async def close(self) -> None:
        tasks = tuple(
            task
            for task in (self._processes, self._obs, self._mixer, self._audio)
            if task is not None
        )
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


@dataclass(frozen=True, slots=True)
class Check:
    name: str
    subsystem: Subsystem
    timeout_seconds: float
    operation: CheckOperation


async def _run_one(check: Check, run: ValidationRun, logger: logging.Logger) -> CheckResult:
    started = time.perf_counter()
    checked_at = datetime.now(UTC)
    logger.info(
        "Check started",
        extra={"event": "check_started", "check_id": check.name},
    )
    try:
        status, summary, evidence = await asyncio.wait_for(
            check.operation(run), check.timeout_seconds
        )
        category = None
    except TimeoutError:
        status, summary, evidence, category = Status.UNKNOWN, "Check timed out", (), "timeout"
    except UnsupportedPlatform:
        status = Status.UNKNOWN
        summary = "Check is unsupported on this platform"
        evidence = ()
        category = "unsupported_platform"
    except Exception as error:
        status = Status.UNKNOWN
        summary = "Check could not determine state"
        evidence = ()
        category = "unexpected"
        logger.exception(
            "Unexpected %s: %s",
            type(error).__name__,
            error,
            extra={
                "event": "check_exception",
                "check_id": check.name,
                "exception_class": type(error).__name__,
                "error_category": category,
            },
        )
    result = CheckResult(
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
    logger.info(
        "Check finished",
        extra={
            "event": "check_finished",
            "check_id": check.name,
            "duration_ms": result.duration_ms,
            "error_category": result.error_category,
        },
    )
    return result


async def run_validation(
    checks: tuple[Check, ...], run_id: str, logger: logging.Logger | None = None
) -> ValidationReport:
    started_at = datetime.now(UTC)
    run = ValidationRun()
    run_logger = logger or _null_logger()
    try:
        results = await asyncio.gather(*(_run_one(check, run, run_logger) for check in checks))
    finally:
        await run.close()
    return ValidationReport("1.0", run_id, started_at, tuple(results))
