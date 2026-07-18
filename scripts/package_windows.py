"""Create a reproducible archive and checksum for the complete PyInstaller onedir."""

import hashlib
import sys
import zipfile
from pathlib import Path

_ZIP_TIMESTAMP = (2026, 1, 1, 0, 0, 0)


def package(source: Path, destination: Path) -> None:
    if not source.is_dir():
        raise SystemExit(f"onedir package does not exist: {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(item for item in source.rglob("*") if item.is_file()):
            relative = Path(source.name) / path.relative_to(source)
            info = zipfile.ZipInfo(relative.as_posix(), _ZIP_TIMESTAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, path.read_bytes())
    digest = hashlib.sha256(destination.read_bytes()).hexdigest()
    destination.with_suffix(destination.suffix + ".sha256").write_text(
        f"{digest}  {destination.name}\n", encoding="ascii"
    )


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: package_windows.py ONEDIR OUTPUT_ZIP")
    package(Path(sys.argv[1]), Path(sys.argv[2]))
