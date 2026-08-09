from __future__ import annotations

import pytest


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("IM_GEN_CONFIG", str(tmp_path / "config.yaml"))
    monkeypatch.setenv("OUTPUT_ROOT", str(tmp_path / "generated"))

    from src import config

    config.reset_config_cache()

    from src.models import registry
    from src.schemas import ModelCapabilities, ModelDefaults, ModelInfo

    monkeypatch.setitem(
        registry.MODEL_REGISTRY,
        "fake-model",
        ModelInfo(
            name="fake-model",
            module="tests.fake_model",
            description="Fast fake model for tests",
            defaults=ModelDefaults(
                guidance_scale=2.0, inf_steps=3, height=64, width=64
            ),
            capabilities=ModelCapabilities(),
        ),
    )

    import src.api.app as app_module
    from src.services.generation import GenerationService

    service = GenerationService()
    monkeypatch.setattr("src.services.generation.generation_service", service)
    monkeypatch.setattr(app_module, "generation_service", service)

    from fastapi.testclient import TestClient

    yield TestClient(app_module.create_app())

    config.reset_config_cache()


def wait_for_job(client, job_id: str, timeout: float = 10.0) -> dict:
    import time

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        response = client.get(f"/jobs/{job_id}")
        assert response.status_code == 200
        payload = response.json()
        if payload["status"] in ("succeeded", "failed"):
            return payload
        time.sleep(0.05)
    raise AssertionError(f"Job {job_id} did not finish within {timeout}s")
