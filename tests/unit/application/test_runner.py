import asyncio

import pytest

from wortava.application.runner import Check, Evaluation, ValidationRun, run_validation
from wortava.domain.models import Status, Subsystem
from wortava.ports.probes import ObsObservation


@pytest.mark.asyncio
async def test_timeout_becomes_unknown_and_other_checks_complete() -> None:
    async def slow(_: object) -> Evaluation:
        await asyncio.sleep(0.1)
        return Status.PASS, "ok", ()

    async def fast(_: object) -> Evaluation:
        return Status.PASS, "ok", ()

    checks = (
        Check("slow", Subsystem.OBS, 0.01, slow),
        Check("fast", Subsystem.SYSTEM, 1, fast),
    )
    report = await run_validation(checks, "run-1")

    assert [item.status for item in report.results] == [Status.UNKNOWN, Status.PASS]
    assert report.results[0].error_category == "timeout"


@pytest.mark.asyncio
async def test_exception_is_sanitized_and_other_checks_complete() -> None:
    async def broken(_: object) -> Evaluation:
        raise RuntimeError("password=secret")

    async def fast(_: object) -> Evaluation:
        return Status.PASS, "ok", ()

    checks = (
        Check("broken", Subsystem.OBS, 1, broken),
        Check("fast", Subsystem.SYSTEM, 1, fast),
    )
    report = await run_validation(checks, "run-2")

    assert [item.status for item in report.results] == [Status.UNKNOWN, Status.PASS]
    assert report.results[0].summary == "Check could not determine state"
    assert report.results[0].error_category == "unexpected"
    assert "secret" not in repr(report.results[0])


@pytest.mark.asyncio
async def test_checks_run_concurrently() -> None:
    gate = asyncio.Event()
    arrivals = 0

    async def wait_for_peer(_: object) -> Evaluation:
        nonlocal arrivals
        arrivals += 1
        if arrivals == 2:
            gate.set()
        await asyncio.wait_for(gate.wait(), timeout=0.1)
        return Status.PASS, "ok", ()

    checks = tuple(Check(str(index), Subsystem.SYSTEM, 1, wait_for_peer) for index in range(2))

    report = await run_validation(checks, "run-3")

    assert [item.status for item in report.results] == [Status.PASS, Status.PASS]


@pytest.mark.asyncio
async def test_consumer_timeout_does_not_cancel_shared_acquisition() -> None:
    class SlowObsProbe:
        calls = 0

        async def inspect_obs(self) -> ObsObservation:
            self.calls += 1
            await asyncio.sleep(0.05)
            return ObsObservation(True, None, None)

    probe = SlowObsProbe()

    async def consume_obs(run: ValidationRun) -> Evaluation:
        observation = await run.obs(probe)
        return Status.PASS, str(observation.connected), ()

    checks = (
        Check("impatient", Subsystem.OBS, 0.01, consume_obs),
        Check("patient", Subsystem.OBS, 0.2, consume_obs),
    )

    report = await run_validation(checks, "shared-timeout")

    assert probe.calls == 1
    assert [item.status for item in report.results] == [Status.UNKNOWN, Status.PASS]


@pytest.mark.asyncio
async def test_all_consumer_timeouts_cancel_and_join_shared_acquisition() -> None:
    class HangingObsProbe:
        task: asyncio.Task[object] | None = None
        cancelled = asyncio.Event()

        async def inspect_obs(self) -> ObsObservation:
            self.task = asyncio.current_task()
            try:
                await asyncio.sleep(10)
            except asyncio.CancelledError:
                self.cancelled.set()
                raise
            return ObsObservation(True, None, None)

    probe = HangingObsProbe()

    async def consume_obs(run: ValidationRun) -> Evaluation:
        await run.obs(probe)
        return Status.PASS, "ok", ()

    checks = (
        Check("first", Subsystem.OBS, 0.01, consume_obs),
        Check("second", Subsystem.OBS, 0.02, consume_obs),
    )

    report = await run_validation(checks, "all-timeout")

    assert [item.status for item in report.results] == [Status.UNKNOWN, Status.UNKNOWN]
    assert probe.cancelled.is_set()
    assert probe.task is not None
    assert probe.task.done()
    assert probe.task.cancelled()
