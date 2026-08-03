import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { api } from "../api/client";
import type { PublicConfig } from "../types";
import Stepper from "../components/Stepper";
import { SAMPLE_SPEC } from "../lib/sampleSpec";

type Mode = "paste" | "url" | "sdk";

export default function NewProject() {
  const nav = useNavigate();
  const [params] = useSearchParams();
  const [name, setName] = useState("");
  const [mode, setMode] = useState<Mode>("paste");
  const [specText, setSpecText] = useState("");
  const [specUrl, setSpecUrl] = useState("");
  const [sdkModule, setSdkModule] = useState("");
  const [useLlm, setUseLlm] = useState(false);
  const [cfg, setCfg] = useState<PublicConfig | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.config().then(setCfg).catch(() => {});
  }, []);

  useEffect(() => {
    if (params.get("sample") === "1") {
      setSpecText(SAMPLE_SPEC);
      setName((n) => n || "Swagger Petstore");
    }
  }, [params]);

  const loadSample = () => {
    setMode("paste");
    setSpecText(SAMPLE_SPEC);
    if (!name) setName("Swagger Petstore");
  };

  const submit = async () => {
    setError(null);
    if (mode === "paste" && !specText.trim()) {
      setError("Paste an OpenAPI spec, or load the sample.");
      return;
    }
    if (mode === "url" && !specUrl.trim()) {
      setError("Enter a spec URL.");
      return;
    }
    if (mode === "sdk" && !sdkModule.trim()) {
      setError("Enter an installed Python module name, e.g. 'base64'.");
      return;
    }
    setBusy(true);
    try {
      const project = await api.createProject(name || "Untitled server");
      if (mode === "sdk") {
        await api.parseSdk(project.id, { module: sdkModule.trim(), use_llm: useLlm });
      } else {
        await api.parse(project.id, {
          spec_text: mode === "paste" ? specText : undefined,
          spec_url: mode === "url" ? specUrl : undefined,
          use_llm: useLlm,
        });
      }
      nav(`/p/${project.id}/proposal`);
    } catch (e) {
      setError((e as Error).message);
      setBusy(false);
    }
  };

  return (
    <div>
      <Stepper current="input" reached={[]} />

      <div className="mx-auto max-w-2xl">
        <h1 className="text-2xl font-semibold tracking-tight text-slate-100">
          New MCP server
        </h1>
        <p className="mt-1 text-sm text-slate-400">
          Map an <span className="text-slate-200">OpenAPI 3 / Swagger 2</span> spec
          or an installed <span className="text-slate-200">Python library</span>{" "}
          directly to tools — deterministic and reliable.
        </p>

        <div className="card mt-6 space-y-5 p-6">
          <div>
            <label className="label">Project name</label>
            <input
              className="input"
              placeholder="e.g. Stripe Billing Server"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>

          <div>
            <div className="mb-2 flex items-center justify-between">
              <label className="label mb-0">
                {mode === "sdk" ? "Python library" : "OpenAPI specification"}
              </label>
              {mode !== "sdk" && (
                <button
                  onClick={loadSample}
                  className="text-xs text-forge-500 hover:text-forge-400"
                >
                  Load sample (Petstore)
                </button>
              )}
            </div>

            <div className="mb-3 inline-flex rounded-lg border border-line bg-ink-950 p-0.5 text-sm">
              {(["paste", "url", "sdk"] as Mode[]).map((m) => (
                <button
                  key={m}
                  onClick={() => setMode(m)}
                  disabled={m === "sdk" && !cfg?.sdk_introspection_enabled}
                  title={
                    m === "sdk" && !cfg?.sdk_introspection_enabled
                      ? "Set ENABLE_SDK_INTROSPECTION=true to use this mode"
                      : undefined
                  }
                  className={
                    "rounded-md px-3 py-1 disabled:cursor-not-allowed disabled:opacity-40 " +
                    (mode === m
                      ? "bg-ink-700 text-slate-100"
                      : "text-slate-400 hover:text-slate-200")
                  }
                >
                  {m === "paste" ? "Paste spec" : m === "url" ? "From URL" : "Python library"}
                </button>
              ))}
            </div>

            {mode === "paste" ? (
              <textarea
                className="input h-64 resize-y font-mono text-xs"
                placeholder='Paste JSON or YAML OpenAPI spec here…'
                value={specText}
                onChange={(e) => setSpecText(e.target.value)}
              />
            ) : mode === "url" ? (
              <input
                className="input"
                placeholder="https://api.example.com/openapi.json"
                value={specUrl}
                onChange={(e) => setSpecUrl(e.target.value)}
              />
            ) : (
              <div>
                <input
                  className="input font-mono text-sm"
                  placeholder="e.g. base64, pathlib, or an installed package"
                  value={sdkModule}
                  onChange={(e) => setSdkModule(e.target.value)}
                />
                <p className="mt-2 text-xs text-slate-400">
                  Wraps a Python library's public functions as tools that run
                  in-process — for software with no REST API.
                </p>
                <p className="mt-2 rounded-lg border border-amber-900/50 bg-amber-950/20 px-3 py-2 text-xs text-amber-300">
                  Introspection imports the module, which runs its top-level
                  code. Only point this at libraries you trust.
                </p>
                {cfg?.sdk_allowed_modules?.length ? (
                  <p className="mt-2 font-mono text-xs text-slate-500">
                    allowed: {cfg.sdk_allowed_modules.join(", ")}
                  </p>
                ) : null}
              </div>
            )}
          </div>

          {cfg?.llm_enabled && (
            <label className="flex cursor-pointer items-center gap-2 text-sm text-slate-300">
              <input
                type="checkbox"
                checked={useLlm}
                onChange={(e) => setUseLlm(e.target.checked)}
                className="accent-forge-500"
              />
              Polish tool descriptions with{" "}
              <span className="font-mono text-xs text-forge-400">
                {cfg.llm_model || cfg.llm_provider}
              </span>
            </label>
          )}

          {error && (
            <div className="rounded-lg border border-red-900/60 bg-red-950/40 px-3 py-2 text-sm text-red-300">
              {error}
            </div>
          )}

          <div className="flex justify-end gap-3 pt-1">
            <button
              onClick={submit}
              disabled={busy}
              className="btn-primary"
            >
              {busy ? "Parsing spec…" : "Parse spec →"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
