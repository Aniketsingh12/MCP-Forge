"""Application configuration, read from environment variables.

Everything has a sane default so the platform runs with zero configuration.
The LLM layer defaults to ``none`` — OpenAPI generation is fully deterministic
and needs no model at all. Point ``LLM_PROVIDER`` at Ollama, Together AI, or
any OpenAI-compatible endpoint to get LLM-polished tool descriptions.
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path


class Settings:
    def __init__(self) -> None:
        # --- storage ---
        self.data_dir = Path(os.getenv("MCPFORGE_DATA_DIR", _default_data_dir()))
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.data_dir / "mcpforge.db"

        # --- LLM ---
        # provider: none | ollama | together | openai-compatible | anthropic
        self.llm_provider = os.getenv("LLM_PROVIDER", "none").strip().lower()
        self.llm_model = os.getenv("LLM_MODEL", _default_model(self.llm_provider))
        self.llm_base_url = os.getenv("LLM_BASE_URL", _default_base_url(self.llm_provider))
        self.llm_api_key = os.getenv("LLM_API_KEY", "")
        self.llm_timeout = float(os.getenv("LLM_TIMEOUT", "60"))
        # Shared secret gating the *metered* path. Description polishing is the
        # only feature that spends provider credits, and everything else here is
        # deterministic and free — so on a public deploy this keeps the demo
        # fully open while making the billable path unreachable to strangers.
        # Unset (the default) leaves polishing open, which is right for local use.
        self.llm_access_key = os.getenv("LLM_ACCESS_KEY", "")

        # --- abuse limits ---
        self.rate_limit_enabled = _truthy(os.getenv("RATE_LIMIT_ENABLED", "true"))
        # Specs are parsed in memory, so an unbounded upload is a memory DoS.
        self.max_spec_bytes = int(os.getenv("MAX_SPEC_BYTES", "2000000"))
        # Polishing sends every tool's metadata in one prompt; a 500-operation
        # spec would otherwise become a single very expensive request.
        self.max_llm_tools = int(os.getenv("MAX_LLM_TOOLS", "60"))

        # --- CORS (frontend dev server) ---
        self.cors_origins = [
            o.strip()
            for o in os.getenv(
                "CORS_ORIGINS",
                "http://localhost:5173,http://127.0.0.1:5173",
            ).split(",")
            if o.strip()
        ]

        # --- playground ---
        # Comma-separated allowlist of hosts the playground may call. Empty = allow any.
        self.playground_allowlist = [
            h.strip().lower()
            for h in os.getenv("PLAYGROUND_ALLOWLIST", "").split(",")
            if h.strip()
        ]
        self.playground_timeout = float(os.getenv("PLAYGROUND_TIMEOUT", "30"))

        # --- SDK introspection ---
        # Introspecting a module IMPORTS it, which runs its top-level code. On a
        # shared/hosted deployment that is remote code execution, so this is off
        # unless explicitly enabled, and can be narrowed to an allowlist.
        self.enable_sdk_introspection = _truthy(
            os.getenv("ENABLE_SDK_INTROSPECTION", "false")
        )
        self.sdk_allowed_modules = [
            m.strip()
            for m in os.getenv("SDK_ALLOWED_MODULES", "").split(",")
            if m.strip()
        ]

    def as_public_dict(self) -> dict:
        """Settings safe to expose to the frontend (no secrets)."""
        return {
            "llm_provider": self.llm_provider,
            "llm_model": self.llm_model,
            "llm_enabled": self.llm_provider != "none",
            # Whether an access key is *required* — never the key itself.
            "llm_requires_key": bool(self.llm_access_key),
            "sdk_introspection_enabled": self.enable_sdk_introspection,
            "sdk_allowed_modules": self.sdk_allowed_modules,
        }


def _truthy(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _default_data_dir() -> str:
    # Keep data next to the backend by default; overridable for containers.
    return str(Path(__file__).resolve().parent.parent / "data")


def _default_model(provider: str) -> str:
    return {
        "ollama": "llama3.1",
        # Together's own naming convention for its Turbo-optimized serverless
        # endpoint of Llama 3.3 70B — a strong general-purpose instruct model,
        # comfortably enough for rewriting tool descriptions.
        "together": "meta-llama/Llama-3.3-70B-Instruct-Turbo",
        "openai-compatible": "meta-llama/llama-3.1-8b-instruct",
        "anthropic": "claude-opus-4-8",
        "none": "",
    }.get(provider, "")


def _default_base_url(provider: str) -> str:
    return {
        "ollama": "http://localhost:11434/v1",
        "together": "https://api.together.ai/v1",
        "openai-compatible": "https://openrouter.ai/api/v1",
        "anthropic": "https://api.anthropic.com/v1",
        "none": "",
    }.get(provider, "")


@lru_cache
def get_settings() -> Settings:
    return Settings()
