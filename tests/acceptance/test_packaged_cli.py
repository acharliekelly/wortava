import json
import subprocess
from pathlib import Path

import pytest


@pytest.mark.windows_package
def test_packaged_cli_runs_without_python() -> None:
    executable = Path("dist/wortava/wortava.exe")
    assert executable.is_file(), (
        f"packaged executable is absent: {executable}; "
        "build it with 'uv run pyinstaller wortava.spec --clean'"
    )
    completed = subprocess.run(
        [executable, "simulate", "all-pass", "--format", "json"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout)["schema_version"] == "1.0"
