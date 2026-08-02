import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../api/client";
import type { AuthConfig, McpCallResult, McpTool } from "../types";
import Stepper from "../components/Stepper";
import SchemaForm, { type ArgValues } from "../components/SchemaForm";
import JsonView from "../components/JsonView";

/** One entry in the tool-call trace timeline. */
interface TraceEntry extends McpCallResult {
  at: string;
  parsed: unknown;
  request?: { method?: string; url?: string; body?: unknown };
}

export default function Playground() {
  const { id = "" } = useParams();
  const nav = useNavigate();

  const [tools, setTools] = useState<McpTool[]>([]);
  const [auth, setAuth] = useState<AuthConfig | null>(null);
  const [baseUrl, setBaseUrl] = useState("");
  const [credential, setCredential] = useState("");
  const [selected, setSelected] = useState(0);
  const [args, setArgs] = useState<ArgValues>({});
  const [trace, setTrace] = useState<TraceEntry[]>([]);
  const [connecting, setConnecting] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<"result" | "raw">("result");

  const connect = useCallback(
    async (url: string, cred: string) => {
      setConnecting(true);
      setError(null);
      try {
        const res = await api.mcpTools(id, { base_url: url, credential: cred });
        setTools(res.tools);
      } catch (e) {
        setError((e as Error).message);
        setTools([]);
      } finally {
        setConnecting(false);
      }
    },
    [id]
  );

  useEffect(() => {
    api.getProject(id).then((p) => {
      if (!p.generate_result) return nav(`/p/${id}/proposal`);
      const url = p.parse_result?.base_url ?? "";
      setBaseUrl(url);
      setAuth(p.parse_result?.auth ?? null);
      connect(url, "");
    });
  }, [id, connect]);

  const tool = tools[selected];

  useEffect(() => {
    setArgs({});
    setTab("result");
  }, [selected]);

  const run = async () => {
    if (!tool) return;
    setError(null);
    setRunning(true);
    try {
      const res = await api.mcpCall(id, {
        base_url: baseUrl,
        credential,
        tool: tool.name,
        args,
      });
      let parsed: unknown = res.text;
      let request: TraceEntry["request"];
      try {
        const obj = JSON.parse(res.text);
        parsed = obj;
        if (obj && typeof obj === "object" && "_request" in obj) {
          request = (obj as Record<string, unknown>)._request as TraceEntry["request"];
        }
      } catch {
        /* non-JSON tool output is fine */
      }
      setTrace((t) => [
        { ...res, at: new Date().toLocaleTimeString(), parsed, request },
        ...t,
      ]);
      setTab("result");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setRunning(false);
    }
  };

  const credHint = auth
    ? auth.type === "basic"
      ? "username:password"
      : auth.type === "bearer"
        ? "bearer token"
        : auth.type === "none"
          ? "no credential needed"
          : `API key (${auth.param_name})`
    : "";

  const latest = trace[0];

  return (
    <div>
      <Stepper
        current="playground"
        projectId={id}
        reached={["proposal", "generate", "playground", "export"]}
      />

      <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-slate-100">
            Playground
          </h1>
          <p className="mt-1 text-sm text-slate-400">
            Your generated package is launched as a real MCP server and driven
            over stdio — what you test is the code you download.
          </p>
        </div>
        <Link to={`/p/${id}/export`} className="btn-primary">
          Export →
        </Link>
      </div>

      {/* Connection bar */}
      <div className="card mb-5 flex flex-wrap items-end gap-4 p-4">
        <div className="min-w-[16rem] flex-1">
          <label className="label">Base URL</label>
          <input
            className="input font-mono text-xs"
            value={baseUrl}
            onChange={(e) => setBaseUrl(e.target.value)}
          />
        </div>
        {auth && auth.type !== "none" && (
          <div className="min-w-[16rem] flex-1">
            <label className="label">Credential — {credHint} (session only)</label>
            <input
              className="input font-mono text-xs"
              type="password"
              value={credential}
              placeholder={credHint}
              onChange={(e) => setCredential(e.target.value)}
            />
          </div>
        )}
        <button
          onClick={() => connect(baseUrl, credential)}
          disabled={connecting}
          className="btn-ghost"
        >
          {connecting ? "Connecting…" : "↻ Reconnect"}
        </button>
      </div>

      {error && (
        <div className="mb-4 rounded-lg border border-red-900/60 bg-red-950/40 px-3 py-2 text-sm text-red-300">
          {error}
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-[250px_1fr]">
        {/* Tools advertised by the running server */}
        <aside className="card h-fit overflow-hidden p-2">
          <div className="flex items-center gap-2 px-2 py-1.5 text-xs uppercase tracking-wide text-slate-500">
            <span
              className={
                "h-1.5 w-1.5 rounded-full " +
                (connecting
                  ? "bg-amber-400"
                  : tools.length
                    ? "bg-emerald-400"
                    : "bg-red-400")
              }
            />
            {connecting
              ? "starting server…"
              : `${tools.length} tool${tools.length === 1 ? "" : "s"} via MCP`}
          </div>
          {tools.map((t, i) => (
            <button
              key={t.name}
              onClick={() => setSelected(i)}
              className={
                "block w-full truncate rounded-md px-2 py-2 text-left font-mono text-xs " +
                (i === selected
                  ? "bg-forge-500/10 text-forge-300"
                  : "text-slate-300 hover:bg-ink-800")
              }
            >
              {t.name}
            </button>
          ))}
        </aside>

        <div className="space-y-4">
          {tool ? (
            <>
              <div className="card p-5">
                <div className="mb-1 font-mono text-sm text-slate-200">
                  {tool.name}
                </div>
                <p className="mb-4 text-sm text-slate-400">{tool.description}</p>

                <SchemaForm tool={tool} values={args} onChange={setArgs} />

                <div className="mt-5 flex items-center gap-3">
                  <button onClick={run} disabled={running} className="btn-primary">
                    {running ? "Calling…" : "▶ Call tool"}
                  </button>
                  <span className="font-mono text-xs text-slate-500">
                    tools/call → {tool.name}
                  </span>
                </div>
              </div>

              {latest && (
                <div className="card p-5">
                  <div className="mb-4 flex flex-wrap items-center gap-3">
                    <span
                      className={
                        "badge " +
                        (latest.is_error
                          ? "border-red-800/60 bg-red-950/40 text-red-300"
                          : "border-emerald-800/60 bg-emerald-950/40 text-emerald-300")
                      }
                    >
                      {latest.is_error ? "tool error" : "ok"}
                    </span>
                    <span className="text-xs text-slate-500">
                      {latest.latency_ms} ms
                    </span>
                    {latest.request?.url && (
                      <span className="truncate font-mono text-xs text-slate-500">
                        {latest.request.method} {latest.request.url}
                      </span>
                    )}
                    <div className="ml-auto inline-flex rounded-md border border-line bg-ink-950 p-0.5 text-xs">
                      {(["result", "raw"] as const).map((t) => (
                        <button
                          key={t}
                          onClick={() => setTab(t)}
                          className={
                            "rounded px-2 py-0.5 " +
                            (tab === t ? "bg-ink-700 text-slate-100" : "text-slate-400")
                          }
                        >
                          {t}
                        </button>
                      ))}
                    </div>
                  </div>
                  <JsonView value={tab === "result" ? latest.parsed : latest.text} />
                </div>
              )}

              {trace.length > 1 && (
                <div className="card p-5">
                  <h2 className="mb-3 text-sm font-medium text-slate-300">
                    Tool-call trace
                  </h2>
                  <ol className="space-y-2">
                    {trace.map((t, i) => (
                      <li
                        key={i}
                        className="flex items-center gap-3 border-l-2 border-line pl-3 text-xs"
                      >
                        <span
                          className={
                            "h-1.5 w-1.5 shrink-0 rounded-full " +
                            (t.is_error ? "bg-red-400" : "bg-emerald-400")
                          }
                        />
                        <span className="font-mono text-slate-300">{t.tool}</span>
                        <span className="truncate text-slate-500">
                          {JSON.stringify(t.args)}
                        </span>
                        <span className="ml-auto shrink-0 text-slate-600">
                          {t.latency_ms} ms · {t.at}
                        </span>
                      </li>
                    ))}
                  </ol>
                </div>
              )}
            </>
          ) : (
            !connecting && (
              <div className="card p-8 text-center text-sm text-slate-400">
                No tools available. Check the base URL and reconnect.
              </div>
            )
          )}
        </div>
      </div>
    </div>
  );
}
