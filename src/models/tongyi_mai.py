from __future__ import annotations

from pathlib import Path

import torch
from diffusers.pipelines.z_image.pipeline_z_image import ZImagePipeline

from src.models.base import run_generation
from src.schemas import GenerationRequest, GenerationResult

PIPE = None


def get_pipe() -> ZImagePipeline:
    global PIPE
    if PIPE is None:
        PIPE = ZImagePipeline.from_pretrained(
            "Tongyi-MAI/Z-Image-Turbo",
            torch_dtype=torch.bfloat16,
            low_cpu_mem_usage=False,
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
        offload="model",
        accepts_num_images=False,
        single_image_only=True,
    )
