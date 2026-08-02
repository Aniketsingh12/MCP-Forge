"""Template-driven code generation.

Auth, transport, and error handling come from audited Jinja templates. The only
per-tool logic is a mechanical translation of each operation's parameters into a
typed Python function — deterministic, so there is nothing for a model to get
wrong. (The optional LLM pass only touches human-readable descriptions.)
"""
from __future__ import annotations

import json
import keyword
import re
import sys
import textwrap
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from ..models import AuthConfig, GeneratedFile, GenerateRequest, ProposedTool, ToolParam

_TEMPLATE_DIR = Path(__file__).parent / "templates"
_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATE_DIR)),
    undefined=StrictUndefined,
    keep_trailing_newline=True,
)

_JSON_TO_PY = {
    "string": "str",
    "integer": "int",
    "number": "float",
    "boolean": "bool",
    "array": "list",
    "object": "dict",
}


def generate(req: GenerateRequest) -> list[GeneratedFile]:
    tools = [t for t in req.tools if t.enabled]
    server_slug = _safe_slug(req.server_slug)
    is_sdk = req.kind == "python_sdk"

    tool_functions = "\n\n".join(
        (_render_sdk_tool(t) if is_sdk else _render_tool(t)) for t in tools
    )
    auth_block = _auth_block(req.auth)
    credential_hint = _credential_hint(req.auth)
    claude_config = _claude_config(server_slug)

    # server.py is Python source: anything spec- or user-supplied that lands
    # inside it must be emitted as a literal (or, for prose in the module
    # docstring, stripped of sequences that could close the docstring early).
    if is_sdk:
        sdk_module = _safe_module(req.sdk_module)
        server_py = _env.get_template("sdk_server.py.jinja").render(
            api_title=_doc_safe(req.api_title or sdk_module),
            sdk_module=sdk_module,
            sdk_root=sdk_module.split(".")[0],
            server_slug_literal=_lit(server_slug),
            tool_functions=tool_functions,
        )
    else:
        server_py = _env.get_template("server.py.jinja").render(
            api_title=_doc_safe(req.api_title or "API"),
            server_slug=server_slug,
            server_slug_literal=_lit(server_slug),
            base_url=req.base_url,
            base_url_literal=_lit(req.base_url),
            auth_block=auth_block,
            tool_functions=tool_functions,
            credential_hint=_doc_safe(credential_hint),
            # Don't ship polling helpers into packages that never poll.
            needs_polling=any(
                t.polling.enabled and t.polling.status_path for t in tools
            ),
        )

    ctx_common = dict(
        api_title=req.api_title or "API",
        server_slug=server_slug,
        base_url=req.base_url,
        credential_hint=credential_hint,
        # HTTP servers need an HTTP client; SDK servers need the wrapped library
        # — unless it ships with Python, in which case there's nothing to pin.
        extra_deps=(
            _sdk_deps(req.sdk_module) if is_sdk else ["httpx>=0.27"]
        ),
        kind=req.kind,
    )

    readme = _env.get_template("README.md.jinja").render(
        tools=tools,
        tool_count=len(tools),
        claude_config=claude_config,
        **ctx_common,
    )
    # The registered MCP tool name is the generated function name, so assert
    # against that (and emit it as a literal, not raw interpolated text).
    test_py = _env.get_template("test_server.py.jinja").render(
        tool_name_literals=[_lit(_safe_ident(t.name)) for t in tools], **ctx_common
    )

    files = [
        GeneratedFile(path="server.py", content=server_py, language="python"),
        GeneratedFile(
            path="pyproject.toml",
            content=_env.get_template("pyproject.toml.jinja").render(**ctx_common),
            language="toml",
        ),
        GeneratedFile(
            path="requirements.txt",
            content=_env.get_template("requirements.txt.jinja").render(**ctx_common),
            language="text",
        ),
        GeneratedFile(
            path=".env.example",
            content=_env.get_template("env.example.jinja").render(**ctx_common),
            language="bash",
        ),
        GeneratedFile(
            path=".gitignore",
            content=_env.get_template("gitignore.jinja").render(**ctx_common),
            language="text",
        ),
        GeneratedFile(path="README.md", content=readme, language="markdown"),
        GeneratedFile(path="tests/test_server.py", content=test_py, language="python"),
        GeneratedFile(
            path="claude_desktop_config.json", content=claude_config, language="json"
        ),
    ]
    return files


