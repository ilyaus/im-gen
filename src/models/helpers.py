from __future__ import annotations

from pathlib import Path
from typing import Any, cast

from PIL import Image

from src.schemas import GeneratedArtifact


def load_input_images(image_paths: list[str | None] | None) -> list[Image.Image] | None:
    valid_paths = [p for p in (image_paths or []) if p]
    if not valid_paths:
        return None

    loaded_images: list[Image.Image] = []
    for image_path in valid_paths:
        loaded_images.append(Image.open(image_path).convert("RGB"))
    return loaded_images


def save_generated_images(
    images: list[Image.Image],
    output_dir: Path,
    output_prefix: str,
    seed: int | None = None,
) -> list[GeneratedArtifact]:
    artifacts: list[GeneratedArtifact] = []

    for index, image in enumerate(images, start=1):
        filename = f"{output_prefix}_{index}.png"
        output_path = output_dir / filename
        image.save(output_path)
        artifacts.append(
            GeneratedArtifact(
                filename=filename,
                path=str(output_path.resolve()),
                size_bytes=output_path.stat().st_size,
                seed=seed,
            )
        )

    return artifacts


def extract_generated_images(result: Any) -> list[Image.Image]:
    images = getattr(result, "images", None)
    if not isinstance(images, list) or not images:
        raise RuntimeError("Model pipeline returned no generated images")
    return cast(list[Image.Image], images)
