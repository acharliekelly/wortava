import hashlib
import subprocess
import sys
import zipfile
from pathlib import Path


def test_windows_archive_is_deterministic_and_contains_entire_onedir(tmp_path: Path) -> None:
    onedir = tmp_path / "wortava"
    (onedir / "_internal").mkdir(parents=True)
    (onedir / "wortava.exe").write_bytes(b"launcher")
    (onedir / "_internal" / "payload.dll").write_bytes(b"payload")
    (onedir / "_internal" / "defaults.toml").write_bytes(b"defaults")
    output = tmp_path / "wortava-windows-x64.zip"
    command = [sys.executable, "scripts/package_windows.py", str(onedir), str(output)]
    subprocess.run(command, check=True)
    first = output.read_bytes()
    subprocess.run(command, check=True)
    assert output.read_bytes() == first
    with zipfile.ZipFile(output) as archive:
        assert set(archive.namelist()) == {
            "wortava/wortava.exe",
            "wortava/_internal/payload.dll",
            "wortava/_internal/defaults.toml",
        }
    checksum_path = tmp_path / "wortava-windows-x64.zip.sha256"
    digest, filename = checksum_path.read_text(encoding="ascii").split()
    assert digest == hashlib.sha256(output.read_bytes()).hexdigest()
    assert filename == output.name
