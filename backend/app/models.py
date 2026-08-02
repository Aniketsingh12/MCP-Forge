"""Pydantic models shared across the API."""
from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

AuthType = Literal["none", "api_key", "bearer", "basic"]
ProjectStatus = Literal["draft", "proposed", "generated", "tested"]


class ToolParam(BaseModel):
    name: str
    type: str = "string"  # JSON schema primitive: string/integer/number/boolean/array/object
    description: str = ""
    required: bool = False
    location: Literal["query", "path", "header", "body"] = "query"
    # For body params we keep the raw JSON schema so nested objects survive.
    # (named json_schema to avoid shadowing pydantic's BaseModel.schema)
    json_schema: Optional[dict[str, Any]] = None


class ProposedTool(BaseModel):
    name: str
    description: str = ""
    method: str = "GET"
    path: str = "/"
    params: list[ToolParam] = Field(default_factory=list)
    confirm_required: bool = False  # write-actions gated behind a confirm flag
    enabled: bool = True

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


class GenerateRequest(BaseModel):
    server_slug: str
    api_title: str = ""
    base_url: str
    auth: AuthConfig
    tools: list[ProposedTool]


class GeneratedFile(BaseModel):
    path: str
    content: str
    language: str = "python"


class GenerateResult(BaseModel):
    server_slug: str
    files: list[GeneratedFile]
    valid: bool
    validation_messages: list[str] = Field(default_factory=list)


class TestToolRequest(BaseModel):
    base_url: str
    auth: AuthConfig
    credential: str = ""  # api key / bearer token / "user:pass"
    tool: ProposedTool
    args: dict[str, Any] = Field(default_factory=dict)


class TestToolResult(BaseModel):
    request_method: str
    request_url: str
    request_headers: dict[str, str]
    request_body: Optional[Any] = None
    status_code: Optional[int] = None
    response_headers: dict[str, str] = Field(default_factory=dict)
    response_body: Any = None
    normalized: dict[str, Any]
    latency_ms: int
    error: Optional[str] = None


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
