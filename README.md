# MCP Server builder

**MCP servers without the expertise.** Point it at an OpenAPI spec (or an
installed Python library) → review the proposed tools → generate a full MCP
server from audited templates → **run it as a real MCP server** in the
playground → download a pip-installable package.

Generation is **deterministic** (no model required) and **open-source-model
friendly** (optional description polishing via Ollama or any OpenAI-compatible
endpoint). Ships as a **single deployable container**.

```
OpenAPI spec  ┐
              ├→ Tool proposal → Generate → Playground → Download
Python library┘   (edit / gate)  (templates) (real MCP)  (.zip package)
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

1. **New project** — from the homepage hit **Forge a server** (or **Try the
   sample spec** to skip straight to a filled-in demo). Existing projects live
   under **Dashboard**.
2. **Input** — one of:
   - paste an OpenAPI 3 / Swagger 2 spec (JSON or YAML), or a hosted spec URL.
     No spec handy? Click **Load sample (Petstore)**;
   - or pick **Python library** and name an installed module (see
     [SDK mode](#python-sdk-mode) — off by default).
3. **Tool proposal (the quality gate)** — every operation becomes a candidate
   tool. Uncheck what you don't want, rename tools, edit descriptions (this is
   what an agent reads to decide when to call a tool), and toggle
   **confirm-required** (on by default for `POST/PUT/PATCH/DELETE`). For
   submit-then-poll APIs, toggle **long-running job** (see
   [async jobs](#async-jobs)). Confirm the base URL and auth type. Click
   **Generate server →**.
4. **Generate** — template-driven codegen runs (no model involved); browse the
   file tree and check the ✓ **validated** badge.
5. **Playground** — MCP Forge launches your generated package **as a real MCP
   server** over stdio, performs the protocol handshake, and lists the tools it
   actually advertises. Pick one, fill the form built from its real JSON schema,
   enter your credential (session-only, never persisted), and **▶ Call tool** —
   this is a genuine `tools/call`, so what you test is the code you download.
   Iterate: edit a tool in step 3, regenerate, retest.
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
| Together AI (hosted open-weight) | `together` | `https://api.together.ai/v1` (default) | `meta-llama/Llama-3.3-70B-Instruct-Turbo` (default) |
| OpenRouter / Groq / vLLM / LM Studio | `openai-compatible` | e.g. `https://openrouter.ai/api/v1` | any model id |
| Anthropic | `anthropic` | `https://api.anthropic.com/v1` | `claude-opus-4-8` |
| Disabled (default) | `none` | — | — |

