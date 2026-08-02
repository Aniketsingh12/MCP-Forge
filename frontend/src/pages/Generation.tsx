import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../api/client";
import type { GenerateResult } from "../types";
import Stepper from "../components/Stepper";
import CodeViewer from "../components/CodeViewer";

const FILE_ICON: Record<string, string> = {
  python: "🐍",
  toml: "⚙",
  markdown: "📄",
  json: "{}",
  bash: "$",
  text: "≡",
};

export default function Generation() {
  const { id = "" } = useParams();
  const nav = useNavigate();
  const [result, setResult] = useState<GenerateResult | null>(null);
  const [active, setActive] = useState<string>("server.py");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getProject(id).then((p) => {
      if (!p.generate_result) {
        nav(`/p/${id}/proposal`);
        return;
      }
      setResult(p.generate_result);
      setLoading(false);
    });
  }, [id]);

  if (loading || !result)
    return (
      <div>
        <Stepper current="generate" projectId={id} reached={["proposal", "generate"]} />
        <div className="card h-64 animate-pulse" />
      </div>
    );

  const activeFile =
    result.files.find((f) => f.path === active) ?? result.files[0];

  return (
    <div>
      <Stepper
        current="generate"
        projectId={id}
        reached={["proposal", "generate", "playground", "export"]}
      />

      <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-slate-100">
            Generated server
          </h1>
          <div className="mt-2 flex items-center gap-3 text-sm">
            {result.valid ? (
              <span className="badge border-emerald-800/60 bg-emerald-950/40 text-emerald-300">
                ✓ validated
              </span>
            ) : (
              <span className="badge border-red-800/60 bg-red-950/40 text-red-300">
                ✕ validation issues
              </span>
            )}
            <span className="text-slate-500">
              {result.validation_messages.join(" · ")}
            </span>
          </div>
        </div>
        <div className="flex gap-3">
          <Link to={`/p/${id}/playground`} className="btn-ghost">
            Test in playground →
          </Link>
          <Link to={`/p/${id}/export`} className="btn-primary">
            Export →
          </Link>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-[220px_1fr]">
        <aside className="card h-fit overflow-hidden p-2">
          <div className="px-2 py-1.5 text-xs uppercase tracking-wide text-slate-500">
            {result.server_slug}/
          </div>
          {result.files.map((f) => (
            <button
              key={f.path}
              onClick={() => setActive(f.path)}
              className={
                "flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-sm " +
                (f.path === active
                  ? "bg-forge-500/10 text-forge-300"
                  : "text-slate-300 hover:bg-ink-800")
              }
            >
              <span className="w-4 text-center text-xs text-slate-500">
                {FILE_ICON[f.language] ?? "≡"}
              </span>
              <span className="truncate font-mono text-xs">{f.path}</span>
            </button>
          ))}
        </aside>

        <div>
          <CodeViewer content={activeFile.content} filename={activeFile.path} />
        </div>
      </div>
    </div>
  );
}
