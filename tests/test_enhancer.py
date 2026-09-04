from __future__ import annotations

from tests.conftest import wait_for_job


def test_llm_models_lists_configured_cloud_models(client):
    config = client.get("/config").json()
    config["llm"]["ollama"]["base_url"] = "http://127.0.0.1:1"  # unreachable
    config["llm"]["lmstudio"]["base_url"] = "http://127.0.0.1:1"
    config["llm"]["azure"]["endpoint"] = "https://example.openai.azure.com"
    config["llm"]["azure"]["deployments"] = ["gpt-4o", "gpt-4o-mini"]
    config["llm"]["bedrock"]["region"] = "us-east-1"
    config["llm"]["bedrock"]["model_ids"] = [
        "anthropic.claude-3-5-sonnet-20240620-v1:0"
    ]
    assert client.put("/config", json=config).status_code == 200

    models = client.get("/llm/models").json()
    ids = [model["id"] for model in models]
    assert "azure:gpt-4o" in ids
    assert "azure:gpt-4o-mini" in ids
    assert "bedrock:anthropic.claude-3-5-sonnet-20240620-v1:0" in ids


def test_job_with_enhancement_uses_llm_response(client, monkeypatch):
    from src.services import enhancer

    def fake_enhance(enhance, user_prompt):
        assert enhance.model == "ollama:test-model"
        assert enhance.system_prompt == "You are a prompt engineer."
        assert user_prompt == "a cat"
        return "a majestic fluffy cat wearing a tall black hat, studio lighting"

    monkeypatch.setattr(enhancer, "enhance_prompt", fake_enhance)

    response = client.post(
        "/jobs",
        json={
            "model": "fake-model",
            "prompt": "a cat",
            "enhance": {
                "model": "ollama:test-model",
                "system_prompt": "You are a prompt engineer.",
                "max_tokens": 256,
                "temperature": 0.5,
            },
        },
    )
    assert response.status_code == 202

    payload = wait_for_job(client, response.json()["job_id"])
    assert payload["status"] == "succeeded"
    result = payload["result"]
    assert (
        result["prompt"]
        == "a majestic fluffy cat wearing a tall black hat, studio lighting"
    )
    assert result["source_prompt"] == "a cat"
    assert result["llm_model"] == "ollama:test-model"


def test_job_without_enhancement_keeps_prompt(client):
    response = client.post(
        "/jobs", json={"model": "fake-model", "prompt": "plain prompt"}
    )
    payload = wait_for_job(client, response.json()["job_id"])
    assert payload["status"] == "succeeded"
    assert payload["result"]["prompt"] == "plain prompt"
    assert payload["result"]["source_prompt"] is None
    assert payload["result"]["llm_model"] is None


def test_enhancement_failure_fails_job(client, monkeypatch):
    from src.services import enhancer

    def failing_enhance(enhance, user_prompt):
        raise RuntimeError("LLM unavailable")

    monkeypatch.setattr(enhancer, "enhance_prompt", failing_enhance)

    response = client.post(
        "/jobs",
        json={
            "model": "fake-model",
            "prompt": "a cat",
            "enhance": {"model": "ollama:test-model"},
        },
    )
    payload = wait_for_job(client, response.json()["job_id"])
    assert payload["status"] == "failed"
    assert "LLM unavailable" in payload["error"]


def test_enabled_models_allowlist_flags_and_enforces(client):
    config = client.get("/config").json()
    config["llm"]["azure"]["endpoint"] = "https://example.openai.azure.com"
    config["llm"]["azure"]["deployments"] = ["gpt-4o", "gpt-4o-mini"]
    config["llm"]["enabled_models"] = ["azure:gpt-4o"]
    assert client.put("/config", json=config).status_code == 200

    models = {m["id"]: m for m in client.get("/llm/models").json()}
    assert models["azure:gpt-4o"]["enabled"] is True
    assert models["azure:gpt-4o-mini"]["enabled"] is False

    import pytest

    from src.schemas import PromptEnhancement
    from src.services.enhancer import enhance_prompt

    with pytest.raises(ValueError, match="not enabled for prompt enhancement"):
        enhance_prompt(PromptEnhancement(model="azure:gpt-4o-mini"), "hi")


def test_all_models_enabled_by_default(client):
    config = client.get("/config").json()
    config["llm"]["azure"]["endpoint"] = "https://example.openai.azure.com"
    config["llm"]["azure"]["deployments"] = ["gpt-4o"]
    config["llm"]["enabled_models"] = None
    assert client.put("/config", json=config).status_code == 200

    models = {m["id"]: m for m in client.get("/llm/models").json()}
    assert models["azure:gpt-4o"]["enabled"] is True


def test_invalid_llm_model_id_rejected():
    import pytest

    from src.schemas import PromptEnhancement
    from src.services.enhancer import enhance_prompt

    with pytest.raises(ValueError, match="Invalid LLM model id"):
        enhance_prompt(PromptEnhancement(model="no-provider-prefix"), "hi")


def test_unload_pipelines_clears_cached_pipes(client):
    import sys

    from src.models.registry import unload_pipelines

    fake_module = sys.modules["tests.fake_model"]
    fake_module.PIPE = object()
    try:
        unload_pipelines()
        assert fake_module.PIPE is None
    finally:
        if hasattr(fake_module, "PIPE"):
            del fake_module.PIPE


def test_pipelines_unloaded_after_job(client, monkeypatch):
    import sys

    fake_module = sys.modules["tests.fake_model"]
    fake_module.PIPE = object()
    try:
        response = client.post(
            "/jobs", json={"model": "fake-model", "prompt": "unload me"}
        )
        payload = wait_for_job(client, response.json()["job_id"])
        assert payload["status"] == "succeeded"
        assert fake_module.PIPE is None
    finally:
        if hasattr(fake_module, "PIPE"):
            del fake_module.PIPE


def test_pipelines_unloaded_after_failed_job(client):
    import sys

    fake_module = sys.modules["tests.fake_model"]
    fake_module.PIPE = object()
    try:
        response = client.post(
            "/jobs", json={"model": "fake-model", "prompt": "trigger-failure"}
        )
        payload = wait_for_job(client, response.json()["job_id"])
        assert payload["status"] == "failed"
        assert fake_module.PIPE is None
    finally:
        if hasattr(fake_module, "PIPE"):
            del fake_module.PIPE
