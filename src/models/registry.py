from __future__ import annotations

import gc
import logging
import sys
from collections.abc import Callable
from importlib import import_module

from src.schemas import ModelCapabilities, ModelDefaults, ModelInfo

logger = logging.getLogger(__name__)

GeneratorCallable = Callable[..., object]


MODEL_REGISTRY: dict[str, ModelInfo] = {
    "tongyi-mai": ModelInfo(
        name="tongyi-mai",
        module="src.models.tongyi_mai",
        description="Tongyi Z-Image Turbo text-to-image pipeline (6B, distilled)",
        defaults=ModelDefaults(
            guidance_scale=0.0, inf_steps=8, height=1024, width=1024
        ),
        capabilities=ModelCapabilities(supports_multi_image=False, max_images=1),
    ),
    "baidu-ernie-image": ModelInfo(
        name="baidu-ernie-image",
        module="src.models.baidu_ernie_image",
        description="Baidu ERNIE-Image text-to-image pipeline",
        defaults=ModelDefaults(
            guidance_scale=4.0, inf_steps=50, height=1024, width=1024
        ),
    ),
    "flux2-klein-4b-small-decoder": ModelInfo(
        name="flux2-klein-4b-small-decoder",
        module="src.models.img_flux2_gen_4b_sm",
        description="FLUX.2 Klein 4B with small decoder (fast, distilled)",
        defaults=ModelDefaults(
            guidance_scale=1.0, inf_steps=4, height=1024, width=512
        ),
        capabilities=ModelCapabilities(
            supports_negative_prompt=False, supports_image_input=True
        ),
    ),
    "flux2-klein-9b": ModelInfo(
        name="flux2-klein-9b",
        module="src.models.img_flux2_gen_9b",
        description="FLUX.2 Klein 9B (distilled)",
        defaults=ModelDefaults(
            guidance_scale=1.0, inf_steps=4, height=1024, width=512
        ),
        capabilities=ModelCapabilities(
            supports_negative_prompt=False, supports_image_input=True
        ),
    ),
    "flux2-klein-9b-bfs": ModelInfo(
        name="flux2-klein-9b-bfs",
        module="src.models.img_flux2_gen_9b_bfs",
        description="FLUX.2 Klein 9B with BFS LoRA adapter",
        defaults=ModelDefaults(
            guidance_scale=1.0, inf_steps=4, height=1024, width=512
        ),
        capabilities=ModelCapabilities(
            supports_negative_prompt=False, supports_image_input=True
        ),
    ),
    "flux2-klein-9b-small-decoder": ModelInfo(
        name="flux2-klein-9b-small-decoder",
        module="src.models.img_flux2_gen_9b_sm",
        description="FLUX.2 Klein 9B with small decoder",
        defaults=ModelDefaults(
            guidance_scale=1.0, inf_steps=4, height=1024, width=512
        ),
        capabilities=ModelCapabilities(
            supports_negative_prompt=False, supports_image_input=True
        ),
    ),
    "qwen-image": ModelInfo(
        name="qwen-image",
        module="src.models.qwen_image",
        description="Qwen-Image 20B; best-in-class text rendering (CPU offload)",
        defaults=ModelDefaults(
            guidance_scale=4.0, inf_steps=50, height=1024, width=1024
        ),
    ),
    "qwen-image-edit": ModelInfo(
        name="qwen-image-edit",
        module="src.models.qwen_image_edit",
        description="Qwen-Image-Edit 2509; image editing with input images",
        defaults=ModelDefaults(
            guidance_scale=4.0, inf_steps=40, height=1024, width=1024
        ),
        capabilities=ModelCapabilities(
            supports_image_input=True, requires_image_input=True
        ),
    ),
    "sd35-medium": ModelInfo(
        name="sd35-medium",
        module="src.models.sd35_medium",
        description="Stable Diffusion 3.5 Medium (2.5B; gated HF repo)",
        defaults=ModelDefaults(
            guidance_scale=4.5, inf_steps=40, height=1024, width=1024
        ),
    ),
    "sd35-large": ModelInfo(
        name="sd35-large",
        module="src.models.sd35_large",
        description="Stable Diffusion 3.5 Large (8B; gated HF repo, CPU offload)",
        defaults=ModelDefaults(
            guidance_scale=3.5, inf_steps=28, height=1024, width=1024
        ),
    ),
    "sana-sprint": ModelInfo(
        name="sana-sprint",
        module="src.models.sana_sprint",
        description="NVIDIA Sana Sprint 1.6B; 1-4 step generation, very fast",
        defaults=ModelDefaults(
            guidance_scale=4.5, inf_steps=2, height=1024, width=1024
        ),
        capabilities=ModelCapabilities(supports_negative_prompt=False),
    ),
    "hunyuan-image": ModelInfo(
        name="hunyuan-image",
        module="src.models.hunyuan_image",
        description="Tencent HunyuanImage 2.1 (17B; CPU offload)",
        defaults=ModelDefaults(
            guidance_scale=3.5, inf_steps=50, height=1024, width=1024
        ),
    ),
    "lumina-2": ModelInfo(
        name="lumina-2",
        module="src.models.lumina2",
        description="Lumina Image 2.0 (2.6B)",
        defaults=ModelDefaults(
            guidance_scale=4.0, inf_steps=40, height=1024, width=1024
        ),
    ),
    "krea2-turbo": ModelInfo(
        name="krea2-turbo",
        module="src.models.krea2_turbo",
        description="Krea 2 Turbo 12B; 8-step distilled, guidance-free (gated HF repo)",
        defaults=ModelDefaults(
            guidance_scale=0.0, inf_steps=8, height=1024, width=1024
        ),
        capabilities=ModelCapabilities(supports_negative_prompt=False),
    ),
}


def list_models() -> list[ModelInfo]:
    return list(MODEL_REGISTRY.values())


def get_model_info(model_name: str) -> ModelInfo:
    try:
        return MODEL_REGISTRY[model_name]
    except KeyError as exc:
        available_models = ", ".join(sorted(MODEL_REGISTRY))
        raise ValueError(
            f"Unknown model '{model_name}'. Available models: {available_models}"
        ) from exc


def get_generator(model_name: str) -> GeneratorCallable:
    model_info = get_model_info(model_name)
    module = import_module(model_info.module)

    try:
        return module.generate
    except AttributeError as exc:
        raise RuntimeError(
            f"Model module '{model_info.module}' has no generate()"
        ) from exc


def unload_pipelines() -> None:
    """Release every cached model pipeline and free GPU memory."""
    unloaded = []
    for info in MODEL_REGISTRY.values():
        module = sys.modules.get(info.module)
        if module is not None and getattr(module, "PIPE", None) is not None:
            module.PIPE = None
            unloaded.append(info.name)

    if not unloaded:
        return

    gc.collect()
    try:
        import torch

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.ipc_collect()
    except ImportError:
        pass
    logger.info("Unloaded model pipelines: %s", ", ".join(unloaded))
