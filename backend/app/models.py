"""Pydantic models shared across the API."""
from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

AuthType = Literal["none", "api_key", "bearer", "basic"]
# "http" wraps a REST API; "python_sdk" wraps an installed Python library.
ServerKind = Literal["http", "python_sdk"]
ProjectStatus = Literal["draft", "proposed", "generated", "tested"]


class ToolParam(BaseModel):
    name: str
    type: str = "string"  # JSON schema primitive: string/integer/number/boolean/array/object
    description: str = ""
    required: bool = False
    location: Literal["query", "path", "header", "body", "python_arg"] = "query"
    # For body params we keep the raw JSON schema so nested objects survive.
    # (named json_schema to avoid shadowing pydantic's BaseModel.schema)
    json_schema: Optional[dict[str, Any]] = None


class PollingConfig(BaseModel):
    """Turn a submit → poll → fetch-result API into a single blocking tool.

    Generative-AI APIs (image/video/audio jobs) typically return a job id, then
    expect the caller to poll a status endpoint until it completes. Without this
    an agent sees two unrelated tools and has to invent the loop itself.
    """
    enabled: bool = False
    # Where the submit response carries the job id, e.g. "id" or "data.job_id".
    id_field: str = "id"
    # Status endpoint; "{job_id}" is substituted, e.g. "/jobs/{job_id}".
    status_path: str = ""
    # Where the status response carries the state, e.g. "status".
    status_field: str = "status"
    success_values: list[str] = Field(
        default_factory=lambda: ["succeeded", "completed", "success", "done", "finished"]
    )
    failure_values: list[str] = Field(
        default_factory=lambda: ["failed", "error", "cancelled", "canceled"]
    )
    interval_seconds: float = 2.0
    max_attempts: int = 60


class ProposedTool(BaseModel):
    name: str
    description: str = ""
    method: str = "GET"
    path: str = "/"
    params: list[ToolParam] = Field(default_factory=list)
    confirm_required: bool = False  # write-actions gated behind a confirm flag
    enabled: bool = True
    polling: PollingConfig = Field(default_factory=PollingConfig)

    @property
    def is_write(self) -> bool:
        return self.method.upper() in {"POST", "PUT", "PATCH", "DELETE"}


class AuthConfig(BaseModel):
    type: AuthType = "api_key"
    # Where an API key is injected.
    location: Literal["header", "query"] = "header"
    param_name: str = "Authorization"
    # For api_key header: the value prefix, e.g. "Bearer " or "Token ".
    value_prefix: str = ""


class ProjectCreate(BaseModel):
    name: str
    description: str = ""


class ParseRequest(BaseModel):
    """Body for parsing an OpenAPI spec into a tool proposal."""
    spec_text: Optional[str] = None  # raw JSON or YAML
    spec_url: Optional[str] = None
    use_llm: bool = False  # polish descriptions with the configured model


class ParseResult(BaseModel):
    api_title: str = ""
    api_version: str = ""
    base_url: str = ""
    server_slug: str = ""
    auth: AuthConfig
    tools: list[ProposedTool]
    llm_used: bool = False
    kind: ServerKind = "http"
    sdk_module: str = ""


class GenerateRequest(BaseModel):
    server_slug: str
    api_title: str = ""
    base_url: str = ""
    auth: AuthConfig
    tools: list[ProposedTool]
    kind: ServerKind = "http"
    sdk_module: str = ""


class GeneratedFile(BaseModel):
    path: str
    content: str
    language: str = "python"


class GenerateResult(BaseModel):
    server_slug: str
    files: list[GeneratedFile]
    valid: bool
    validation_messages: list[str] = Field(default_factory=list)


class ProjectState(BaseModel):
    """Everything persisted for a project."""
    id: str
    name: str
    description: str = ""
    status: ProjectStatus = "draft"
    created_at: str
    updated_at: str
    parse_result: Optional[ParseResult] = None
    generate_result: Optional[GenerateResult] = None
