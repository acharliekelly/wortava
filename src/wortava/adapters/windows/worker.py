import asyncio
import multiprocessing
import queue
from collections.abc import Callable
from multiprocessing.queues import Queue
from typing import Any


def _worker_entry(
    target: Callable[..., Any], arguments: tuple[Any, ...], output: Queue[Any]
) -> None:
    try:
        output.put((True, target(*arguments)))
    except BaseException as error:
        output.put((False, type(error).__name__))


async def run_in_spawned_process(
    target: Callable[..., Any],
    arguments: tuple[Any, ...],
    *,
    timeout_seconds: float,
) -> Any:
    """Run picklable vendor work with a process lifecycle that can be terminated."""
    context = multiprocessing.get_context("spawn")
    output = context.Queue(maxsize=1)
    process = context.Process(target=_worker_entry, args=(target, arguments, output))
    process.start()
    deadline = asyncio.get_running_loop().time() + timeout_seconds
    try:
        while process.is_alive() and asyncio.get_running_loop().time() < deadline:
            await asyncio.sleep(0.01)
        if process.is_alive():
            raise TimeoutError("Vendor inspection exceeded its bounded worker timeout")
        process.join(timeout=0.1)
        try:
            succeeded, value = output.get_nowait()
        except queue.Empty as error:
            raise RuntimeError("Vendor inspection worker exited without a result") from error
        if not succeeded:
            raise RuntimeError(f"Vendor inspection failed ({value})")
        return value
    finally:
        if process.is_alive():
            process.terminate()
            process.join(timeout=0.5)
            if process.is_alive():
                process.kill()
                process.join(timeout=0.5)
        output.close()
        output.join_thread()
