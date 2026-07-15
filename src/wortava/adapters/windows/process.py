import asyncio
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any, Protocol

import psutil  # type: ignore[import-untyped]

from wortava.config.models import ProcessExpectation
from wortava.ports.probes import ProcessObservation


class VendorProcess(Protocol):
    @property
    def info(self) -> dict[str, Any]: ...


type ProcessIterator = Callable[[list[str]], Iterable[VendorProcess]]

_PROCESS_ERRORS = (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess)


class WindowsProcessProbe:
    def __init__(
        self,
        expectations: tuple[ProcessExpectation, ...],
        process_iter: ProcessIterator = psutil.process_iter,
    ) -> None:
        self._expectations = expectations
        self._process_iter = process_iter

    async def inspect_processes(self) -> tuple[ProcessObservation, ...]:
        return await asyncio.to_thread(self._inspect_processes_sync)

    def _inspect_processes_sync(self) -> tuple[ProcessObservation, ...]:
        discovered: dict[str, dict[str, Any]] = {}
        try:
            processes = self._process_iter(["pid", "name", "exe"])
            for process in processes:
                try:
                    info = process.info
                    name = info.get("name")
                    if isinstance(name, str):
                        discovered.setdefault(name.casefold(), info)
                except _PROCESS_ERRORS:
                    continue
        except _PROCESS_ERRORS:
            pass

        return tuple(
            self._observation(expectation, discovered) for expectation in self._expectations
        )

    @staticmethod
    def _observation(
        expectation: ProcessExpectation, discovered: dict[str, dict[str, Any]]
    ) -> ProcessObservation:
        info = discovered.get(expectation.name.casefold())
        configured_executable = expectation.executable
        installed = (
            Path(configured_executable).is_file()
            if configured_executable is not None
            else None
        )
        return ProcessObservation(
            name=expectation.name,
            installed=installed,
            running=info is not None,
            pid=info.get("pid") if info is not None else None,
            executable=info.get("exe") if info is not None else configured_executable,
            version=None,
        )
