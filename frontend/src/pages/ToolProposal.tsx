import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../api/client";
import type { AuthConfig, ProposedTool, ServerKind } from "../types";
import Stepper from "../components/Stepper";
import ToolEditor from "../components/ToolEditor";

const AUTH_TYPES: AuthConfig["type"][] = ["api_key", "bearer", "basic", "none"];

export default function ToolProposal() {
  const { id = "" } = useParams();
  const nav = useNavigate();

  const [title, setTitle] = useState("");
  const [slug, setSlug] = useState("");
  const [baseUrl, setBaseUrl] = useState("");
  const [auth, setAuth] = useState<AuthConfig | null>(null);
  const [tools, setTools] = useState<ProposedTool[]>([]);
  const [kind, setKind] = useState<ServerKind>("http");
  const [sdkModule, setSdkModule] = useState("");
  const [llmError, setLlmError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .getProject(id)
      .then((p) => {
        if (!p.parse_result) {
          nav("/new");
          return;
        }
        const pr = p.parse_result;
        setTitle(pr.api_title);
        setSlug(pr.server_slug);
        setBaseUrl(pr.base_url);
        setAuth(pr.auth);
        setTools(pr.tools);
        setKind(pr.kind ?? "http");
        setSdkModule(pr.sdk_module ?? "");
        setLlmError(pr.llm_error ?? null);
      })
      .catch((e) => setError((e as Error).message))
      .finally(() => setLoading(false));
  }, [id]);

  const enabledCount = useMemo(
    () => tools.filter((t) => t.enabled).length,
    [tools]
  );

  const updateTool = (idx: number, t: ProposedTool) =>
    setTools((prev) => prev.map((x, i) => (i === idx ? t : x)));

  const generate = async () => {
    if (!auth) return;
    setError(null);
    if (enabledCount === 0) {
      setError("Enable at least one tool.");
      return;
    }
    if (kind === "http" && !baseUrl.trim()) {
      setError("A base URL is required — the spec didn't include one.");
      return;
    }
    setBusy(true);
    try {
      await api.generate(id, {
        server_slug: slug,
        api_title: title,
        base_url: baseUrl.trim(),
        auth,
        tools,
        kind,
        sdk_module: sdkModule,
      });
      nav(`/p/${id}/generate`);
    } catch (e) {
      setError((e as Error).message);
      setBusy(false);
    }
  };

  if (loading)
    return (
      <div>
        <Stepper current="proposal" projectId={id} reached={["proposal"]} />
        <div className="card h-40 animate-pulse" />
      </div>
    );

  return (
    <div>
      <Stepper current="proposal" projectId={id} reached={["proposal"]} />

      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-slate-100">
            Review tools
          </h1>
          <p className="mt-1 text-sm text-slate-400">
            The quality gate. Rename, drop, tweak descriptions, and mark write
            actions before generating.
          </p>
        </div>
        <button onClick={generate} disabled={busy} className="btn-primary">
          {busy ? "Generating…" : `Generate server (${enabledCount}) →`}
        </button>
      </div>

      {/* Server config */}
      <div className="card mb-6 grid gap-4 p-5 sm:grid-cols-2 lg:grid-cols-4">
        <div className="lg:col-span-1">
          <label className="label">Server name</label>
          <input
            className="input font-mono text-xs"
            value={slug}
            onChange={(e) => setSlug(e.target.value)}
          />
        </div>
        {kind === "python_sdk" ? (
          <div className="sm:col-span-1 lg:col-span-3">
            <label className="label">Python module</label>
            <div className="input font-mono text-xs text-slate-400">
              import {sdkModule}
            </div>
            <p className="mt-1 text-xs text-slate-500">
              Tools call this library in-process — no base URL or credentials.
            </p>
          </div>
        ) : (
          <div className="sm:col-span-1 lg:col-span-2">
            <label className="label">Base URL</label>
            <input
              className="input font-mono text-xs"
              value={baseUrl}
              placeholder="https://api.example.com"
              onChange={(e) => setBaseUrl(e.target.value)}
            />
          </div>
        )}
        {kind === "http" && auth && (
          <div>
            <label className="label">Auth</label>
            <div className="flex gap-2">
              <select
                className="input"
                value={auth.type}
                onChange={(e) =>
                  setAuth({ ...auth, type: e.target.value as AuthConfig["type"] })
                }
              >
                {AUTH_TYPES.map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>
            </div>
            {(auth.type === "api_key" || auth.type === "bearer") && (
              <input
                className="input mt-2 font-mono text-xs"
                value={auth.param_name}
                onChange={(e) => setAuth({ ...auth, param_name: e.target.value })}
                placeholder="Header / query name"
              />
            )}
          </div>
        )}
      </div>

      {llmError && (
        <div className="mb-4 rounded-lg border border-amber-900/50 bg-amber-950/20 px-3 py-2 text-sm text-amber-300">
          <span className="font-medium">
            Descriptions weren't polished — the model call failed.
          </span>{" "}
          These are the descriptions read straight from the spec, which are
          still valid. Check <code className="font-mono text-xs">LLM_API_KEY</code>{" "}
          and <code className="font-mono text-xs">LLM_MODEL</code>.
          <div className="mt-1 font-mono text-xs text-amber-400/80">{llmError}</div>
        </div>
      )}

      {error && (
        <div className="mb-4 rounded-lg border border-red-900/60 bg-red-950/40 px-3 py-2 text-sm text-red-300">
          {error}
        </div>
      )}

      <div className="space-y-3">
        {tools.map((t, i) => (
          <ToolEditor key={i} tool={t} onChange={(nt) => updateTool(i, nt)} />
        ))}
      </div>
    </div>
  );
}
