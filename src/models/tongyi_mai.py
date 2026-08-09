from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter

import torch
from diffusers.pipelines.z_image.pipeline_z_image import ZImagePipeline

from src.models.helpers import extract_generated_images, save_generated_images
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
    if request.num_images_per_prompt != 1:
        raise ValueError("Model 'tongyi-mai' only supports num_images_per_prompt=1")

    pipe = get_pipe()
    device = request.device or "cuda"
    started_at = datetime.now(UTC)
    started = perf_counter()

    if device == "cuda":
        pipe.to("cuda")
        pipe.enable_model_cpu_offload()
    else:
        pipe.to(device)

    produced_images = extract_generated_images(
        pipe(
            prompt=request.prompt,
            negative_prompt=request.neg_prompt,
            height=request.height,
            width=request.width,
            num_inference_steps=request.inf_steps,
            guidance_scale=request.guidance_scale
            if request.guidance_scale is not None
            else 0.0,
            generator=torch.Generator(device).manual_seed(request.seed),
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
        else 0.0,
        inf_steps=request.inf_steps,
        seed=request.seed,
        device=device,
        started_at=started_at,
        completed_at=completed_at,
        duration_seconds=perf_counter() - started,
    )
