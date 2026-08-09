from __future__ import annotations

from pathlib import Path

from tests.conftest import wait_for_job


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_models_include_defaults_and_capabilities(client):
    response = client.get("/models")
    assert response.status_code == 200
    models = {model["name"]: model for model in response.json()}
    assert "fake-model" in models
    assert models["fake-model"]["defaults"]["inf_steps"] == 3
    assert models["fake-model"]["capabilities"]["supports_negative_prompt"] is True
    assert "flux2-klein-9b" in models
    assert models["flux2-klein-9b"]["capabilities"]["supports_image_input"] is True


def test_unknown_model_rejected(client):
    response = client.post("/jobs", json={"model": "nope", "prompt": "hi"})
    assert response.status_code == 400


def test_test_gen_with_multi_image_rejected(client):
    response = client.post(
        "/jobs",
        json={
            "model": "fake-model",
            "prompt": "hi",
            "num_images_per_prompt": 2,
            "test_gen": {"count": 2, "seed_inc": 1},
        },
    )
    assert response.status_code == 422


def test_job_lifecycle_and_artifact_download(client):
    response = client.post(
        "/jobs", json={"model": "fake-model", "prompt": "a purple square"}
    )
    assert response.status_code == 202
    job_id = response.json()["job_id"]

    payload = wait_for_job(client, job_id)
    assert payload["status"] == "succeeded"
    result = payload["result"]
    # Defaults resolved from registry ModelDefaults
    assert result["height"] == 64
    assert result["width"] == 64
    assert result["inf_steps"] == 3
    assert result["guidance_scale"] == 2.0
    assert len(result["artifacts"]) == 1

    artifact = result["artifacts"][0]
    download = client.get(artifact["download_url"])
    assert download.status_code == 200
    assert download.headers["content-type"] == "image/png"

    # job.json persisted next to artifacts
    assert (Path(result["output_dir"]) / "job.json").is_file()


def test_config_overrides_apply_to_jobs(client):
    config = client.get("/config").json()
    config["model_defaults"] = {"fake-model": {"inf_steps": 7, "height": 128}}
    put = client.put("/config", json=config)
    assert put.status_code == 200, put.text

    response = client.post(
        "/jobs", json={"model": "fake-model", "prompt": "with overrides"}
    )
    payload = wait_for_job(client, response.json()["job_id"])
    assert payload["status"] == "succeeded"
    assert payload["result"]["inf_steps"] == 7
    assert payload["result"]["height"] == 128
    # Explicit request values still win
    response = client.post(
        "/jobs",
        json={"model": "fake-model", "prompt": "explicit", "inf_steps": 9},
    )
    payload = wait_for_job(client, response.json()["job_id"])
    assert payload["result"]["inf_steps"] == 9


def test_config_rejects_unknown_model_override(client):
    config = client.get("/config").json()
    config["model_defaults"] = {"not-a-model": {"inf_steps": 7}}
    assert client.put("/config", json=config).status_code == 400


def test_config_roundtrip_persists_to_file(client, tmp_path):
    config = client.get("/config").json()
    config["max_workers"] = 2
    config["default_model"] = "fake-model"
    assert client.put("/config", json=config).status_code == 200

    fetched = client.get("/config").json()
    assert fetched["max_workers"] == 2
    assert fetched["default_model"] == "fake-model"
    assert (tmp_path / "config.yaml").is_file()


def test_job_list_filters_and_delete(client):
    ok = client.post("/jobs", json={"model": "fake-model", "prompt": "good"})
    bad = client.post(
        "/jobs", json={"model": "fake-model", "prompt": "trigger-failure"}
    )
    ok_id = ok.json()["job_id"]
    bad_id = bad.json()["job_id"]
    wait_for_job(client, ok_id)
    wait_for_job(client, bad_id)

    listing = client.get("/jobs").json()
    assert listing["total"] == 2

    failed = client.get("/jobs", params={"status": "failed"}).json()
    assert failed["total"] == 1
    assert failed["jobs"][0]["job_id"] == bad_id
    assert failed["jobs"][0]["error"] == "fake generation failure"

    succeeded = client.get("/jobs", params={"status": "succeeded"}).json()
    assert succeeded["jobs"][0]["thumbnail_url"] is not None

    assert client.delete(f"/jobs/{ok_id}").status_code == 204
    assert client.get(f"/jobs/{ok_id}").status_code == 404
    assert client.delete(f"/jobs/{ok_id}").status_code == 404
    assert client.get("/jobs").json()["total"] == 1


def test_jobs_rehydrated_after_restart(client):
    response = client.post(
        "/jobs", json={"model": "fake-model", "prompt": "persist me"}
    )
    job_id = response.json()["job_id"]
    wait_for_job(client, job_id)

    from src.services.generation import GenerationService

    restarted = GenerationService()
    jobs, total = restarted.list_jobs()
    assert total == 1
    assert jobs[0].job_id == job_id
    assert jobs[0].status == "succeeded"
    assert jobs[0].artifact_count == 1


def test_test_gen_seed_sweep(client):
    response = client.post(
        "/jobs",
        json={
            "model": "fake-model",
            "prompt": "sweep",
            "seed": 100,
            "test_gen": {"count": 3, "seed_inc": 10},
        },
    )
    payload = wait_for_job(client, response.json()["job_id"])
    assert payload["status"] == "succeeded"
    artifacts = payload["result"]["artifacts"]
    assert len(artifacts) == 3
    assert [artifact["seed"] for artifact in artifacts] == [100, 110, 120]
