from __future__ import annotations

import shutil
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from src.config import get_config, resolve_request_defaults
from src.models.registry import get_generator, get_model_info
from src.schemas import (
    GenerationRequest,
    GenerationResult,
    JobRecord,
    JobStatus,
    JobStatusResponse,
    JobSubmissionResponse,
    JobSummary,
)
from src.storage import get_job_output_dir, get_output_root

JOB_RECORD_FILENAME = "job.json"


class GenerationService:
    def __init__(self, max_workers: int | None = None):
        self._jobs: dict[str, JobRecord] = {}
        self._lock = threading.Lock()
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers or get_config().max_workers,
            thread_name_prefix="generation",
        )
        self._load_persisted_jobs()

    def submit(self, request: GenerationRequest) -> JobSubmissionResponse:
        model_info = get_model_info(request.model)
        resolved_request = resolve_request_defaults(request, model_info)

        job_id = str(uuid4())
        job = JobRecord(
            job_id=job_id,
            status=JobStatus.QUEUED,
            created_at=datetime.now(UTC),
            request=resolved_request,
        )

        with self._lock:
            self._jobs[job_id] = job
        self._persist_job(job)

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

    def list_jobs(
        self,
        limit: int = 20,
        offset: int = 0,
        model: str | None = None,
        status: JobStatus | None = None,
    ) -> tuple[list[JobSummary], int]:
        with self._lock:
            jobs = [job.model_copy(deep=True) for job in self._jobs.values()]

        if model is not None:
            jobs = [job for job in jobs if job.request.model == model]
        if status is not None:
            jobs = [job for job in jobs if job.status == status]

        jobs.sort(key=lambda job: job.created_at, reverse=True)
        total = len(jobs)
        page = jobs[offset : offset + limit]

        summaries = []
        for job in page:
            artifacts = job.result.artifacts if job.result else []
            summaries.append(
                JobSummary(
                    job_id=job.job_id,
                    status=job.status,
                    created_at=job.created_at,
                    completed_at=job.completed_at,
                    model=job.request.model,
                    prompt=job.request.prompt,
                    error=job.error,
                    artifact_count=len(artifacts),
                    thumbnail_url=artifacts[0].download_url if artifacts else None,
                )
            )
        return summaries, total

    def delete_job(self, job_id: str) -> bool:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return False
            if job.status in (JobStatus.QUEUED, JobStatus.RUNNING):
                raise ValueError("Cannot delete a job that is queued or running")
            del self._jobs[job_id]

        job_dir = get_output_root() / job_id
        if job_dir.is_dir():
            shutil.rmtree(job_dir, ignore_errors=True)
        return True

    def _persist_job(self, job: JobRecord) -> None:
        try:
            output_dir = get_job_output_dir(job.job_id)
            record_path = output_dir / JOB_RECORD_FILENAME
            record_path.write_text(job.model_dump_json(indent=2))
        except OSError:
            pass

    def _load_persisted_jobs(self) -> None:
        output_root = get_output_root()
        if not output_root.is_dir():
            return

        for record_path in sorted(output_root.glob(f"*/{JOB_RECORD_FILENAME}")):
            try:
                job = JobRecord.model_validate_json(record_path.read_text())
            except ValueError:
                continue

            if job.status in (JobStatus.QUEUED, JobStatus.RUNNING):
                job.status = JobStatus.FAILED
                job.error = "Job was interrupted by a service restart"
                job.completed_at = job.completed_at or datetime.now(UTC)
                self._persist_job(job)

            self._jobs[job.job_id] = job

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
            height=first_result.height,
            width=first_result.width,
            num_images_per_prompt=first_result.num_images_per_prompt,
            neg_prompt=request.neg_prompt,
            guidance_scale=first_result.guidance_scale,
            inf_steps=first_result.inf_steps,
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
                failed_job = job.model_copy(deep=True)
            self._persist_job(failed_job)
            return

        with self._lock:
            job = self._jobs[job_id]
            job.status = JobStatus.SUCCEEDED
            job.completed_at = result.completed_at
            job.result = result
            succeeded_job = job.model_copy(deep=True)
        self._persist_job(succeeded_job)


generation_service = GenerationService()
