from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter

import torch
from diffusers import ErnieImagePipeline

from src.models.helpers import extract_generated_images, save_generated_images
from src.schemas import GenerationRequest, GenerationResult

PIPE = None
OFFLOAD_DEVICE = None


def resolve_device(requested_device: str | None) -> str:
    device = requested_device or ("cuda" if torch.cuda.is_available() else "cpu")
    if not device.startswith("cuda"):
        return device

    device_count = torch.cuda.device_count()
    if device_count == 0:
        raise ValueError("CUDA was requested, but no CUDA devices are available")

    if device == "cuda":
        return device

    try:
        device_index = int(device.removeprefix("cuda:"))
    except ValueError as exc:
        raise ValueError(
            f"Invalid CUDA device '{device}'. Use 'cuda' or 'cuda:<index>'."
        ) from exc

    if device_index < 0 or device_index >= device_count:
        raise ValueError(
            f"CUDA device '{device}' is out of range. "
            f"Available CUDA devices: cuda:0 through cuda:{device_count - 1}."
        )

    return device


def get_pipe() -> ErnieImagePipeline:
    global PIPE
    if PIPE is None:
        PIPE = ErnieImagePipeline.from_pretrained(
            "Baidu/ERNIE-Image",
            torch_dtype=torch.bfloat16,
        )
    return PIPE


def generate(
    request: GenerationRequest, output_dir: Path, job_id: str
) -> GenerationResult:
    global OFFLOAD_DEVICE

    pipe = get_pipe()
    device = resolve_device(request.device)
    started_at = datetime.now(UTC)
    started = perf_counter()

    if device.startswith("cuda"):
        if OFFLOAD_DEVICE != device:
            pipe.enable_sequential_cpu_offload(device=device)
            OFFLOAD_DEVICE = device
    else:
        pipe.to(device)

    guidance_scale = request.guidance_scale if request.guidance_scale is not None else 4.0

    produced_images = extract_generated_images(
        pipe(
            prompt=request.prompt,
            negative_prompt=request.neg_prompt,
            height=request.height,
            width=request.width,
            num_inference_steps=request.inf_steps,
            guidance_scale=guidance_scale,
            num_images_per_prompt=request.num_images_per_prompt,
            generator=torch.Generator(device=device).manual_seed(request.seed),
            use_pe=True,
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
        guidance_scale=guidance_scale,
        inf_steps=request.inf_steps,
        seed=request.seed,
        device=device,
        started_at=started_at,
        completed_at=completed_at,
        duration_seconds=perf_counter() - started,
    )
