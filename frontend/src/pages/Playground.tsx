import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../api/client";
import type { AuthConfig, ProposedTool, TestToolResult } from "../types";
import Stepper from "../components/Stepper";
import ParamForm, { type ArgValues } from "../components/ParamForm";
import JsonView from "../components/JsonView";
import { methodColor } from "../lib/utils";

export default function Playground() {
  const { id = "" } = useParams();
  const nav = useNavigate();

  const [tools, setTools] = useState<ProposedTool[]>([]);
  const [auth, setAuth] = useState<AuthConfig | null>(null);
  const [baseUrl, setBaseUrl] = useState("");
  const [credential, setCredential] = useState("");
  const [selected, setSelected] = useState(0);
  const [args, setArgs] = useState<ArgValues>({});
  const [result, setResult] = useState<TestToolResult | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<"normalized" | "raw">("normalized");

  useEffect(() => {
    api.getProject(id).then((p) => {
      if (!p.parse_result) return nav("/new");
      const enabled = p.parse_result.tools.filter((t) => t.enabled);
      setTools(enabled);
      setAuth(p.parse_result.auth);
      setBaseUrl(p.parse_result.base_url);
    });
  }, [id]);

  const tool = tools[selected];

  // Reset args when switching tools.
  useEffect(() => {
    setArgs({});
    setResult(null);
    setError(null);
  }, [selected]);

  const credHint = useMemo(() => {
    if (!auth) return "";
    switch (auth.type) {
      case "basic":
        return "username:password";
      case "bearer":
        return "bearer token";
      case "none":
        return "no credential needed";
      default:
        return `API key (${auth.param_name})`;
    }
  }, [auth]);

  const run = async () => {
    if (!tool || !auth) return;
    setError(null);
    setRunning(true);
    setResult(null);
    // include confirm=true so write actions actually execute from the playground
    const finalArgs = tool.confirm_required ? { ...args, confirm: true } : args;
    try {
      const res = await api.testTool({
        base_url: baseUrl,
        auth,
        credential,
        tool,
        args: finalArgs,
      });
      setResult(res);
      setTab("normalized");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setRunning(false);
    }
  };

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
            Fire each tool against the live API with your own credential. Nothing
            is stored server-side.
          </p>
        </div>
        <Link to={`/p/${id}/export`} className="btn-primary">
          Export →
        </Link>
      </div>

      {/* Credential bar */}
      <div className="card mb-5 flex flex-wrap items-end gap-4 p-4">
        <div className="flex-1">
          <label className="label">Base URL</label>
          <input
            className="input font-mono text-xs"
            value={baseUrl}
            onChange={(e) => setBaseUrl(e.target.value)}
          />
        </div>
        {auth && auth.type !== "none" && (
          <div className="flex-1">
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
      </div>

      <div className="grid gap-4 lg:grid-cols-[240px_1fr]">
        {/* Tool list */}
        <aside className="card h-fit overflow-hidden p-2">
          {tools.map((t, i) => (
            <button
              key={i}
              onClick={() => setSelected(i)}
              className={
                "flex w-full items-center gap-2 rounded-md px-2 py-2 text-left " +
                (i === selected ? "bg-forge-500/10" : "hover:bg-ink-800")
              }
            >
              <span className={"badge shrink-0 font-mono text-[10px] " + methodColor(t.method)}>
                {t.method}
              </span>
              <span
                className={
                  "truncate font-mono text-xs " +
                  (i === selected ? "text-forge-300" : "text-slate-300")
                }
              >
                {t.name}
              </span>
            </button>
          ))}
        </aside>

        {/* Test panel */}
        <div className="space-y-4">
          {tool && (
            <>
              <div className="card p-5">
                <div className="mb-3 flex items-center gap-2">
                  <span className={"badge font-mono " + methodColor(tool.method)}>
                    {tool.method}
                  </span>
                  <span className="font-mono text-sm text-slate-200">{tool.name}</span>
                  {tool.confirm_required && (
                    <span className="badge border-amber-800/60 bg-amber-950/40 text-amber-300">
                      write · confirm auto-sent
                    </span>
                  )}
                </div>
                <p className="mb-4 text-sm text-slate-400">{tool.description}</p>

                <ParamForm tool={tool} values={args} onChange={setArgs} />

                <div className="mt-5 flex items-center gap-3">
                  <button onClick={run} disabled={running} className="btn-primary">
                    {running ? "Running…" : "▶ Run tool"}
                  </button>
                  <span className="font-mono text-xs text-slate-500">
                    {tool.method} {baseUrl}
                    {tool.path}
                  </span>
                </div>

                {error && (
                  <div className="mt-4 rounded-lg border border-red-900/60 bg-red-950/40 px-3 py-2 text-sm text-red-300">
                    {error}
                  </div>
                )}
              </div>

              {result && <ResultView result={result} tab={tab} setTab={setTab} />}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function ResultView({
  result,
  tab,
  setTab,
}: {
  result: TestToolResult;
  tab: "normalized" | "raw";
  setTab: (t: "normalized" | "raw") => void;
}) {
  const ok = (result.normalized as { ok?: boolean }).ok;
  return (
    <div className="card p-5">
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <span
          className={
            "badge " +
            (result.status_code && result.status_code < 400
              ? "border-emerald-800/60 bg-emerald-950/40 text-emerald-300"
              : "border-red-800/60 bg-red-950/40 text-red-300")
          }
        >
          {result.status_code ?? "no response"}
        </span>
        <span className="text-xs text-slate-500">{result.latency_ms} ms</span>
        <span
          className={
            "text-xs " + (ok ? "text-emerald-400" : "text-red-400")
          }
        >
          {ok ? "ok" : "error"}
        </span>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <div>
          <div className="label">Request</div>
          <div className="rounded-lg border border-line bg-ink-950 p-3 font-mono text-xs text-slate-300">
            <div className="text-forge-400">
              {result.request_method} {result.request_url}
            </div>
            <div className="mt-2 space-y-0.5 text-slate-400">
              {Object.entries(result.request_headers).map(([k, v]) => (
                <div key={k}>
                  <span className="text-slate-500">{k}:</span> {v}
                </div>
              ))}
            </div>
            {result.request_body != null && (
              <pre className="mt-2 whitespace-pre-wrap text-slate-300">
                {JSON.stringify(result.request_body, null, 2)}
              </pre>
            )}
          </div>
        </div>

        <div>
          <div className="mb-1 flex items-center justify-between">
            <span className="label mb-0">Response</span>
            <div className="inline-flex rounded-md border border-line bg-ink-950 p-0.5 text-xs">
              {(["normalized", "raw"] as const).map((t) => (
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
          <JsonView value={tab === "normalized" ? result.normalized : result.response_body} />
        </div>
      </div>
    </div>
  );
}
