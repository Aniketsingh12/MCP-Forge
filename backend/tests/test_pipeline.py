"""End-to-end pipeline check: spec -> proposal -> codegen -> validate.

Run directly (``python tests/test_pipeline.py``) or under pytest.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.generation.openapi_parser import parse_spec  # noqa: E402
from app.generation import codegen, validator  # noqa: E402
from app.models import GenerateRequest  # noqa: E402

SPEC = (Path(__file__).parent / "sample_petstore.json").read_text()


def build():
    parsed = parse_spec(SPEC)
    req = GenerateRequest(
        server_slug=parsed.server_slug,
        api_title=parsed.api_title,
        base_url=parsed.base_url,
        auth=parsed.auth,
        tools=parsed.tools,
    )
    files = codegen.generate(req)
    ok, messages = validator.validate(files)
    return parsed, files, ok, messages


def test_parse_produces_four_tools():
    parsed = parse_spec(SPEC)
    names = {t.name for t in parsed.tools}
    assert names == {"list_pets", "create_pet", "get_pet_by_id", "delete_pet"}
    assert parsed.base_url == "https://petstore.example.com/v1"
    assert parsed.auth.type == "api_key"
    assert parsed.auth.param_name == "X-API-Key"


def test_write_tools_marked_confirm():
    parsed = parse_spec(SPEC)
    by_name = {t.name: t for t in parsed.tools}
    assert by_name["create_pet"].confirm_required is True
    assert by_name["delete_pet"].confirm_required is True
    assert by_name["list_pets"].confirm_required is False


def test_codegen_validates():
    _, files, ok, messages = build()
    assert ok, messages
    server = next(f for f in files if f.path == "server.py")
    assert "def list_pets(" in server.content
    assert "def create_pet(" in server.content
    assert "confirm: bool = False" in server.content  # write action gate


def _gen(spec_dict):
    import json

    parsed = parse_spec(json.dumps(spec_dict))
    files = codegen.generate(
        GenerateRequest(
            server_slug=parsed.server_slug,
            api_title=parsed.api_title,
            base_url=parsed.base_url,
            auth=parsed.auth,
            tools=parsed.tools,
        )
    )
    return parsed, files


def test_duplicate_params_do_not_break_generated_code():
    """A param declared at both path-item and operation level is legal OpenAPI.

    Emitting it twice produced `def f(x, x)` — which ast.parse accepts but the
    interpreter rejects, shipping a package that died on import.
    """
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Dup", "version": "1"},
        "servers": [{"url": "https://api.example.com"}],
        "paths": {
            "/items/{itemId}": {
                "parameters": [
                    {"name": "itemId", "in": "path", "required": True,
                     "schema": {"type": "string"}}
                ],
                "get": {
                    "operationId": "getItem",
                    "summary": "Get",
                    "parameters": [
                        {"name": "itemId", "in": "path", "required": True,
                         "schema": {"type": "string"}}
                    ],
                },
            }
        },
    }
    _, files = _gen(spec)
    server = next(f for f in files if f.path == "server.py")
    compile(server.content, "server.py", "exec")  # must not raise
    assert server.content.count("itemId: str") == 1
    ok, msgs = validator.validate(files)
    assert ok, msgs


import ast

import pytest


@pytest.mark.parametrize(
    "field,payload",
    [
        # Header name: breaks out of headers["..."] into a statement.
        ("param_name", "X\"] = __import__('os').popen('whoami').read(); headers[\"Y"),
        # Header name: closes the module docstring, then runs code.
        ("param_name", '"""\nimport os; os.system("whoami")\n"""'),
        # Base URL: breaks out of the default-value string literal.
        ("base_url", "https://a.com\") or __import__('os').system('whoami') #"),
    ],
)
def test_hostile_input_cannot_inject_executable_code(field, payload):
    """Spec/user-supplied text lands in generated source and must stay inert.

    Users download and run this code, so a crafted spec turning into executable
    statements would be a supply-chain hole, not just a rendering bug.
    """
    from app.models import AuthConfig, ProposedTool

    kwargs = dict(
        server_slug="x",
        api_title="X",
        base_url="https://api.example.com",
        auth=AuthConfig(type="api_key", location="header", param_name="K"),
        tools=[ProposedTool(name="ping", description="p", method="GET",
                            path="/p", params=[])],
    )
    if field == "param_name":
        kwargs["auth"] = AuthConfig(type="api_key", location="header",
                                    param_name=payload)
    else:
        kwargs["base_url"] = payload

    server = next(
        f for f in codegen.generate(GenerateRequest(**kwargs)) if f.path == "server.py"
    )
    tree = ast.parse(compile(server.content, "server.py", "exec", ast.PyCF_ONLY_AST))

    # The payload may appear only as an inert string constant — never as a call.
    assert not [
        n for n in ast.walk(tree)
        if isinstance(n, ast.Call)
        and isinstance(n.func, ast.Name)
        and n.func.id == "__import__"
    ], "payload became an executable __import__ call"
    assert any(
        isinstance(n, ast.Constant) and isinstance(n.value, str) and payload in n.value
        for n in ast.walk(tree)
    ), "payload should survive as an inert string constant"


def test_validator_rejects_duplicate_arguments():
    from app.models import GeneratedFile

    bad = GeneratedFile(
        path="server.py",
        content=(
            'from mcp.server.fastmcp import FastMCP\nmcp = FastMCP("x")\n'
            "@mcp.tool()\ndef f(a: str, a: str) -> dict:\n    return {}\n"
        ),
    )
    ok, msgs = validator.validate([bad])
    assert not ok and any("duplicate argument" in m for m in msgs)


def test_path_params_are_url_encoded():
    """An unencoded path value could inject extra segments or a query string."""
    _, files = _gen(
        {
            "openapi": "3.0.0",
            "info": {"title": "Enc", "version": "1"},
            "servers": [{"url": "https://api.example.com"}],
            "paths": {
                "/u/{id}": {
                    "get": {
                        "operationId": "getU",
                        "parameters": [
                            {"name": "id", "in": "path", "required": True,
                             "schema": {"type": "string"}}
                        ],
                    }
                }
            },
        }
    )
    server = next(f for f in files if f.path == "server.py")
    assert "quote(str(value), safe=" in server.content


def test_polling_tool_emits_submit_and_poll():
    """A long-running job becomes one blocking tool, not two unrelated ones."""
    from app.models import AuthConfig, PollingConfig, ProposedTool, ToolParam

    tool = ProposedTool(
        name="generate_image", description="Generate", method="POST", path="/jobs",
        params=[ToolParam(name="body", type="object", required=True, location="body")],
        polling=PollingConfig(
            enabled=True, id_field="id", status_path="/jobs/{job_id}",
            status_field="status", interval_seconds=0.5, max_attempts=5,
        ),
    )
    files = codegen.generate(
        GenerateRequest(server_slug="img", api_title="Img",
                        base_url="https://api.example.com",
                        auth=AuthConfig(type="none"), tools=[tool])
    )
    server = next(f for f in files if f.path == "server.py")
    compile(server.content, "server.py", "exec")
    assert "_submit_and_poll(" in server.content
    assert "status_path='/jobs/{job_id}'" in server.content
    ok, msgs = validator.validate(files)
    assert ok, msgs


def test_polling_off_by_default_emits_plain_request():
    _, files = _gen(
        {
            "openapi": "3.0.0",
            "info": {"title": "P", "version": "1"},
            "servers": [{"url": "https://api.example.com"}],
            "paths": {"/things": {"get": {"operationId": "listThings"}}},
        }
    )
    server = next(f for f in files if f.path == "server.py")
    assert "_submit_and_poll(" not in server.content
    assert "return _request(" in server.content


# --------------------------------------------------------------------------- #
# SDK introspection mode
# --------------------------------------------------------------------------- #
def test_sdk_introspection_is_disabled_by_default(monkeypatch):
    """Importing a module runs its code, so this must never be on implicitly."""
    from app.config import get_settings
    from app.generation import sdk_introspect

    monkeypatch.delenv("ENABLE_SDK_INTROSPECTION", raising=False)
    get_settings.cache_clear()
    with pytest.raises(sdk_introspect.SdkIntrospectError, match="disabled"):
        sdk_introspect.introspect("base64")
    get_settings.cache_clear()


def test_sdk_allowlist_blocks_other_modules(monkeypatch):
    from app.config import get_settings
    from app.generation import sdk_introspect

    monkeypatch.setenv("ENABLE_SDK_INTROSPECTION", "true")
    monkeypatch.setenv("SDK_ALLOWED_MODULES", "base64")
    get_settings.cache_clear()
    try:
        with pytest.raises(sdk_introspect.SdkIntrospectError, match="not in SDK_ALLOWED"):
            sdk_introspect.introspect("subprocess")
    finally:
        get_settings.cache_clear()


def test_sdk_generation_produces_valid_in_process_server(monkeypatch):
    from app.config import get_settings
    from app.generation import sdk_introspect

    monkeypatch.setenv("ENABLE_SDK_INTROSPECTION", "true")
    monkeypatch.delenv("SDK_ALLOWED_MODULES", raising=False)
    get_settings.cache_clear()
    try:
        parsed = sdk_introspect.introspect("base64")
        assert parsed.kind == "python_sdk" and parsed.sdk_module == "base64"
        files = codegen.generate(
            GenerateRequest(
                server_slug=parsed.server_slug, api_title=parsed.api_title,
                base_url="", auth=parsed.auth, tools=parsed.tools,
                kind=parsed.kind, sdk_module=parsed.sdk_module,
            )
        )
        server = next(f for f in files if f.path == "server.py")
        compile(server.content, "server.py", "exec")
        assert "import base64 as _sdk" in server.content
        assert "httpx" not in server.content  # no HTTP layer in an SDK server
        # stdlib modules must not be emitted as pip requirements
        reqs = next(f for f in files if f.path == "requirements.txt").content
        assert "base64" not in reqs
        ok, msgs = validator.validate(files)
        assert ok, msgs
    finally:
        get_settings.cache_clear()


def test_sdk_module_path_cannot_inject_import_statement():
    """sdk_module lands in real `import` syntax and can't be repr()-escaped."""
    from app.models import AuthConfig, ProposedTool

    with pytest.raises(ValueError, match="Unsafe or invalid module path"):
        codegen.generate(
            GenerateRequest(
                server_slug="x", api_title="X", base_url="",
                auth=AuthConfig(type="none"),
                tools=[ProposedTool(name="t", method="CALL", path="f")],
                kind="python_sdk",
                sdk_module="os, sys; __import__('os').system('whoami')",
            )
        )


if __name__ == "__main__":
    parsed, files, ok, messages = build()
    print(f"Parsed API: {parsed.api_title}  base={parsed.base_url}")
    print(f"Auth: {parsed.auth.type} ({parsed.auth.param_name})")
    print(f"Tools ({len(parsed.tools)}): {[t.name for t in parsed.tools]}")
    print(f"\nValidation ok={ok}")
    for m in messages:
        print("  -", m)
    print("\nFiles generated:")
    for f in files:
        print(f"  - {f.path} ({len(f.content)} bytes)")
    print("\n===== server.py =====\n")
    print(next(f for f in files if f.path == "server.py").content)