**Together AI:** create a key at [api.together.ai/settings/api-keys](https://api.together.ai/settings/api-keys), then set:

```bash
LLM_PROVIDER=together
LLM_API_KEY=<your key>
```

`LLM_MODEL` and `LLM_BASE_URL` can stay unset — they default to Together's
`Llama-3.3-70B-Instruct-Turbo` endpoint. Set `LLM_MODEL` to any other model id
from your Together dashboard to switch.

**Check the connection** (works against any provider):

```bash
curl https://<your-app>/api/llm/test
```

Returns `{"ok": true, ...}` on a successful round trip, or the provider's own
error if the key or model id is wrong. Worth running right after a deploy —
description polishing falls back to spec text rather than failing the request,
so a bad key would otherwise just look like the feature doing nothing. (The
tool-review screen also shows a warning when a polish attempt fails.)

**Local models with Docker:** uncomment the `ollama` service in
[`docker-compose.yml`](docker-compose.yml), then:

```bash
docker compose up --build -d
docker compose exec ollama ollama pull llama3.1
# .env: LLM_PROVIDER=ollama  LLM_BASE_URL=http://ollama:11434/v1  LLM_MODEL=llama3.1
```

---

## <a id="async-jobs"></a>Async jobs (submit → poll → result)

Generative-AI APIs usually return a job id and expect you to poll a status
endpoint. Left alone that becomes two unrelated tools and the agent has to
invent the loop. Toggle **long-running job** on a tool and configure:

| Field | Meaning | Example |
|-------|---------|---------|
| Job id field | where the submit response carries the id | `id`, `data.job_id` |
| Status path | status endpoint; `{job_id}` is substituted | `/jobs/{job_id}` |
| Status field | where the status response carries state | `status` |
| Success / failure values | terminal states | `succeeded` / `failed` |
| Interval, max polls | pacing and give-up point | `2.0`, `60` |

The generated tool submits, polls until the job resolves, and returns the final
result — one call, no orchestration on the agent's side. Timeouts and failure
states come back as normal error envelopes.

---

## <a id="python-sdk-mode"></a>Python SDK mode

Not everything has a REST API. Playwright, Blender's `bpy`, and similar tools
expose a **Python library** instead. In that mode MCP Forge introspects an
installed module and generates tools that call it **in-process** — same audited
scaffold (error normalization, confirm gates, packaging), no HTTP layer.

```bash
ENABLE_SDK_INTROSPECTION=true
SDK_ALLOWED_MODULES=playwright,pandas    # optional; empty = any installed module
```

> **This is off by default, and should stay off on shared deployments.**
> Introspection *imports* the module, which executes its top-level code — on a
> hosted instance that is remote code execution. Enable it for local,
> single-user use, and use `SDK_ALLOWED_MODULES` to narrow what can be imported.

Scope: public module-level functions with introspectable signatures. Methods
that need a constructed instance, and `*args`/`**kwargs`, are skipped — those
remain hand-built work.

---

## Running this publicly (abuse limits)

Anything reachable by a link is reachable by everyone, so a public deploy needs
two things: **nobody else spending your model credits**, and **nobody exhausting
the box**.

The useful asymmetry here is that **description polishing is the only feature
that costs money.** Parsing, the tool-proposal gate, generation, validation, the
playground and download are all deterministic and free. So you don't have to gate
the demo — just the metered path:

```bash
LLM_ACCESS_KEY=<a long random string>
```

With that set, `use_llm` requests (and `/api/llm/test`) require an
`X-LLM-Access-Key` header, while the rest of the app stays fully open to visitors.
The UI shows a key field only when the deployment requires one, and stores it in
your browser so you type it once. Without a key configured, polishing stays open —
which is what you want locally.

Also enforced by default:

| Control | Default | Env var |
|---|---|---|
| Per-IP rate limits (parse, generate, playground, project create) | on | `RATE_LIMIT_ENABLED` |
| Max spec upload size | 2 MB | `MAX_SPEC_BYTES` |
| Max tools sent to the model in one prompt | 60 | `MAX_LLM_TOOLS` |

> **Set a hard spending cap at your model provider too.** The rate limiter is
> in-process, so counters are per-instance and reset on redeploy. That is a
> throttle against casual abuse and runaway loops — it is *not* a billing
> guarantee. A provider-side cap holds even if this process restarts or a bug
> lets a request through, so it's the only real backstop.

Note also that the playground spawns a Python subprocess per call, which is
cheaper to abuse than your credits (no key needed, no tokens spent). It is rate
limited, but if you expect real traffic, cap concurrency as well.

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

For each project you get a complete, runnable package:

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

Auth injection, transport, and error normalization come from **audited
templates** — only the tool set reflects your API or library. Write actions
(`POST/PUT/PATCH/DELETE`, or mutating-sounding library functions) are gated
behind a `confirm=True` argument by default.

`mcp` is pinned `<2` in generated packages: 2.0 replaced `FastMCP` with
`MCPServer`, and the 1.x API is what MCP client documentation describes.

---

## Architecture

```
React + Vite + Tailwind (SPA)
        │  relative /api  (Vite proxy in dev; same-origin in prod)
FastAPI
  ├─ generation/  openapi_parser ┐
  │               sdk_introspect ┴→ proposer(LLM, opt) → codegen(Jinja) → validator(compile)
  ├─ playground/  mcp_runner: spawns generated server, drives it over stdio
  ├─ netguard.py  egress allowlist + SSRF check, shared by the playground
  │               launch and the backend's own spec_url fetch
  ├─ ratelimit.py in-process per-IP sliding-window limiter (parse/generate/
  │               playground/project-create/llm-test)
  ├─ export/      zip packager
  └─ db (SQLite)  projects + parse/generate results
```

Design choices vs. the original spec, for a self-contained MVP:

- **SQLite** instead of Supabase — zero external services, deploys anywhere.
- **The playground runs the real thing.** Your generated package is written to a
  temp directory and launched as an MCP server; the backend is a generic MCP
  client speaking stdio JSON-RPC to it. Isolation is process-level (scrubbed
  environment, temp cwd, timeout, torn down after each call) rather than a
  container — adequate for code you just generated yourself, not a hostile-code
  sandbox.
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
- Every outbound URL is validated by the same egress guard — both the base URL
  handed to the playground's child process **and** the `spec_url` the backend
  fetches itself (redirects are followed manually so a public URL cannot 302 to
  an internal one). Checks run **before** any request leaves: private/loopback/link-local targets
  are refused (including NAT64-wrapped addresses) and `PLAYGROUND_ALLOWLIST` can
  restrict permitted hosts. **Known limitation:** the guard resolves DNS to
  validate, then the child resolves again when it connects — a hostile DNS
  server could answer differently the second time (DNS rebinding). Don't point
  the playground at specs from parties you don't trust.
- **Python SDK mode is disabled by default** because introspection imports the
  target module, executing its code. See [Python SDK mode](#python-sdk-mode).

---

## MVP scope (per spec) & roadmap

**In:** OpenAPI + Python-library input, API-key/bearer/basic auth,
tool-proposal quality gate, async job polling, template generation, a playground
that drives the real MCP protocol, download export.

**Not yet:** plain-text/docs-URL parsing, OAuth2 token refresh, agent-chat
playground, hosted deploys, GitHub push, billing, versioning — these are the
V2/V3 layers from the spec and slot into the existing structure.

**Out of scope by design:** integrations that need a plugin *inside* a running
desktop app (Blender's `bpy`, Unreal) can't be generated — they need a
hand-written bridge addon on the far side. That's the spec's Custom tier.

---

## Tests

```bash
cd backend
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install pytest
pytest tests/ -q
```

25 tests across two files:

- **`test_pipeline.py`** — the Petstore spec yields the expected tools with
  write actions gated; duplicate path/operation-level params don't produce
  uncompilable output; hostile spec/user input (auth header names, base URLs,
  module paths) can't become executable code; the validator rejects duplicate
  function arguments; path parameters are URL-encoded; polling emits a
  submit-and-poll tool (and no dead helper code when unused); and SDK
  introspection stays disabled without the env flag. Run directly
  (`python tests/test_pipeline.py`) it also prints the full generated
  `server.py` for inspection.
- **`test_hardening.py`** — the public-deploy abuse limits: SSRF is blocked
  against loopback/link-local/cloud-metadata/private/`file://` targets, a
  redirect is re-validated on *every* hop (a public URL can't 302 to an
  internal one), `LLM_ACCESS_KEY` gates `use_llm` requests and `/api/llm/test`
  but never leaks through `/api/config` or `/api/health`, oversized specs get
  a 413, and the rate limiter trips a 429 with `Retry-After` and resets
  per client.
