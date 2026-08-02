"""Turn an installed Python library into a proposed tool set.

This is the second input mode. Where OpenAPI covers "software with a REST API"
(GitHub, Stripe), this covers "software with a Python API" — the Playwright /
Blender-addon shape, where the integration is a library call, not an HTTP call.

SECURITY: introspection imports the target module, which executes its top-level
code. On a shared deployment that is remote code execution, so the caller must
have set ENABLE_SDK_INTROSPECTION, and SDK_ALLOWED_MODULES can narrow it to
specific packages. See ``ensure_allowed``.
"""
from __future__ import annotations

import importlib
import inspect
import re
from typing import Any, Optional

from ..config import get_settings
from ..models import AuthConfig, ParseResult, ProposedTool, ToolParam


class SdkIntrospectError(RuntimeError):
    pass


# Mutating verbs get the confirm gate, mirroring how write HTTP verbs are treated.
_WRITE_HINTS = (
    "delete", "remove", "destroy", "drop", "create", "write", "save", "update",
    "set_", "add", "insert", "send", "post", "put", "patch", "execute", "run",
    "install", "uninstall", "kill", "stop", "start", "move", "rename", "clear",
)

_ANNOTATION_TO_JSON = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
    list: "array",
    dict: "object",
}


def ensure_allowed(module_name: str) -> None:
    """Gate introspection behind explicit configuration."""
    settings = get_settings()
    if not settings.enable_sdk_introspection:
        raise SdkIntrospectError(
            "SDK introspection is disabled. Importing a module runs its code, so "
            "this is opt-in: set ENABLE_SDK_INTROSPECTION=true to allow it."
        )
    root = module_name.split(".")[0]
    allowed = settings.sdk_allowed_modules
    if allowed and root not in allowed and module_name not in allowed:
        raise SdkIntrospectError(
            f"Module '{module_name}' is not in SDK_ALLOWED_MODULES "
            f"({', '.join(allowed)})."
        )


def introspect(module_name: str, include_private: bool = False) -> ParseResult:
    """Import ``module_name`` and propose one tool per public function."""
    ensure_allowed(module_name)

    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)*", module_name):
        raise SdkIntrospectError(f"'{module_name}' is not a valid module path")

    try:
        module = importlib.import_module(module_name)
    except ImportError as exc:
        raise SdkIntrospectError(f"Could not import '{module_name}': {exc}")
    except Exception as exc:  # module-level code blew up
        raise SdkIntrospectError(f"Importing '{module_name}' raised {type(exc).__name__}: {exc}")

    tools: list[ProposedTool] = []
    seen: set[str] = set()

    for name, obj in inspect.getmembers(module):
        if name.startswith("_") and not include_private:
            continue
        if not (inspect.isfunction(obj) or inspect.isbuiltin(obj)):
            continue
        # Skip re-exports from other packages: tool sets should reflect this module.
        origin = getattr(obj, "__module__", "") or ""
        if origin and not origin.startswith(module_name.split(".")[0]):
            continue
        tool = _function_to_tool(name, obj, seen)
        if tool:
            tools.append(tool)

    if not tools:
        raise SdkIntrospectError(
            f"No public functions found in '{module_name}'. "
            "Try a submodule that exposes functions directly."
        )

    return ParseResult(
        api_title=module_name,
        api_version=str(getattr(module, "__version__", "") or ""),
        base_url="",  # not an HTTP integration
        server_slug=_slug(module_name),
        auth=AuthConfig(type="none"),
        tools=tools,
        kind="python_sdk",
        sdk_module=module_name,
    )


def _function_to_tool(name: str, fn: Any, seen: set[str]) -> Optional[ProposedTool]:
    try:
        sig = inspect.signature(fn)
    except (ValueError, TypeError):
        # Builtins often have no introspectable signature; skip rather than guess.
        return None

    params: list[ToolParam] = []
    for pname, p in sig.parameters.items():
        if p.kind in (p.VAR_POSITIONAL, p.VAR_KEYWORD):
            # *args/**kwargs can't be expressed in a JSON schema; skip them.
            continue
        params.append(
            ToolParam(
                name=pname,
                type=_json_type(p.annotation),
                description="",
                required=p.default is inspect.Parameter.empty,
                location="python_arg",
            )
        )

    doc = inspect.getdoc(fn) or ""
    description = re.sub(r"\s+", " ", doc.split("\n\n")[0]).strip()[:300] or f"Call {name}()"

    tool_name = _unique(_snake(name), seen)
    return ProposedTool(
        name=tool_name,
        description=description,
        method="CALL",
        path=name,  # the attribute to call on the module
        params=params,
        confirm_required=any(h in name.lower() for h in _WRITE_HINTS),
    )


def _json_type(annotation: Any) -> str:
    if annotation is inspect.Parameter.empty:
        return "string"
    if annotation in _ANNOTATION_TO_JSON:
        return _ANNOTATION_TO_JSON[annotation]
    # Handle typing constructs like Optional[int] / list[str] by their origin.
    origin = getattr(annotation, "__origin__", None)
    if origin in _ANNOTATION_TO_JSON:
        return _ANNOTATION_TO_JSON[origin]
    args = [a for a in getattr(annotation, "__args__", ()) if a is not type(None)]
    if len(args) == 1 and args[0] in _ANNOTATION_TO_JSON:
        return _ANNOTATION_TO_JSON[args[0]]
    return "string"


def _snake(text: str) -> str:
    text = re.sub(r"[^0-9a-zA-Z]+", "_", text)
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", text)
    return re.sub(r"_+", "_", text).strip("_").lower()


def _unique(base: str, seen: set[str]) -> str:
    name, i = base or "call", 2
    while name in seen:
        name = f"{base}_{i}"
        i += 1
    seen.add(name)
    return name


def _slug(module_name: str) -> str:
    return f"{_snake(module_name)}_mcp"
