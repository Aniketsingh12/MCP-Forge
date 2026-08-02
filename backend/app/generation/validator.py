"""Validate generated files before they ever reach the user.

The gate is intentionally conservative: it parses every generated ``.py`` file
and confirms the server module has the structural markers we expect (a FastMCP
instance and at least one ``@mcp.tool()``). Syntax errors here mean a template
bug, and we want to catch that, not the user.
"""
from __future__ import annotations

import ast

from ..models import GeneratedFile


def validate(files: list[GeneratedFile]) -> tuple[bool, list[str]]:
    messages: list[str] = []
    ok = True

    server = next((f for f in files if f.path == "server.py"), None)
    if server is None:
        return False, ["server.py was not generated"]

    for f in files:
        if not f.path.endswith(".py"):
            continue
        try:
            # compile(), not ast.parse(): parsing alone accepts things the
            # compiler rejects (e.g. `def f(a, a)`), which would ship a package
            # that explodes on import while we reported it valid.
            compile(f.content, f.path, "exec")
        except SyntaxError as e:
            ok = False
            messages.append(f"{f.path}: syntax error at line {e.lineno}: {e.msg}")
        except ValueError as e:
            ok = False
            messages.append(f"{f.path}: invalid source: {e}")

    if ok:
        tree = ast.parse(server.content)
        tool_names = _tool_names(tree)
        if not tool_names:
            ok = False
            messages.append("server.py declares no @mcp.tool() functions")
        else:
            messages.append(f"server.py parsed cleanly with {len(tool_names)} tool(s)")
        # Two tools sharing a name would silently shadow each other at import.
        dupes = {n for n in tool_names if tool_names.count(n) > 1}
        if dupes:
            ok = False
            messages.append(
                "duplicate tool name(s): " + ", ".join(sorted(dupes))
            )
        if "FastMCP(" not in server.content:
            ok = False
            messages.append("server.py is missing a FastMCP instance")

    if ok and not messages:
        messages.append("All files valid.")
    return ok, messages


def _tool_names(tree: ast.Module) -> list[str]:
    """Names of every function decorated with @mcp.tool() / @mcp.tool."""
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            for dec in node.decorator_list:
                # match @mcp.tool() and @mcp.tool
                target = dec.func if isinstance(dec, ast.Call) else dec
                if (
                    isinstance(target, ast.Attribute)
                    and target.attr == "tool"
                    and isinstance(target.value, ast.Name)
                    and target.value.id == "mcp"
                ):
                    names.append(node.name)
    return names
