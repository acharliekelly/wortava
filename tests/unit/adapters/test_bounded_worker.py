import asyncio
import time

import pytest

from wortava.adapters.windows.worker import run_in_spawned_process


@pytest.mark.asyncio
async def test_spawned_worker_timeout_terminates_without_stalling_shutdown() -> None:
    started = time.perf_counter()
    with pytest.raises(TimeoutError):
        await run_in_spawned_process(time.sleep, (5.0,), timeout_seconds=0.05)
    await asyncio.sleep(0)
    assert time.perf_counter() - started < 1.0
