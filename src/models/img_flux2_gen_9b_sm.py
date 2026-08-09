from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter

import torch
from diffusers.models.autoencoders.autoencoder_kl_flux2 import AutoencoderKLFlux2
from diffusers.pipelines.flux2.pipeline_flux2_klein import Flux2KleinPipeline

from src.models.helpers import (
    extract_generated_images,
    load_input_images,
    save_generated_images,
)
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
    pipe = get_pipe()
    device = request.device or "cuda"
    started_at = datetime.now(UTC)
    started = perf_counter()

    if device == "cuda":
        pipe.enable_sequential_cpu_offload()

    produced_images = extract_generated_images(
        pipe(
            prompt=request.prompt,
            image=load_input_images(request.images),
            height=request.height,
            width=request.width,
            guidance_scale=request.guidance_scale
            if request.guidance_scale is not None
            else 1.0,
            num_inference_steps=request.inf_steps,
            num_images_per_prompt=request.num_images_per_prompt,
            generator=torch.Generator(device=device).manual_seed(request.seed),
        )
    )

    artifacts = save_generated_images(
        images=produced_images,
        output_dir=output_dir,
        output_prefix=request.output_prefix or request.model.replace("-", "_"),
        seed=request.seed,
    )

    for artifact in artifacts:
        artifact.download_url = f"/jobs/{job_id}/artifacts/{artifact.filename}"

    completed_at = datetime.now(UTC)
    return GenerationResult(
        model=request.model,
        prompt=request.prompt,
        output_dir=str(output_dir.resolve()),
        artifacts=artifacts,
        height=request.height,
        width=request.width,
        num_images_per_prompt=request.num_images_per_prompt,
        neg_prompt=request.neg_prompt,
        guidance_scale=request.guidance_scale
        if request.guidance_scale is not None
        else 1.0,
        inf_steps=request.inf_steps,
        seed=request.seed,
        device=device,
        started_at=started_at,
        completed_at=completed_at,
        duration_seconds=perf_counter() - started,
    )
