import subprocess
import sys
from pathlib import Path


def test_windows_archive_is_deterministic_and_contains_entire_onedir(tmp_path: Path) -> None:
    onedir = tmp_path / "wortava"
    (onedir / "_internal").mkdir(parents=True)
    (onedir / "wortava.exe").write_bytes(b"launcher")
    (onedir / "_internal" / "payload.dll").write_bytes(b"payload")
    output = tmp_path / "wortava-windows-x64.zip"
    command = [sys.executable, "scripts/package_windows.py", str(onedir), str(output)]
    subprocess.run(command, check=True)
    first = output.read_bytes()
    subprocess.run(command, check=True)
    assert output.read_bytes() == first
    assert (tmp_path / "wortava-windows-x64.zip.sha256").is_file()
