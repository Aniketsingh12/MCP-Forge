"""Optional LLM pass that polishes tool descriptions.

Descriptions are what an agent reads to decide when to call a tool, so clarity
matters. When enabled, we ask the model to rewrite terse spec summaries into
crisp, agent-facing descriptions — but we only ever *replace text*, never the
names, methods, paths, or params the deterministic parser produced. The spec
stays the source of truth for behaviour; the LLM only improves prose.
"""
from __future__ import annotations

from .. import llm
from ..models import ParseResult

_SYSTEM = (
    "You write tool descriptions for AI agents. Given a list of API operations, "
    "rewrite each description to be a single clear sentence an agent can use to "
    "decide when to call the tool. Be concrete about what it does. Do not invent "
    "capabilities. Return JSON only."
)


def polish_descriptions(result: ParseResult) -> ParseResult:
    """Return a copy of ``result`` with LLM-improved descriptions where possible.

    Failures are swallowed — the deterministic descriptions are always a valid
    fallback, so a flaky model never blocks generation.
    """
    if not llm.is_enabled() or not result.tools:
        return result

    items = [
        {"name": t.name, "method": t.method, "path": t.path, "current": t.description}
        for t in result.tools
    ]
    user = (
        f"API: {result.api_title}\n\n"
        "Rewrite the 'current' description for each operation. Respond with JSON "
        'of the form {"tools": [{"name": "...", "description": "..."}]}.\n\n'
        f"Operations:\n{items}"
    )
    try:
        data = llm.complete_json(_SYSTEM, user)
    except llm.LLMError:
        return result
    if not isinstance(data, dict):
        return result

    by_name = {t.get("name"): t.get("description") for t in data.get("tools", []) if isinstance(t, dict)}
    updated = result.model_copy(deep=True)
    for tool in updated.tools:
        new_desc = by_name.get(tool.name)
        if isinstance(new_desc, str) and new_desc.strip():
            tool.description = new_desc.strip()[:300]
    updated.llm_used = True
    return updated
