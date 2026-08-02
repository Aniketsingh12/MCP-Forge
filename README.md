# MCP Server builder

**MCP servers without the expertise.** Paste an OpenAPI spec → review the
proposed tools → generate a full MCP server from audited templates → test each
tool live against the real API → download a pip-installable package.

Generation is **deterministic** (no model required) and **open-source-model
friendly** (optional description polishing via Ollama or any OpenAI-compatible
endpoint). Ships as a **single deployable container**.

```
OpenAPI spec  →  Tool proposal  →  Generate  →  Playground  →  Download
 (JSON/YAML)     (edit / gate)     (templates)   (live calls)   (.zip package)
```

---

## Quick start

### Option A — one command, no Docker (recommended)

```bash
powershell -ExecutionPolicy Bypass -File run.ps1     # Windows
./run.sh                                             # macOS/Linux
```

Builds the frontend, bundles it into the backend, and serves everything from
FastAPI. Requires Python 3.10+ and Node 18+ on `PATH` — the script creates its
own venv and installs everything else. Open **http://localhost:8000**.

### Option B — Docker

```bash
docker compose up --build
```

Open **http://localhost:8000**. Same single-container result as above; useful
once you're ready to deploy the same image you tested locally.

### Option C — local dev with hot reload (two terminals)

```bash
# 1) Backend
cd backend
python -m venv .venv && . .venv/Scripts/activate    # Windows
#                       source .venv/bin/activate    # macOS/Linux
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

```bash
# 2) Frontend (proxies /api to :8000)
cd frontend
npm install
npm run dev            # http://localhost:5173
```

---

## Workflow: spec → running MCP server

1. **New project** — Dashboard → **+ New server**, name it.
2. **Input** — paste an OpenAPI 3 / Swagger 2 spec (JSON or YAML) or point at a
   hosted spec URL. No spec handy? Click **Load sample (Petstore)**. Click
   **Parse spec →**.
3. **Tool proposal (the quality gate)** — every operation becomes a candidate
   tool. Uncheck what you don't want, rename tools, edit descriptions (this is
   what an agent reads to decide when to call a tool), and toggle
   **confirm-required** (on by default for `POST/PUT/PATCH/DELETE`). Confirm
   the base URL and auth type. Click **Generate server →**.
4. **Generate** — template-driven codegen runs (no model involved); browse the
   file tree and check the ✓ **validated** badge.
5. **Playground** — pick a tool, fill the auto-generated param form, enter your
   real credential (session-only, never persisted), **▶ Run tool** against the
   live API. Iterate: edit a tool in step 3, regenerate, retest.
6. **Export** — **Download .zip**, or copy the **Claude Desktop config**
   snippet shown on this page.
7. **Run it for real:**
   ```bash
   cd <server_slug>
   pip install -r requirements.txt
   export API_CREDENTIAL="your-real-key"
   python server.py            # stdio transport, for MCP clients
   ```
   Or point Claude Desktop's `claude_desktop_config.json` at the extracted
   `server.py` using the exported snippet.

---

## Open-source (and other) models

The whole OpenAPI → server pipeline is deterministic, so **no model is needed**.
A model is only used — when you opt in on the input screen — to rewrite terse
spec summaries into clearer, agent-facing tool descriptions. It never writes
code, names, or params.

Configure via environment variables (see [`.env.example`](.env.example)):

| Provider | `LLM_PROVIDER` | `LLM_BASE_URL` | `LLM_MODEL` |
|----------|----------------|----------------|-------------|
| Local, open-source | `ollama` | `http://localhost:11434/v1` | `llama3.1`, `qwen2.5` |
| OpenRouter / Together / Groq / vLLM / LM Studio | `openai-compatible` | e.g. `https://openrouter.ai/api/v1` | any model id |
| Anthropic | `anthropic` | `https://api.anthropic.com/v1` | `claude-opus-4-8` |
| Disabled (default) | `none` | — | — |

**Local models with Docker:** uncomment the `ollama` service in
[`docker-compose.yml`](docker-compose.yml), then:

