"""Deterministic OpenAPI (3.x / Swagger 2.0) -> tool proposal mapping.

This is the MVP's quality bedrock: no LLM guessing, just a faithful walk of the
spec. Each operation becomes one proposed tool; parameters map straight to a
JSON-schema-backed param list; the security scheme becomes the auth config.
"""
from __future__ import annotations

import json
import re
from typing import Any, Optional

import yaml

from ..models import AuthConfig, ParseResult, ProposedTool, ToolParam

_HTTP_METHODS = ["get", "put", "post", "delete", "patch", "head", "options"]


class SpecParseError(ValueError):
    pass


def parse_spec(spec_text: str) -> ParseResult:
    spec = _load(spec_text)
    if not isinstance(spec, dict):
        raise SpecParseError("Spec did not parse to an object")

    is_swagger2 = str(spec.get("swagger", "")).startswith("2")
    info = spec.get("info", {}) or {}
    title = info.get("title", "API")
    version = info.get("version", "")

    base_url = _base_url(spec, is_swagger2)
    auth = _auth(spec, is_swagger2)

    tools: list[ProposedTool] = []
    seen: set[str] = set()
    for path, path_item in (spec.get("paths", {}) or {}).items():
        if not isinstance(path_item, dict):
            continue
        shared_params = path_item.get("parameters", []) or []
        for method in _HTTP_METHODS:
            op = path_item.get(method)
            if not isinstance(op, dict):
                continue
            tool = _operation_to_tool(
                spec, method, path, op, shared_params, is_swagger2, seen
            )
            tools.append(tool)

    if not tools:
        raise SpecParseError("No operations found in spec paths")

    return ParseResult(
        api_title=title,
        api_version=str(version),
        base_url=base_url,
        server_slug=_slug(title),
        auth=auth,
        tools=tools,
    )


# --------------------------------------------------------------------------- #
def _load(spec_text: str) -> Any:
    spec_text = (spec_text or "").strip()
    if not spec_text:
        raise SpecParseError("Empty spec")
    try:
        return json.loads(spec_text)
    except json.JSONDecodeError:
        pass
    try:
        return yaml.safe_load(spec_text)
    except yaml.YAMLError as e:
        raise SpecParseError(f"Not valid JSON or YAML: {e}")


def _base_url(spec: dict, is_swagger2: bool) -> str:
    if is_swagger2:
        schemes = spec.get("schemes") or ["https"]
        host = spec.get("host", "")
        base_path = spec.get("basePath", "")
        if host:
            return f"{schemes[0]}://{host}{base_path}".rstrip("/")
        return ""
    servers = spec.get("servers") or []
    if servers and isinstance(servers[0], dict):
        url = servers[0].get("url", "")
        # Substitute server variable defaults, e.g. {environment}.
        for name, var in (servers[0].get("variables", {}) or {}).items():
            default = var.get("default", "")
            url = url.replace("{" + name + "}", str(default))
        return url.rstrip("/")
    return ""


def _auth(spec: dict, is_swagger2: bool) -> AuthConfig:
    if is_swagger2:
        schemes = spec.get("securityDefinitions", {}) or {}
    else:
        schemes = (spec.get("components", {}) or {}).get("securitySchemes", {}) or {}

    for scheme in schemes.values():
        if not isinstance(scheme, dict):
            continue
        stype = (scheme.get("type") or "").lower()
        if stype == "http":
            sub = (scheme.get("scheme") or "").lower()
            if sub == "bearer":
                return AuthConfig(type="bearer", location="header",
                                  param_name="Authorization", value_prefix="Bearer ")
            if sub == "basic":
                return AuthConfig(type="basic", location="header",
                                  param_name="Authorization")
        if stype == "apikey":
            loc = (scheme.get("in") or "header").lower()
            name = scheme.get("name") or "Authorization"
            return AuthConfig(
                type="api_key",
                location="query" if loc == "query" else "header",
                param_name=name,
            )
        if stype == "oauth2":
            # OAuth is out of MVP scope; treat the access token as a bearer key.
            return AuthConfig(type="bearer", location="header",
                              param_name="Authorization", value_prefix="Bearer ")
    # Default: API key in an Authorization header.
    return AuthConfig(type="api_key", location="header", param_name="Authorization")


