import asyncio

import pytest

from wortava.application.runner import Check, run_validation
from wortava.domain.models import Status, Subsystem


@pytest.mark.asyncio
async def test_timeout_becomes_unknown_and_other_checks_complete() -> None:
    async def slow() -> object:
        await asyncio.sleep(0.1)
        return object()

    async def fast() -> object:
        return object()

    checks = (
        Check("slow", Subsystem.OBS, 0.01, slow, lambda _: (Status.PASS, "ok", ())),
        Check("fast", Subsystem.SYSTEM, 1, fast, lambda _: (Status.PASS, "ok", ())),
    )
    report = await run_validation(checks, "run-1")

    assert [item.status for item in report.results] == [Status.UNKNOWN, Status.PASS]
    assert report.results[0].error_category == "timeout"


@pytest.mark.asyncio
async def test_exception_is_sanitized_and_other_checks_complete() -> None:
    async def broken() -> object:
        raise RuntimeError("password=secret")

    async def fast() -> object:
        return object()

    checks = (
        Check("broken", Subsystem.OBS, 1, broken, lambda _: (Status.PASS, "ok", ())),
        Check("fast", Subsystem.SYSTEM, 1, fast, lambda _: (Status.PASS, "ok", ())),
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

    async def wait_for_peer() -> object:
        nonlocal arrivals
        arrivals += 1
        if arrivals == 2:
            gate.set()
        await asyncio.wait_for(gate.wait(), timeout=0.1)
        return object()

    checks = tuple(
        Check(str(index), Subsystem.SYSTEM, 1, wait_for_peer, lambda _: (Status.PASS, "ok", ()))
        for index in range(2)
    )

    report = await run_validation(checks, "run-3")

    assert [item.status for item in report.results] == [Status.PASS, Status.PASS]
