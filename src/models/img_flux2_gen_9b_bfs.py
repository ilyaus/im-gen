from __future__ import annotations

import os
from pathlib import Path

import torch
from diffusers.pipelines.flux2.pipeline_flux2_klein import Flux2KleinPipeline

from src.config import get_config
from src.models.base import run_generation
from src.schemas import GenerationRequest, GenerationResult

PIPE = None
DTYPE = torch.bfloat16
BFS_ADAPTER_NAME = "bfs"
BFS_LORA_ENV = "IM_GEN_BFS_LORA"
BFS_LORA_WEIGHT_ENV = "IM_GEN_BFS_LORA_WEIGHT_NAME"


def get_pipe() -> Flux2KleinPipeline:
    global PIPE
    if PIPE is None:
        PIPE = Flux2KleinPipeline.from_pretrained(
            "black-forest-labs/FLUX.2-klein-9B",
            torch_dtype=DTYPE,
        )
    return PIPE


def _get_bfs_lora_source() -> str:
    source = get_config().bfs_lora.source
    if source:
        return source

    raise RuntimeError(
        "BFS LoRA is not configured. Set bfs_lora.source in config.yaml (or the "
        f"{BFS_LORA_ENV} environment variable) to a local LoRA file/directory or "
        "Hugging Face repository id."
    )


def get_pipe_with_bfs(weight_name: str | None = None) -> Flux2KleinPipeline:
    bfs_config = get_config().bfs_lora
    lora_source = None
    if PIPE is None or not getattr(PIPE, "_bfs_loaded", False):
        lora_source = _get_bfs_lora_source()

    pipe = get_pipe()
    if not getattr(pipe, "_bfs_loaded", False):
        load_kwargs = {}
        resolved_weight_name = weight_name or bfs_config.weight_name
        if resolved_weight_name:
            load_kwargs["weight_name"] = resolved_weight_name
        elif os.environ.get("HF_HUB_OFFLINE", "0") not in ("0", "") or os.environ.get(
            "TRANSFORMERS_OFFLINE", "0"
        ) not in ("0", ""):
            raise RuntimeError(
                "Offline mode is enabled but no LoRA weight name was specified. "
                "Set bfs_lora.weight_name in config.yaml, the "
                f"{BFS_LORA_WEIGHT_ENV} environment variable, or pass "
                "lora_weight_name in the request payload."
            )

        pipe.load_lora_weights(
            lora_source,
            adapter_name=BFS_ADAPTER_NAME,
            **load_kwargs,
        )
        pipe._bfs_loaded = True
    pipe.set_adapters(BFS_ADAPTER_NAME, adapter_weights=bfs_config.scale)
    return pipe


def generate(
    request: GenerationRequest, output_dir: Path, job_id: str
) -> GenerationResult:
    return run_generation(
        request=request,
        output_dir=output_dir,
        job_id=job_id,
        get_pipe=lambda: get_pipe_with_bfs(weight_name=request.lora_weight_name),
        default_guidance_scale=1.0,
        offload="sequential",
        accepts_negative_prompt=False,
        accepts_image_input=True,
    )