def _operation_to_tool(
    spec: dict,
    method: str,
    path: str,
    op: dict,
    shared_params: list,
    is_swagger2: bool,
    seen: set[str],
) -> ProposedTool:
    op_id = op.get("operationId")
    name = _tool_name(op_id, method, path, seen)

    description = (op.get("summary") or op.get("description") or "").strip()
    description = re.sub(r"\s+", " ", description)[:300]
    if not description:
        description = f"{method.upper()} {path}"

    params: list[ToolParam] = []
    all_params = list(shared_params) + list(op.get("parameters", []) or [])
    for p in all_params:
        p = _resolve_ref(spec, p)
        if not isinstance(p, dict) or "name" not in p:
            continue
        loc = (p.get("in") or "query").lower()
        if loc not in {"query", "path", "header"}:
            continue
        if is_swagger2:
            ptype = p.get("type", "string")
        else:
            ptype = (p.get("schema", {}) or {}).get("type", "string")
        params.append(
            ToolParam(
                name=p["name"],
                type=ptype or "string",
                description=re.sub(r"\s+", " ", (p.get("description") or "")).strip()[:200],
                required=bool(p.get("required", loc == "path")),
                location="path" if loc == "path" else ("header" if loc == "header" else "query"),
            )
        )

    # Request body (OpenAPI 3) -> a single "body" object param.
    body_schema = _request_body_schema(spec, op, is_swagger2)
    if body_schema is not None:
        params.append(
            ToolParam(
                name="body",
                type="object",
                description="JSON request body",
                required=True,
                location="body",
                json_schema=body_schema,
            )
        )

    return ProposedTool(
        name=name,
        description=description,
        method=method.upper(),
        path=path,
        params=params,
        confirm_required=method.upper() in {"POST", "PUT", "PATCH", "DELETE"},
    )


def _request_body_schema(spec: dict, op: dict, is_swagger2: bool) -> Optional[dict]:
    if is_swagger2:
        for p in op.get("parameters", []) or []:
            p = _resolve_ref(spec, p)
            if isinstance(p, dict) and p.get("in") == "body":
                return _resolve_ref(spec, p.get("schema", {})) or {"type": "object"}
        return None
    rb = op.get("requestBody")
    if not isinstance(rb, dict):
        return None
    rb = _resolve_ref(spec, rb)
    content = rb.get("content", {}) or {}
    for ctype in ("application/json", "application/*+json"):
        if ctype in content:
            schema = content[ctype].get("schema", {})
            return _resolve_ref(spec, schema) or {"type": "object"}
    # Any content type with a schema.
    for c in content.values():
        if isinstance(c, dict) and "schema" in c:
            return _resolve_ref(spec, c["schema"]) or {"type": "object"}
    return {"type": "object"}


def _resolve_ref(spec: dict, node: Any, _depth: int = 0) -> Any:
    """Follow a single local ``$ref`` (bounded depth to avoid cycles)."""
    if _depth > 8 or not isinstance(node, dict):
        return node
    ref = node.get("$ref")
    if not ref or not isinstance(ref, str) or not ref.startswith("#/"):
        return node
    target: Any = spec
    for part in ref[2:].split("/"):
        part = part.replace("~1", "/").replace("~0", "~")
        if isinstance(target, dict) and part in target:
            target = target[part]
        else:
            return node
    return _resolve_ref(spec, target, _depth + 1)


# --------------------------------------------------------------------------- #
def _tool_name(op_id: Optional[str], method: str, path: str, seen: set[str]) -> str:
    if op_id:
        base = _snake(op_id)
    else:
        # Build a readable name from method + path segments.
        segs = [s for s in path.split("/") if s and not s.startswith("{")]
        base = _snake(f"{method}_{'_'.join(segs) or 'root'}")
    base = base or f"{method}_op"
    name = base
    i = 2
    while name in seen:
        name = f"{base}_{i}"
        i += 1
    seen.add(name)
    return name


def _snake(text: str) -> str:
    text = re.sub(r"[^0-9a-zA-Z]+", "_", text)
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", text)
    return re.sub(r"_+", "_", text).strip("_").lower()


def _slug(title: str) -> str:
    slug = _snake(title) or "api"
    return f"{slug}_mcp"
