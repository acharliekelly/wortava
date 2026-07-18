from pathlib import Path
from typing import Any

import psutil
import pytest

from wortava.adapters.windows.process import WindowsProcessProbe
from wortava.config.models import ProcessExpectation


class FakeProcess:
    def __init__(self, info: dict[str, Any] | Exception) -> None:
        self._info = info

    @property
    def info(self) -> dict[str, Any]:
        if isinstance(self._info, Exception):
            raise self._info
        return self._info


async def run_inline(operation: Any) -> Any:
    return operation()


@pytest.mark.asyncio
async def test_process_discovery_is_case_insensitive_and_skips_inaccessible_processes(
    tmp_path: Path,
) -> None:
    installed = tmp_path / "OBS64.EXE"
    installed.touch()
    calls: list[list[str]] = []

    def process_iter(attrs: list[str]) -> list[FakeProcess]:
        calls.append(attrs)
        return [
            FakeProcess(psutil.AccessDenied(pid=1)),
            FakeProcess({"pid": 42, "name": "obs64.EXE", "exe": str(installed)}),
        ]

    probe = WindowsProcessProbe(
        (
            ProcessExpectation(name="OBS64.exe", executable=str(installed)),
            ProcessExpectation(name="Companion.exe", executable=str(tmp_path / "missing.exe")),
            ProcessExpectation(name="Optional.exe"),
        ),
        process_iter=process_iter,
        run_sync=run_inline,
    )

    observations = await probe.inspect_processes()

    assert calls == [["pid", "name", "exe"]]
    assert observations[0].name == "OBS64.exe"
    assert observations[0].running is True
    assert observations[0].pid == 42
    assert observations[0].executable == str(installed)
    assert observations[0].installed is True
    assert observations[1].installed is False
    assert observations[1].running is False
    assert observations[2].installed is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "vendor_error",
    [psutil.NoSuchProcess(pid=2), psutil.AccessDenied(pid=2), psutil.ZombieProcess(pid=2)],
)
async def test_process_discovery_skips_expected_psutil_race_errors(
    vendor_error: Exception,
) -> None:
    probe = WindowsProcessProbe(
        (ProcessExpectation(name="Expected.exe"),),
        process_iter=lambda _attrs: [FakeProcess(vendor_error)],
        run_sync=run_inline,
    )

    assert (await probe.inspect_processes())[0].running is False
