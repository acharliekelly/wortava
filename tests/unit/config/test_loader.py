from pathlib import Path

import pytest

from wortava.config.loader import load_settings


def test_profile_overrides_defaults_and_environment_supplies_secret(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    defaults = tmp_path / "defaults.toml"
    defaults.write_text('[obs]\nhost="127.0.0.1"\nport=4455\ntimeout_seconds=2.0\n')
    profile = tmp_path / "site.toml"
    profile.write_text('[obs]\nhost="10.0.0.5"\n')
    monkeypatch.setenv("WORTAVA_OBS_PASSWORD", "super-secret")

    settings = load_settings(defaults, profile)

    assert settings.obs.host == "10.0.0.5"
    assert settings.obs.port == 4455
    assert str(settings.obs.password) == "**********"
    assert "super-secret" not in repr(settings)


def test_mixer_may_be_unconfigured(tmp_path: Path) -> None:
    defaults = tmp_path / "defaults.toml"
    defaults.write_text('[obs]\nhost="127.0.0.1"\nport=4455\ntimeout_seconds=2.0\n')
    settings = load_settings(defaults, None)
    assert settings.mixer.host is None