# --------------------------------------------------------------------------- #
# Tool function rendering
# --------------------------------------------------------------------------- #
def _render_tool(tool: ProposedTool) -> str:
    fn_name = _safe_ident(tool.name)
    sig_parts = _signature(tool)

    if tool.confirm_required:
        sig_parts.append("confirm: bool = False")

    signature = ", ".join(sig_parts)
    doc = _docstring(tool)

    body_lines: list[str] = []

    if tool.confirm_required:
        warning = (
            f"This is a write action ({tool.method} {tool.path}). "
            "Re-call with confirm=True to proceed."
        )
        body_lines += [
            "if not confirm:",
            "    return {",
            '        "ok": False,',
            '        "status": None,',
            f"        \"error\": {_lit(warning)},",
            '        "data": None,',
            "    }",
        ]

    params = _unique_params(tool)
    path_params = [p for p in params if p.location == "path"]
    query_params = [p for p in params if p.location in ("query", "header")]
    body_param = next((p for p in params if p.location == "body"), None)

    body_lines.append(
        "path_params = {"
        + ", ".join(f"{_lit(p.name)}: {_safe_ident(p.name)}" for p in path_params)
        + "}"
    )
    body_lines.append(
        "query = {"
        + ", ".join(f"{_lit(p.name)}: {_safe_ident(p.name)}" for p in query_params)
        + "}"
    )

    body_arg = f"{_safe_ident(body_param.name)}" if body_param else "None"

    poll = tool.polling
    if poll.enabled and poll.status_path:
        # Submit-then-poll: one tool call blocks until the job resolves.
        body_lines += [
            f"return _submit_and_poll(",
            f"    {_lit(tool.method)}, {_lit(tool.path)},",
            f"    path_params, query, {body_arg},",
            f"    id_field={_lit(poll.id_field)},",
            f"    status_path={_lit(poll.status_path)},",
            f"    status_field={_lit(poll.status_field)},",
            f"    success_values={_lit_list(poll.success_values)},",
            f"    failure_values={_lit_list(poll.failure_values)},",
            f"    interval={float(poll.interval_seconds)!r},",
            f"    max_attempts={int(poll.max_attempts)!r},",
            f")",
        ]
    else:
        body_lines.append(
            f"return _request({_lit(tool.method)}, {_lit(tool.path)}, "
            f"path_params=path_params, query=query, body={body_arg})"
        )

    body = textwrap.indent("\n".join(body_lines), "    ")
    ret_type = " -> dict:"

    return (
        "@mcp.tool()\n"
        f"def {fn_name}({signature}){ret_type}\n"
        f'    """{doc}"""\n'
        f"{body}"
    )


def _render_sdk_tool(tool: ProposedTool) -> str:
    """Render a tool that calls a Python library function in-process."""
    fn_name = _safe_ident(tool.name)
    sig_parts = _signature(tool)
    if tool.confirm_required:
        sig_parts.append("confirm: bool = False")

    body_lines: list[str] = []
    if tool.confirm_required:
        warning = (
            f"This may modify state ({tool.path}). "
            "Re-call with confirm=True to proceed."
        )
        body_lines += [
            "if not confirm:",
            "    return {",
            '        "ok": False,',
            f"        \"error\": {_lit(warning)},",
            '        "error_type": "ConfirmationRequired",',
            "    }",
        ]

    kwargs = ", ".join(
        f"{_lit(p.name)}: {_safe_ident(p.name)}" for p in _unique_params(tool)
    )
    body_lines.append(f"return _call({_lit(tool.path)}, {{{kwargs}}})")

    return (
        "@mcp.tool()\n"
        f"def {fn_name}({', '.join(sig_parts)}) -> dict:\n"
        f'    """{_docstring(tool)}"""\n'
        + textwrap.indent("\n".join(body_lines), "    ")
    )


def _signature(tool: ProposedTool) -> list[str]:
    """Build ordered parameter parts. Required first, optional (with defaults) last."""
    required: list[str] = []
    optional: list[str] = []
    for p in _unique_params(tool):
        ident = _safe_ident(p.name)
        py_type = _JSON_TO_PY.get(p.type, "str")
        if p.location == "body":
            py_type = "dict"
        if p.required:
            required.append(f"{ident}: {py_type}")
        else:
            optional.append(f"{ident}: Optional[{py_type}] = None")
    return required + optional


def _docstring(tool: ProposedTool) -> str:
    desc = tool.description.replace('"""', "'''").strip() or f"{tool.method} {tool.path}"
    # Keep docstrings single-line to avoid indentation surprises in generated code.
    desc = re.sub(r"\s+", " ", desc)
    # A stray backslash would escape the closing triple quote and break the file.
    desc = desc.replace("\\", "\\\\")
    if tool.confirm_required:
        desc += " (write action - requires confirm=True)"
    if tool.polling.enabled and tool.polling.status_path:
        # The agent should know this call blocks and already returns the result.
        desc += " Submits the job and waits for it to finish, returning the final result."
    return desc


def _lit(value: str) -> str:
    """Render ``value`` as a safe Python string literal for generated source."""
    return repr(str(value))