```bash
docker compose up --build -d
docker compose exec ollama ollama pull llama3.1
# .env: LLM_PROVIDER=openai-compatible  LLM_BASE_URL=http://ollama:11434/v1  LLM_MODEL=llama3.1
```

---

## Deploy

Because it's one container that listens on `$PORT`, it drops onto most hosts:

- **Railway / Render / Fly.io:** point at the repo (or the `Dockerfile`). No
  build config needed; `$PORT` is injected automatically. Add a persistent
  volume mounted at `/data` to keep projects across restarts.
- **Any Docker host:**
  ```bash
  docker build -t mcp-forge .
  docker run -p 8000:8000 -v mcpforge_data:/data mcp-forge
  ```
- **Split deploy (Vercel + Railway), per the original spec:** build
  `frontend/` on Vercel and set `VITE_API_TARGET`/a proxy to a separately
  hosted backend. The single-container path above is simpler and recommended.

---

## What's generated

For each spec you get a complete, runnable package:

```
<server_slug>/
├── server.py                    # FastMCP server: one @mcp.tool() per operation
├── pyproject.toml               # pip-installable
├── requirements.txt
├── .env.example
├── README.md                    # per-server usage + Claude Desktop snippet
├── tests/test_server.py         # smoke test: imports + all tools registered
└── claude_desktop_config.json   # drop-in MCP client config
```

Auth injection, HTTP transport, and error normalization come from **audited
templates** — only the tool set reflects your API. Write actions
(`POST/PUT/PATCH/DELETE`) are gated behind a `confirm=True` argument by default.

---

## Architecture

```
React + Vite + Tailwind (SPA)
        │  relative /api  (Vite proxy in dev; same-origin in prod)
FastAPI
  ├─ generation/  openapi_parser → proposer(LLM, optional) → codegen(Jinja) → validator(AST)
  ├─ playground/  live tool runner (session-scoped creds, SSRF guard, egress allowlist)
  ├─ export/      zip packager
  └─ db (SQLite)  projects + parse/generate results
```

Design choices vs. the original spec, for a self-contained MVP:

- **SQLite** instead of Supabase — zero external services, deploys anywhere.
- **Playground replicates the request** (same auth/param logic the generated
  server uses) with an SSRF guard + egress allowlist, instead of spawning a
  Docker sandbox per session. Generated code quality is proven by running each
  package's own test suite against the real MCP SDK.
- **Synchronous generation** — it's fast and template-bound, so no Celery/Redis.

### Security notes

- Every spec- or user-supplied value that lands inside generated Python source
  (auth header names, base URL, tool names/descriptions) is emitted as a
  `repr()`-escaped literal, not interpolated raw — a crafted spec cannot turn
  into executable code in the server you download.
- The validator uses `compile()`, not just `ast.parse()`, so output that would
  crash on import (e.g. a duplicate function argument) is caught before you
  see a "valid" badge.
- The static-file route resolves and containment-checks every path, so `..`
  segments can't escape the frontend's `dist/` directory.
- The playground's SSRF guard blocks private/loopback/link-local targets
  (including NAT64-wrapped addresses) and supports an optional host allowlist
  (`PLAYGROUND_ALLOWLIST`). **Known limitation:** it resolves DNS once to check
  the target, then hands the URL to `httpx`, which resolves again — a hostile
  DNS server could answer differently the second time (DNS rebinding). Don't
  point the playground at untrusted specs from parties you don't trust.

---

## MVP scope (per spec) & roadmap

**In:** OpenAPI input, API-key/bearer/basic auth, tool-proposal quality gate,
template generation, playground tool test panel, download export.

**Not yet:** plain-text/docs-URL parsing, OAuth2 token refresh, agent-chat
playground, hosted deploys, GitHub push, billing, versioning — these are the
V2/V3 layers from the spec and slot into the existing structure.

---

## Tests

```bash
cd backend
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install pytest
pytest tests/ -q
```

Covers: the Petstore spec yields the expected tools with write actions gated;
duplicate path/operation-level params don't produce uncompilable output;
hostile spec/user input (in auth header names, base URLs) can't become
executable code; the validator rejects duplicate function arguments; and path
parameters are URL-encoded. `python tests/test_pipeline.py` run directly also
prints the full generated `server.py` for inspection.
