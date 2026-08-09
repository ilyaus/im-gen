from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter

import torch
from diffusers.pipelines.flux2.pipeline_flux2_klein import Flux2KleinPipeline

from src.models.helpers import (
    extract_generated_images,
    load_input_images,
    save_generated_images,
)
from src.schemas import GenerationRequest, GenerationResult

PIPE = None
DTYPE = torch.bfloat16
BFS_ADAPTER_NAME = "bfs"
BFS_LORA_ENV = "IM_GEN_BFS_LORA"
BFS_LORA_WEIGHT_ENV = "IM_GEN_BFS_LORA_WEIGHT_NAME"
BFS_LORA_SCALE_ENV = "IM_GEN_BFS_LORA_SCALE"


def get_pipe() -> Flux2KleinPipeline:
    global PIPE
    if PIPE is None:
        PIPE = Flux2KleinPipeline.from_pretrained(
            "black-forest-labs/FLUX.2-klein-9B",
            torch_dtype=DTYPE,
        )
    return PIPE


def _get_bfs_lora_source() -> str:
    source = os.environ.get(BFS_LORA_ENV)
    if source:
        return source

    raise RuntimeError(
        f"BFS LoRA is not configured. Set {BFS_LORA_ENV} to a local LoRA "
        "file/directory or Hugging Face repository id."
    )


def _get_bfs_lora_scale() -> float:
    raw_scale = os.environ.get(BFS_LORA_SCALE_ENV)
    if raw_scale is None:
        return 1.0

    try:
        return float(raw_scale)
    except ValueError as exc:
        raise ValueError(f"{BFS_LORA_SCALE_ENV} must be a float") from exc


def get_pipe_with_bfs(weight_name: str | None = None) -> Flux2KleinPipeline:
    lora_scale = _get_bfs_lora_scale()
    lora_source = None
    if PIPE is None or not getattr(PIPE, "_bfs_loaded", False):
        lora_source = _get_bfs_lora_source()

    pipe = get_pipe()
    if not getattr(pipe, "_bfs_loaded", False):
        load_kwargs = {}
        resolved_weight_name = weight_name or os.environ.get(BFS_LORA_WEIGHT_ENV)
        if resolved_weight_name:
            load_kwargs["weight_name"] = resolved_weight_name
        elif os.environ.get("HF_HUB_OFFLINE", "0") not in ("0", "") or os.environ.get(
            "TRANSFORMERS_OFFLINE", "0"
        ) not in ("0", ""):
            raise RuntimeError(
                f"Offline mode is enabled but no LoRA weight name was specified. "
                f"Set {BFS_LORA_WEIGHT_ENV} or pass lora_weight_name in the request payload."
            )

        pipe.load_lora_weights(
            lora_source,
            adapter_name=BFS_ADAPTER_NAME,
            **load_kwargs,
        )
        pipe._bfs_loaded = True
    pipe.set_adapters(BFS_ADAPTER_NAME, adapter_weights=lora_scale)
    return pipe


def generate(
    request: GenerationRequest, output_dir: Path, job_id: str
) -> GenerationResult:
    pipe = get_pipe_with_bfs(weight_name=request.lora_weight_name)
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
