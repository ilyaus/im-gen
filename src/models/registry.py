from __future__ import annotations

from importlib import import_module
from typing import Callable

from src.schemas import ModelInfo


GeneratorCallable = Callable[..., object]


MODEL_REGISTRY: dict[str, ModelInfo] = {
    "tongyi-mai": ModelInfo(
        name="tongyi-mai",
        module="src.models.tongyi_mai",
        description="Tongyi Z-Image Turbo text-to-image pipeline",
    ),
    "baidu-ernie-image": ModelInfo(
        name="baidu-ernie-image",
        module="src.models.baidu_ernie_image",
        description="Baidu ERNIE-Image text-to-image pipeline",
    ),
    "flux2-klein-4b-small-decoder": ModelInfo(
        name="flux2-klein-4b-small-decoder",
        module="src.models.img_flux2_gen_4b_sm",
        description="FLUX.2 Klein 4B with small decoder",
    ),
    "flux2-klein-9b": ModelInfo(
        name="flux2-klein-9b",
        module="src.models.img_flux2_gen_9b",
        description="FLUX.2 Klein 9B",
    ),
    "flux2-klein-9b-bfs": ModelInfo(
        name="flux2-klein-9b-bfs",
        module="src.models.img_flux2_gen_9b_bfs",
        description="FLUX.2 Klein 9B with BFS LoRA",
    ),
    "flux2-klein-9b-small-decoder": ModelInfo(
        name="flux2-klein-9b-small-decoder",
        module="src.models.img_flux2_gen_9b_sm",
        description="FLUX.2 Klein 9B with small decoder",
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
        return getattr(module, "generate")
    except AttributeError as exc:
        raise RuntimeError(
            f"Model module '{model_info.module}' has no generate()"
        ) from exc