def _lit_list(values: list[str]) -> str:
    """Render a list of strings as a safe Python list literal."""
    return "[" + ", ".join(_lit(v) for v in values) + "]"


def _doc_safe(text: str) -> str:
    """Make ``text`` safe to embed inside a triple-quoted docstring.

    A spec-supplied value containing ``\"\"\"`` would otherwise close the module
    docstring and let whatever follows execute as module-level code.
    """
    text = str(text).replace('"""', "'''").replace("\\", "/")
    # A lone `"` at the very end would still abut the closing delimiter.
    return text.rstrip('"')


def _unique_params(tool: ProposedTool) -> list[ToolParam]:
    """Drop params that would collide as Python identifiers.

    Specs legitimately repeat a parameter at both the path-item and operation
    level (OpenAPI says the operation wins), and distinct names like ``user-id``
    and ``user_id`` sanitize to the same identifier. Either case would emit
    ``def f(x, x)`` — which ``ast.parse`` accepts but ``compile`` rejects — so
    the first occurrence wins and the rest are dropped.
    """
    # `confirm` is only reserved when we actually inject the write-action gate;
    # otherwise a genuine `confirm` parameter must still come through.
    seen: set[str] = {"confirm"} if tool.confirm_required else set()
    unique: list[ToolParam] = []
    for p in tool.params:
        ident = _safe_ident(p.name)
        if ident in seen:
            continue
        seen.add(ident)
        unique.append(p)
    return unique


# --------------------------------------------------------------------------- #
# Auth
# --------------------------------------------------------------------------- #
def _auth_block(auth: AuthConfig) -> str:
    # Every value below originates from the spec or the user, so it is emitted
    # via repr() as a Python literal. Interpolating it raw would let a crafted
    # header name inject executable code into the server we hand the user.
    name = _lit(auth.param_name)
    if auth.type == "none":
        lines = ["    # No authentication configured.", "    pass"]
    elif auth.type == "basic":
        lines = [
            "    # Basic auth: API_CREDENTIAL should be 'username:password'.",
            "    if API_CREDENTIAL and ':' in API_CREDENTIAL:",
            '        user, _, pwd = API_CREDENTIAL.partition(":")',
            "        return (user, pwd)",
        ]
    elif auth.type == "bearer":
        prefix = _lit(auth.value_prefix or "Bearer ")
        lines = [
            "    if API_CREDENTIAL:",
            f"        headers[{name}] = {prefix} + API_CREDENTIAL",
        ]
    else:  # api_key
        if auth.location == "query":
            lines = [
                "    if API_CREDENTIAL:",
                f"        query[{name}] = API_CREDENTIAL",
            ]
        else:
            rhs = (
                f"{_lit(auth.value_prefix)} + API_CREDENTIAL"
                if auth.value_prefix
                else "API_CREDENTIAL"
            )
            lines = [
                "    if API_CREDENTIAL:",
                f"        headers[{name}] = {rhs}",
            ]
    return "\n".join(lines)


def _credential_hint(auth: AuthConfig) -> str:
    return {
        "none": "No credential required.",
        "api_key": f"API key, sent as the '{auth.param_name}' {auth.location}.",
        "bearer": "Bearer token (sent as 'Authorization: Bearer ...').",
        "basic": "Basic auth as 'username:password'.",
    }.get(auth.type, "API credential.")


def _claude_config(server_slug: str) -> str:
    config = {
        "mcpServers": {
            server_slug: {
                "command": "python",
                "args": ["/absolute/path/to/server.py"],
                "env": {"API_CREDENTIAL": "your-credential-here"},
            }
        }
    }
    return json.dumps(config, indent=2)


# --------------------------------------------------------------------------- #
def _safe_ident(name: str) -> str:
    ident = re.sub(r"[^0-9a-zA-Z_]", "_", name)
    if not ident or ident[0].isdigit():
        ident = "p_" + ident
    if keyword.iskeyword(ident):
        ident += "_"
    return ident


def _safe_slug(slug: str) -> str:
    slug = re.sub(r"[^0-9a-zA-Z_]", "_", slug).strip("_").lower()
    return slug or "generated_mcp"


def _sdk_deps(module_name: str) -> list[str]:
    """Third-party root package for the wrapped library, if it needs installing."""
    root = _safe_module(module_name).split(".")[0]
    if root in getattr(sys, "stdlib_module_names", frozenset()):
        return []
    return [root]


def _safe_module(name: str) -> str:
    """Validate a dotted module path before it becomes an `import` statement.

    This one can't be escaped with repr() — it lands in real import syntax — so
    anything that isn't a plain dotted identifier is rejected outright.
    """
    name = (name or "").strip()
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)*", name):
        raise ValueError(f"Unsafe or invalid module path: {name!r}")
    return name
