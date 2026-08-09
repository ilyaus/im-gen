from __future__ import annotations

from pathlib import Path

from src.config import get_config


def get_output_root() -> Path:
    return Path(get_config().output_root)


def get_job_output_dir(job_id: str) -> Path:
    output_dir = get_output_root() / job_id
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir
