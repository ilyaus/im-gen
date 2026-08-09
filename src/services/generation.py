from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from src.models.registry import get_generator
from src.schemas import (
    GenerationRequest,
    JobRecord,
    GenerationResult,
    JobStatus,
    JobStatusResponse,
    JobSubmissionResponse,
)
from src.storage import get_job_output_dir


class GenerationService:
    def __init__(self, max_workers: int = 1):
        self._jobs: dict[str, JobRecord] = {}
        self._lock = threading.Lock()
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers, thread_name_prefix="generation"
        )

    def submit(self, request: GenerationRequest) -> JobSubmissionResponse:
        job_id = str(uuid4())
        job = JobRecord(
            job_id=job_id,
            status=JobStatus.QUEUED,
            created_at=datetime.now(UTC),
            request=request,
        )

        with self._lock:
            self._jobs[job_id] = job

        self._executor.submit(self._run_job, job_id)
        return JobSubmissionResponse(
            job_id=job_id,
            status=job.status,
            status_url=f"/jobs/{job_id}",
            result_url=f"/jobs/{job_id}/result",
        )

    def get(self, job_id: str) -> JobRecord | None:
        with self._lock:
            job = self._jobs.get(job_id)
            return job.model_copy(deep=True) if job else None

    def get_status(self, job_id: str) -> JobStatusResponse | None:
        job = self.get(job_id)
        if job is None:
            return None

        return JobStatusResponse(
            job_id=job.job_id,
            status=job.status,
            created_at=job.created_at,
            started_at=job.started_at,
            completed_at=job.completed_at,
            error=job.error,
            result=job.result,
        )

    def _generate_result(
        self, request: GenerationRequest, output_dir: Path, job_id: str
    ) -> GenerationResult:
        generator = get_generator(request.model)
        if request.test_gen is None:
            base_prefix = request.output_prefix or request.model.replace("-", "_")
            seeded_request = request.model_copy(
                deep=True,
                update={"output_prefix": f"{base_prefix}_{request.seed}"},
            )
            return generator(request=seeded_request, output_dir=output_dir, job_id=job_id)

        results: list[GenerationResult] = []
        for index in range(request.test_gen.count):
            seed = request.seed + (index * request.test_gen.seed_inc)
            seeded_request = request.model_copy(
                deep=True,
                update={
                    "seed": seed,
                    "test_gen": None,
                    "output_prefix": self._seeded_output_prefix(request, seed),
                },
            )
            results.append(
                generator(request=seeded_request, output_dir=output_dir, job_id=job_id)
            )

        if not results:
            raise RuntimeError("test_gen did not produce any images")

        first_result = results[0]
        last_result = results[-1]
        return GenerationResult(
            model=request.model,
            prompt=request.prompt,
            output_dir=str(output_dir.resolve()),
            artifacts=[
                artifact for result in results for artifact in result.artifacts
            ],
            height=request.height,
            width=request.width,
            num_images_per_prompt=request.num_images_per_prompt,
            neg_prompt=request.neg_prompt,
            guidance_scale=first_result.guidance_scale,
            inf_steps=request.inf_steps,
            seed=request.seed,
            device=first_result.device,
            started_at=first_result.started_at,
            completed_at=last_result.completed_at,
            duration_seconds=sum(result.duration_seconds for result in results),
        )

    def _seeded_output_prefix(self, request: GenerationRequest, seed: int) -> str:
        base_prefix = request.output_prefix or request.model.replace("-", "_")
        return f"{base_prefix}_seed_{seed}"

    def _run_job(self, job_id: str) -> None:
        with self._lock:
            job = self._jobs[job_id]
            job.status = JobStatus.RUNNING
            job.started_at = datetime.now(UTC)
            request = job.request.model_copy(deep=True)

        try:
            output_dir = get_job_output_dir(job_id)
            result = self._generate_result(
                request=request,
                output_dir=output_dir,
                job_id=job_id,
            )
        except Exception as exc:  # noqa: BLE001
            with self._lock:
                job = self._jobs[job_id]
                job.status = JobStatus.FAILED
                job.completed_at = datetime.now(UTC)
                job.error = str(exc)
            return

        with self._lock:
            job = self._jobs[job_id]
            job.status = JobStatus.SUCCEEDED
            job.completed_at = result.completed_at
            job.result = result


generation_service = GenerationService()
