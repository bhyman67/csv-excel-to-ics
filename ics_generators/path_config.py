from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = REPO_ROOT / "paths.local.json"


def _as_path(value: str, base_dir: Path) -> Path:
    path = Path(value).expanduser()
    if path.is_absolute():
        return path
    return (base_dir / path).resolve()


def _load_local_config() -> dict[str, Any]:
    config_override = os.getenv("ICS_PATHS_CONFIG")
    config_path = _as_path(config_override, REPO_ROOT) if config_override else DEFAULT_CONFIG_PATH
    if not config_path.exists():
        return {}

    try:
        with open(config_path, "r", encoding="utf-8") as handle:
            loaded = json.load(handle)
    except (OSError, ValueError):
        return {}

    if isinstance(loaded, dict):
        return loaded
    return {}


def get_input_output_roots() -> tuple[Path, Path]:
    config = _load_local_config()

    input_root_value = os.getenv("ICS_INPUT_ROOT") or config.get("input_root") or "input"
    output_root_value = os.getenv("ICS_OUTPUT_ROOT") or config.get("output_root") or "output"

    input_root = _as_path(str(input_root_value), REPO_ROOT)
    output_root = _as_path(str(output_root_value), REPO_ROOT)
    return input_root, output_root


def resolve_input_path(path_text: str | None, default_relative: str | None = None) -> Path:
    input_root, _ = get_input_output_roots()

    if path_text:
        path = Path(path_text).expanduser()
        return path if path.is_absolute() else (input_root / path)

    if default_relative is None:
        raise ValueError("No input path was provided and no default is configured.")

    return input_root / default_relative


def resolve_output_path(path_text: str | None, default_relative: str | None = None) -> Path:
    _, output_root = get_input_output_roots()

    if path_text:
        path = Path(path_text).expanduser()
        return path if path.is_absolute() else (output_root / path)

    if default_relative is None:
        raise ValueError("No output path was provided and no default is configured.")

    return output_root / default_relative