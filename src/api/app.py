from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.config import ServiceConfig, get_config, update_config
from src.models.registry import get_model_info, list_models
from src.schemas import (
    GenerationRequest,
    JobListResponse,
    JobStatus,
    JobStatusResponse,
    JobSubmissionResponse,
    ModelInfo,
)
from src.services.generation import generation_service

UI_DIST_DIR = Path(__file__).resolve().parent.parent.parent / "ui" / "dist"


class SPAStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope):
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            if exc.status_code == 404:
                return await super().get_response("index.html", scope)
            raise


def create_app() -> FastAPI:
    app = FastAPI(
        title="im-gen API",
        version="0.2.0",
        description="Deferred image generation API for invoking registered models.",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def healthcheck() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/models", response_model=list[ModelInfo])
    def get_models() -> list[ModelInfo]:
        return list_models()

    @app.get("/config", response_model=ServiceConfig)
    def read_config() -> ServiceConfig:
        return get_config()

    @app.put("/config", response_model=ServiceConfig)
    def write_config(new_config: ServiceConfig) -> ServiceConfig:
        for model_name in new_config.model_defaults:
            try:
                get_model_info(model_name)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
        if new_config.default_model is not None:
            try:
                get_model_info(new_config.default_model)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
        return update_config(new_config)

    @app.post("/jobs", status_code=202, response_model=JobSubmissionResponse)
    def create_job(request: GenerationRequest) -> JobSubmissionResponse:
        try:
            get_model_info(request.model)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return generation_service.submit(request)

    @app.get("/jobs", response_model=JobListResponse)
    def list_jobs(
        limit: int = 20,
        offset: int = 0,
        model: str | None = None,
        status: JobStatus | None = None,
    ) -> JobListResponse:
        limit = max(1, min(limit, 100))
        offset = max(0, offset)
        jobs, total = generation_service.list_jobs(
            limit=limit, offset=offset, model=model, status=status
        )
        return JobListResponse(jobs=jobs, total=total, limit=limit, offset=offset)

    @app.get("/jobs/{job_id}", response_model=JobStatusResponse)
    def get_job(job_id: str) -> JobStatusResponse:
        response = generation_service.get_status(job_id)
        if response is None:
            raise HTTPException(status_code=404, detail="Job not found")
        return response

    @app.delete("/jobs/{job_id}", status_code=204)
    def delete_job(job_id: str) -> None:
        try:
            deleted = generation_service.delete_job(job_id)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        if not deleted:
            raise HTTPException(status_code=404, detail="Job not found")

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

    if UI_DIST_DIR.is_dir():
        app.mount("/", SPAStaticFiles(directory=UI_DIST_DIR, html=True), name="ui")

    return app
