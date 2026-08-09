from __future__ import annotations

from pathlib import Path

import torch
from diffusers import Lumina2Pipeline

from src.models.base import run_generation
from src.schemas import GenerationRequest, GenerationResult

PIPE = None


def get_pipe() -> Lumina2Pipeline:
    global PIPE
    if PIPE is None:
        PIPE = Lumina2Pipeline.from_pretrained(
            "Alpha-VLLM/Lumina-Image-2.0",
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
        default_guidance_scale=4.0,
        offload="model",
    )
