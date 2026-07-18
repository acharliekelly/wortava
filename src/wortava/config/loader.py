import os
import tomllib
from importlib.resources.abc import Traversable
from pathlib import Path
from typing import Any

from wortava.config.models import Settings


def _read(path: Traversable | None) -> dict[str, Any]:
    if path is None:
        return {}
    with path.open("rb") as stream:
        return tomllib.load(stream)


def _merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_settings(defaults_path: Traversable, profile_path: Path | None) -> Settings:
    values = _merge(_read(defaults_path), _read(profile_path))
    password = os.getenv("WORTAVA_OBS_PASSWORD")
    if password:
        values.setdefault("obs", {})["password"] = password
    return Settings.model_validate(values)
