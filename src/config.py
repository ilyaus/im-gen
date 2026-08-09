from __future__ import annotations

import os
import threading
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from src.schemas import GenerationRequest, ModelInfo


class ModelDefaultOverride(BaseModel):
    guidance_scale: float | None = Field(default=None, ge=0.0, le=20.0)
    inf_steps: int | None = Field(default=None, ge=1, le=100)
    height: int | None = Field(default=None, ge=64, le=2048)
    width: int | None = Field(default=None, ge=64, le=2048)
    num_images_per_prompt: int | None = Field(default=None, ge=1, le=8)


class BfsLoraConfig(BaseModel):
    source: str | None = None
    weight_name: str | None = None
    scale: float = 1.0


class ServiceConfig(BaseModel):
    output_root: str = "generated"
    max_workers: int = Field(default=1, ge=1, le=8)
    default_model: str | None = None
    bfs_lora: BfsLoraConfig = Field(default_factory=BfsLoraConfig)
    model_defaults: dict[str, ModelDefaultOverride] = Field(default_factory=dict)


_lock = threading.Lock()
_config: ServiceConfig | None = None


def get_config_path() -> Path:
    return Path(os.getenv("IM_GEN_CONFIG", "config.yaml"))


def _apply_env_fallbacks(data: dict) -> dict:
    if "output_root" not in data and os.getenv("OUTPUT_ROOT"):
        data["output_root"] = os.environ["OUTPUT_ROOT"]

    bfs = data.setdefault("bfs_lora", {})
    if isinstance(bfs, dict):
        if not bfs.get("source") and os.getenv("IM_GEN_BFS_LORA"):
            bfs["source"] = os.environ["IM_GEN_BFS_LORA"]
        if not bfs.get("weight_name") and os.getenv("IM_GEN_BFS_LORA_WEIGHT_NAME"):
            bfs["weight_name"] = os.environ["IM_GEN_BFS_LORA_WEIGHT_NAME"]
        if "scale" not in bfs and os.getenv("IM_GEN_BFS_LORA_SCALE"):
            bfs["scale"] = float(os.environ["IM_GEN_BFS_LORA_SCALE"])
    return data


def load_config() -> ServiceConfig:
    path = get_config_path()
    data: dict = {}
    if path.is_file():
        loaded = yaml.safe_load(path.read_text())
        if isinstance(loaded, dict):
            data = loaded
    return ServiceConfig.model_validate(_apply_env_fallbacks(data))


def get_config() -> ServiceConfig:
    global _config
    with _lock:
        if _config is None:
            _config = load_config()
        return _config


def update_config(new_config: ServiceConfig) -> ServiceConfig:
    global _config
    path = get_config_path()
    with _lock:
        path.write_text(
            yaml.safe_dump(
                new_config.model_dump(mode="json", exclude_none=True),
                sort_keys=False,
            )
        )
        _config = new_config
        return _config


def reset_config_cache() -> None:
    global _config
    with _lock:
        _config = None


def resolve_request_defaults(
    request: GenerationRequest, model_info: ModelInfo
) -> GenerationRequest:
    config = get_config()
    override = config.model_defaults.get(request.model, ModelDefaultOverride())
    defaults = model_info.defaults

    def pick(field: str):
        value = getattr(request, field)
        if value is not None:
            return value
        override_value = getattr(override, field)
        if override_value is not None:
            return override_value
        return getattr(defaults, field)

    updates = {
        field: pick(field)
        for field in (
            "guidance_scale",
            "inf_steps",
            "height",
            "width",
            "num_images_per_prompt",
        )
    }
    if request.test_gen is not None:
        updates["num_images_per_prompt"] = 1
    return request.model_copy(deep=True, update=updates)
