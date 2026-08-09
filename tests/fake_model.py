from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter

from PIL import Image

from src.models.helpers import save_generated_images
from src.schemas import GenerationRequest, GenerationResult


def generate(
    request: GenerationRequest, output_dir: Path, job_id: str
) -> GenerationResult:
    started_at = datetime.now(UTC)
    started = perf_counter()

    if request.prompt == "trigger-failure":
        raise RuntimeError("fake generation failure")

    num_images = request.num_images_per_prompt or 1
    images = [
        Image.new("RGB", (request.width or 8, request.height or 8), "purple")
        for _ in range(num_images)
    ]

    artifacts = save_generated_images(
        images=images,
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
        height=request.height or 8,
        width=request.width or 8,
        num_images_per_prompt=num_images,
        neg_prompt=request.neg_prompt,
        guidance_scale=request.guidance_scale if request.guidance_scale is not None else 1.0,
        inf_steps=request.inf_steps or 4,
        seed=request.seed,
        device="cpu",
        started_at=started_at,
        completed_at=completed_at,
        duration_seconds=perf_counter() - started,
    )
