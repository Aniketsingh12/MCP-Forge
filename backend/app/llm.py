"""LLM abstraction.

One synchronous ``complete()`` entry point routes to whichever provider is
configured. Everything speaks the OpenAI chat-completions shape, which covers:

  * ``ollama``            — local open-source models (llama3.1, qwen2.5, etc.)
  * ``together``          — Together AI's hosted open-weight models
  * ``openai-compatible`` — OpenRouter, Groq, vLLM, LM Studio, ...
  * ``anthropic``         — Claude (native messages API)
  * ``none``              — disabled; callers fall back to deterministic output

The platform never *requires* an LLM: OpenAPI generation is deterministic.
The model is only used to polish tool descriptions when the user opts in.
"""
from __future__ import annotations

import json
from typing import Optional

import httpx

from .config import get_settings


class LLMError(RuntimeError):
    pass


def is_enabled() -> bool:
    return get_settings().llm_provider != "none"


def complete(system: str, user: str, *, json_mode: bool = False) -> str:
    """Return the model's text completion. Raises LLMError on failure."""
    s = get_settings()
    provider = s.llm_provider

    if provider == "none":
        raise LLMError("LLM is disabled (LLM_PROVIDER=none)")
    if provider == "anthropic":
        return _anthropic(system, user, json_mode)
    # ollama, together, and openai-compatible all speak the OpenAI chat shape.
    return _openai_chat(system, user, json_mode)


def complete_json(system: str, user: str) -> Optional[dict | list]:
    """Convenience wrapper that parses a JSON object/array out of the reply."""
    raw = complete(system, user, json_mode=True)
    return _extract_json(raw)


# --------------------------------------------------------------------------- #
# Providers
# --------------------------------------------------------------------------- #
def _openai_chat(system: str, user: str, json_mode: bool) -> str:
    s = get_settings()
    headers = {"Content-Type": "application/json"}
    if s.llm_api_key:
        headers["Authorization"] = f"Bearer {s.llm_api_key}"
    payload = {
        "model": s.llm_model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.2,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    url = s.llm_base_url.rstrip("/") + "/chat/completions"
    try:
        r = httpx.post(url, headers=headers, json=payload, timeout=s.llm_timeout)
        r.raise_for_status()
        data = r.json()
        return data["choices"][0]["message"]["content"] or ""
    except httpx.HTTPStatusError as e:  # pragma: no cover - network dependent
        raise LLMError(f"LLM HTTP {e.response.status_code}: {e.response.text[:200]}")
    except Exception as e:  # pragma: no cover
        raise LLMError(f"LLM request failed: {e}")


def _anthropic(system: str, user: str, json_mode: bool) -> str:
    s = get_settings()
    headers = {
        "Content-Type": "application/json",
        "x-api-key": s.llm_api_key,
        "anthropic-version": "2023-06-01",
    }
    if json_mode:
        user = user + "\n\nRespond with a single valid JSON value and nothing else."
    payload = {
        "model": s.llm_model,
        "max_tokens": 2048,
        "system": system,
        "messages": [{"role": "user", "content": user}],
    }
    url = s.llm_base_url.rstrip("/") + "/messages"
    try:
        r = httpx.post(url, headers=headers, json=payload, timeout=s.llm_timeout)
        r.raise_for_status()
        data = r.json()
        return "".join(block.get("text", "") for block in data.get("content", []))
    except httpx.HTTPStatusError as e:  # pragma: no cover
        raise LLMError(f"LLM HTTP {e.response.status_code}: {e.response.text[:200]}")
    except Exception as e:  # pragma: no cover
        raise LLMError(f"LLM request failed: {e}")


def _extract_json(raw: str) -> Optional[dict | list]:
    raw = raw.strip()
    # Strip markdown fences if a chatty model added them.
    if raw.startswith("```"):
        raw = raw.split("```", 2)[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip("` \n")
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Last resort: grab the outermost {...} or [...].
        for open_c, close_c in (("{", "}"), ("[", "]")):
            start, end = raw.find(open_c), raw.rfind(close_c)
            if start != -1 and end > start:
                try:
                    return json.loads(raw[start : end + 1])
                except json.JSONDecodeError:
                    continue
    return None
