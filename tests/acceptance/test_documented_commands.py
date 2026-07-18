import re
import subprocess
from pathlib import Path

import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
README = REPOSITORY_ROOT / "README.md"


def documented_smoke_commands() -> list[str]:
    text = README.read_text(encoding="utf-8")
    pattern = re.compile(
        r"<!-- smoke-test -->\s*```console\s*\n\$ ([^\n]+)\n```",
        re.MULTILINE,
    )
    return pattern.findall(text)


SMOKE_COMMANDS = documented_smoke_commands()


def test_readme_marks_required_simulation_as_a_smoke_test() -> None:
    assert "uv run wortava simulate all-pass --format json" in SMOKE_COMMANDS


@pytest.mark.parametrize("command", SMOKE_COMMANDS)
def test_documented_smoke_command_exits_zero(command: str) -> None:
    completed = subprocess.run(
        command.split(),
        cwd=REPOSITORY_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, (
        f"command failed: {command}\nstdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
    )
