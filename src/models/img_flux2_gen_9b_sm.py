from __future__ import annotations

from pathlib import Path

import torch
from diffusers.models.autoencoders.autoencoder_kl_flux2 import AutoencoderKLFlux2
from diffusers.pipelines.flux2.pipeline_flux2_klein import Flux2KleinPipeline

from src.models.base import run_generation
from src.schemas import GenerationRequest, GenerationResult

PIPE = None
DTYPE = torch.bfloat16


def get_pipe() -> Flux2KleinPipeline:
    global PIPE
    if PIPE is None:
        vae = AutoencoderKLFlux2.from_pretrained(
            "black-forest-labs/FLUX.2-small-decoder",
            torch_dtype=DTYPE,
        )
        PIPE = Flux2KleinPipeline.from_pretrained(
            "black-forest-labs/FLUX.2-klein-9B",
            vae=vae,
            torch_dtype=DTYPE,
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
        default_guidance_scale=1.0,
        offload="sequential",
        accepts_negative_prompt=False,
        accepts_image_input=True,
    )
