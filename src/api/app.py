from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from src.models.registry import get_model_info, list_models
from src.schemas import (
    GenerationRequest,
    JobStatus,
    JobStatusResponse,
    JobSubmissionResponse,
    ModelInfo,
)
from src.services.generation import generation_service


def create_app() -> FastAPI:
    app = FastAPI(
        title="im-gen API",
        version="0.1.0",
        description="Deferred image generation API for invoking registered models.",
    )

    @app.get("/health")
    def healthcheck() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/models", response_model=list[ModelInfo])
    def get_models() -> list[ModelInfo]:
        return list_models()

    @app.post("/jobs", status_code=202, response_model=JobSubmissionResponse)
    def create_job(request: GenerationRequest) -> JobSubmissionResponse:
        try:
            get_model_info(request.model)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return generation_service.submit(request)

    @app.get("/jobs/{job_id}", response_model=JobStatusResponse)
    def get_job(job_id: str) -> JobStatusResponse:
        response = generation_service.get_status(job_id)
        if response is None:
            raise HTTPException(status_code=404, detail="Job not found")
        return response

    @app.get("/jobs/{job_id}/result")
    def get_job_result(job_id: str) -> dict:
        response = generation_service.get_status(job_id)
        if response is None:
            raise HTTPException(status_code=404, detail="Job not found")
        if response.status == JobStatus.FAILED:
            raise HTTPException(status_code=500, detail=response.error or "Job failed")
        if response.status != JobStatus.SUCCEEDED or response.result is None:
            raise HTTPException(status_code=409, detail="Job is not complete yet")
        return response.result.model_dump(mode="json")

    @app.get("/jobs/{job_id}/artifacts/{filename}")
    def download_artifact(job_id: str, filename: str) -> FileResponse:
        response = generation_service.get_status(job_id)
        if response is None or response.result is None:
            raise HTTPException(status_code=404, detail="Artifact not found")

        for artifact in response.result.artifacts:
            if artifact.filename != filename:
                continue

            artifact_path = Path(artifact.path)
            if not artifact_path.is_file():
                raise HTTPException(status_code=404, detail="Artifact file not found")
            return FileResponse(
                path=artifact_path, media_type=artifact.media_type, filename=filename
            )

        raise HTTPException(status_code=404, detail="Artifact not found")

    return app
