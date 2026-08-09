from __future__ import annotations

from pathlib import Path

import torch
from diffusers import SanaSprintPipeline

from src.models.base import run_generation
from src.schemas import GenerationRequest, GenerationResult

PIPE = None


def get_pipe() -> SanaSprintPipeline:
    global PIPE
    if PIPE is None:
        PIPE = SanaSprintPipeline.from_pretrained(
            "Efficient-Large-Model/Sana_Sprint_1.6B_1024px_diffusers",
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
        default_guidance_scale=4.5,
        offload="none",
        accepts_negative_prompt=False,
    )
