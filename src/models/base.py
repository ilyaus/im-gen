from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import Any

import torch

from src.models.helpers import (
    extract_generated_images,
    load_input_images,
    save_generated_images,
)
from src.schemas import GenerationRequest, GenerationResult

OFFLOAD_STATE_ATTR = "_im_gen_offload_state"


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


def _apply_offload(pipe: Any, device: str, offload: str) -> None:
    state = (offload, device)
    if getattr(pipe, OFFLOAD_STATE_ATTR, None) == state:
        return

    if not device.startswith("cuda") or offload == "none":
        pipe.to(device)
    elif offload == "sequential":
        pipe.enable_sequential_cpu_offload(device=device)
    elif offload == "model":
        pipe.to(device)
        pipe.enable_model_cpu_offload(device=device)
    else:
        raise ValueError(f"Unknown offload strategy '{offload}'")

    setattr(pipe, OFFLOAD_STATE_ATTR, state)


def run_generation(
    *,
    request: GenerationRequest,
    output_dir: Path,
    job_id: str,
    get_pipe: Callable[[], Any],
    default_guidance_scale: float,
    offload: str = "sequential",
    accepts_negative_prompt: bool = True,
    accepts_image_input: bool = False,
    accepts_num_images: bool = True,
    requires_image_input: bool = False,
    single_image_only: bool = False,
    guidance_param: str = "guidance_scale",
    extra_call_kwargs: dict[str, Any] | None = None,
) -> GenerationResult:
    num_images = request.num_images_per_prompt or 1
    if single_image_only and num_images != 1:
        raise ValueError(
            f"Model '{request.model}' only supports num_images_per_prompt=1"
        )

    input_images = load_input_images(request.images) if accepts_image_input else None
    if requires_image_input and not input_images:
        raise ValueError(
            f"Model '{request.model}' requires at least one input image; "
            "set the 'images' field to local image paths"
        )

    pipe = get_pipe()
    device = resolve_device(request.device)
    started_at = datetime.now(UTC)
    started = perf_counter()

    _apply_offload(pipe, device, offload)

    guidance_scale = (
        request.guidance_scale
        if request.guidance_scale is not None
        else default_guidance_scale
    )
    height = request.height or 1024
    width = request.width or 1024
    inf_steps = request.inf_steps or 4

    call_kwargs: dict[str, Any] = {
        "prompt": request.prompt,
        "height": height,
        "width": width,
        "num_inference_steps": inf_steps,
        "generator": torch.Generator(device=device).manual_seed(request.seed),
        guidance_param: guidance_scale,
    }
    if accepts_negative_prompt:
        call_kwargs["negative_prompt"] = request.neg_prompt
    if accepts_image_input:
        call_kwargs["image"] = input_images
    if accepts_num_images:
        call_kwargs["num_images_per_prompt"] = num_images
    if extra_call_kwargs:
        call_kwargs.update(extra_call_kwargs)

    produced_images = extract_generated_images(pipe(**call_kwargs))

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
        height=height,
        width=width,
        num_images_per_prompt=num_images,
        neg_prompt=request.neg_prompt,
        guidance_scale=guidance_scale,
        inf_steps=inf_steps,
        seed=request.seed,
        device=device,
        started_at=started_at,
        completed_at=completed_at,
        duration_seconds=perf_counter() - started,
    )
