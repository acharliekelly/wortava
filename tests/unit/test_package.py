from pathlib import Path

import pytest

import wortava
from wortava.cli import app


def test_package_exposes_version() -> None:
    assert wortava.__version__ == "0.1.0"


def test_default_settings_path_uses_pyinstaller_bundle(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(app.sys, "frozen", True, raising=False)
    monkeypatch.setattr(app.sys, "_MEIPASS", str(tmp_path), raising=False)

    assert app._default_settings_path() == tmp_path / "config" / "defaults.toml"
