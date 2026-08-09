from __future__ import annotations

from pathlib import Path

import torch
from diffusers import QwenImageEditPlusPipeline

from src.models.base import run_generation
from src.schemas import GenerationRequest, GenerationResult

PIPE = None


def get_pipe() -> QwenImageEditPlusPipeline:
    global PIPE
    if PIPE is None:
        PIPE = QwenImageEditPlusPipeline.from_pretrained(
            "Qwen/Qwen-Image-Edit-2511",
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
        offload="sequential",
        guidance_param="true_cfg_scale",
        accepts_image_input=True,
        requires_image_input=True,
    )
