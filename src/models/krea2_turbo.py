from __future__ import annotations

from pathlib import Path

import torch

from src.models.base import run_generation
from src.schemas import GenerationRequest, GenerationResult

PIPE = None


def get_pipe():
    global PIPE
    if PIPE is None:
        try:
            from diffusers import Krea2Pipeline
        except ImportError as exc:
            raise RuntimeError(
                "Krea2Pipeline is not available in the installed diffusers "
                "version. Update diffusers to the latest main branch: "
                "uv lock --upgrade-package diffusers && uv sync"
            ) from exc

        PIPE = Krea2Pipeline.from_pretrained(
            "krea/Krea-2-Turbo",
            torch_dtype=torch.bfloat16,
        )
    return PIPE


def generate(
    request: GenerationRequest, output_dir: Path, job_id: str
) -> GenerationResult:
    return run_generation(
        request=request,
        output_dir=output_dir,
        job_id=job_id,
        get_pipe=get_pipe,
        default_guidance_scale=0.0,
        offload="sequential",
        accepts_negative_prompt=False,
    )
