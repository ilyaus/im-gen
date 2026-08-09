from __future__ import annotations

import os
from pathlib import Path


OUTPUT_ROOT = Path(os.getenv("OUTPUT_ROOT", ""))


def get_job_output_dir(job_id: str) -> Path:
    output_dir = OUTPUT_ROOT / job_id
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir
