from __future__ import annotations

from datetime import datetime
from enum import StrEnum
import random

from pydantic import BaseModel, Field, model_validator


def random_int() -> int:
    return random.randint(0, 999_999_999_999)


class TestImageGen(BaseModel):
    count: int = Field(ge=1)
    seed_inc: int


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class GenerationRequest(BaseModel):
    model: str = Field(description="Registered model name to invoke")
    prompt: str = Field(min_length=1, description="Text prompt used for generation")
    height: int = Field(default=1024, ge=64, le=2048)
    width: int = Field(default=512, ge=64, le=2048)
    num_images_per_prompt: int = Field(default=1, ge=1, le=8)
    neg_prompt: str | None = Field(default=None, description="Optional negative prompt")
    images: list[str] | None = Field(
        default=None,
        description="Optional local image paths for image-conditioned models",
    )
    guidance_scale: float | None = Field(default=None, ge=0.0, le=20.0)
    inf_steps: int = Field(default=4, ge=1, le=100)
    seed: int = Field(default_factory=random_int)
    device: str | None = Field(
        default=None, description="Execution device, e.g. cuda or cpu"
    )
    output_prefix: str | None = Field(
        default=None,
        description="Optional output filename prefix without extension",
    )
    lora_weight_name: str | None = Field(
        default="bfs_head_v1_flux-klein_9b_step3750_rank64.safetensors",
        description="LoRA checkpoint filename; used by BFS model when loading adapter weights",
    )
    test_gen: TestImageGen | None = Field(default=None)

    @model_validator(mode="after")
    def validate_test_gen(self) -> GenerationRequest:
        if self.test_gen is not None and self.num_images_per_prompt != 1:
            raise ValueError(
                "test_gen requires num_images_per_prompt=1 so each seed produces one image"
            )
        return self


class GeneratedArtifact(BaseModel):
    filename: str
    path: str
    media_type: str = "image/png"
    size_bytes: int
    download_url: str | None = None
    seed: int | None = None


class GenerationResult(BaseModel):
    model: str
    prompt: str
    output_dir: str
    artifacts: list[GeneratedArtifact]
    height: int
    width: int
    num_images_per_prompt: int
    neg_prompt: str | None = None
    guidance_scale: float | None = None
    inf_steps: int
    seed: int
    device: str | None = None
    started_at: datetime
    completed_at: datetime
    duration_seconds: float


class JobRecord(BaseModel):
    job_id: str
    status: JobStatus
    created_at: datetime
    request: GenerationRequest
    started_at: datetime | None = None
    completed_at: datetime | None = None
    result: GenerationResult | None = None
    error: str | None = None


class JobSubmissionResponse(BaseModel):
    job_id: str
    status: JobStatus
    status_url: str
    result_url: str


class JobStatusResponse(BaseModel):
    job_id: str
    status: JobStatus
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None
    result: GenerationResult | None = None


class ModelInfo(BaseModel):
    name: str
    module: str
    description: str
