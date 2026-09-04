from __future__ import annotations

import logging
from typing import Any

import httpx

from src.config import get_config
from src.schemas import LlmModelInfo, PromptEnhancement

logger = logging.getLogger(__name__)

DISCOVERY_TIMEOUT_SECONDS = 2.0


def _list_ollama_models(base_url: str) -> list[LlmModelInfo]:
    try:
        response = httpx.get(
            f"{base_url.rstrip('/')}/api/tags", timeout=DISCOVERY_TIMEOUT_SECONDS
        )
        response.raise_for_status()
        models = response.json().get("models", [])
    except Exception as exc:  # noqa: BLE001
        logger.debug("Ollama discovery failed: %s", exc)
        return []
    return [
        LlmModelInfo(id=f"ollama:{m['name']}", provider="ollama", model=m["name"])
        for m in models
        if isinstance(m, dict) and m.get("name")
    ]


def _list_lmstudio_models(base_url: str) -> list[LlmModelInfo]:
    try:
        response = httpx.get(
            f"{base_url.rstrip('/')}/models", timeout=DISCOVERY_TIMEOUT_SECONDS
        )
        response.raise_for_status()
        models = response.json().get("data", [])
    except Exception as exc:  # noqa: BLE001
        logger.debug("LM Studio discovery failed: %s", exc)
        return []
    return [
        LlmModelInfo(id=f"lmstudio:{m['id']}", provider="lmstudio", model=m["id"])
        for m in models
        if isinstance(m, dict) and m.get("id")
    ]


def list_llm_models() -> list[LlmModelInfo]:
    llm = get_config().llm
    models: list[LlmModelInfo] = []
    if llm.ollama.base_url:
        models.extend(_list_ollama_models(llm.ollama.base_url))
    if llm.lmstudio.base_url:
        models.extend(_list_lmstudio_models(llm.lmstudio.base_url))
    if llm.azure.endpoint:
        models.extend(
            LlmModelInfo(id=f"azure:{name}", provider="azure", model=name)
            for name in llm.azure.deployments
        )
    if llm.bedrock.region:
        models.extend(
            LlmModelInfo(id=f"bedrock:{model_id}", provider="bedrock", model=model_id)
            for model_id in llm.bedrock.model_ids
        )

    allowed = llm.enabled_models
    if allowed is not None:
        allowed_set = set(allowed)
        for model in models:
            model.enabled = model.id in allowed_set
    return models


def _build_chat_model(provider: str, model: str, max_tokens: int, temperature: float):
    llm = get_config().llm

    if provider == "ollama":
        from langchain_ollama import ChatOllama

        return ChatOllama(
            model=model,
            base_url=llm.ollama.base_url,
            num_predict=max_tokens,
            temperature=temperature,
        )
    if provider == "lmstudio":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=model,
            base_url=llm.lmstudio.base_url,
            api_key="lm-studio",
            max_completion_tokens=max_tokens,
            temperature=temperature,
        )
    if provider == "azure":
        from langchain_openai import AzureChatOpenAI

        if not llm.azure.endpoint:
            raise ValueError(
                "Azure OpenAI endpoint is not configured; "
                "set it in Settings or via AZURE_OPENAI_ENDPOINT"
            )
        # API key is read from the AZURE_OPENAI_API_KEY environment variable.
        return AzureChatOpenAI(
            azure_deployment=model,
            azure_endpoint=llm.azure.endpoint,
            api_version=llm.azure.api_version,
            max_completion_tokens=max_tokens,
            temperature=temperature,
        )
    if provider == "bedrock":
        from langchain_aws import ChatBedrockConverse

        if not llm.bedrock.region:
            raise ValueError(
                "Bedrock region is not configured; "
                "set it in Settings or via AWS_REGION"
            )
        # Credentials are resolved from the environment / AWS profile.
        return ChatBedrockConverse(
            model_id=model,
            region_name=llm.bedrock.region,
            max_tokens=max_tokens,
            temperature=temperature,
        )
    raise ValueError(
        f"Unknown LLM provider '{provider}'. "
        "Expected one of: ollama, lmstudio, azure, bedrock"
    )


def _extract_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
        return "".join(parts)
    return str(content)


def enhance_prompt(enhance: PromptEnhancement, user_prompt: str) -> str:
    provider, separator, model = enhance.model.partition(":")
    if not separator or not model:
        raise ValueError(
            f"Invalid LLM model id '{enhance.model}'. "
            "Expected format '<provider>:<model>', e.g. 'ollama:llama3.2'"
        )

    llm = get_config().llm
    if llm.enabled_models is not None and enhance.model not in llm.enabled_models:
        raise ValueError(
            f"LLM model '{enhance.model}' is not enabled for prompt enhancement; "
            "enable it on the Settings page"
        )

    max_tokens = enhance.max_tokens or llm.default_max_tokens
    temperature = (
        enhance.temperature
        if enhance.temperature is not None
        else llm.default_temperature
    )

    chat = _build_chat_model(provider, model, max_tokens, temperature)

    messages: list[tuple[str, str]] = []
    if enhance.system_prompt:
        messages.append(("system", enhance.system_prompt))
    messages.append(("human", user_prompt))

    try:
        response = chat.invoke(messages)
    except Exception as exc:
        raise RuntimeError(
            f"Prompt enhancement with '{enhance.model}' failed: {exc}"
        ) from exc

    text = _extract_text(response.content).strip()
    if not text:
        raise RuntimeError(
            f"LLM '{enhance.model}' returned an empty response; "
            "cannot use it as an image prompt"
        )
    return text
