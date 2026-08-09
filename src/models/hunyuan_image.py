from __future__ import annotations

from pathlib import Path

import torch
from diffusers import HunyuanImagePipeline

from src.models.base import run_generation
from src.schemas import GenerationRequest, GenerationResult

PIPE = None


def get_pipe() -> HunyuanImagePipeline:
    global PIPE
    if PIPE is None:
        PIPE = HunyuanImagePipeline.from_pretrained(
            "hunyuanvideo-community/HunyuanImage-2.1",
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
        default_guidance_scale=3.5,
        offload="sequential",
    )
