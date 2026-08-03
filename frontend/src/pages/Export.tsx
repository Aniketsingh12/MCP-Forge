import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../api/client";
import type { GenerateResult } from "../types";
import Stepper from "../components/Stepper";
import CodeViewer from "../components/CodeViewer";

export default function Export() {
  const { id = "" } = useParams();
  const nav = useNavigate();
  const [result, setResult] = useState<GenerateResult | null>(null);

  useEffect(() => {
    api.getProject(id).then((p) => {
      if (!p.generate_result) return nav(`/p/${id}/proposal`);
      setResult(p.generate_result);
    });
  }, [id]);

  if (!result)
    return (
      <div>
        <Stepper current="export" projectId={id} reached={["proposal", "generate", "playground", "export"]} />
        <div className="card h-40 animate-pulse" />
      </div>
    );

  const claudeConfig = result.files.find(
    (f) => f.path === "claude_desktop_config.json"
  );

  return (
    <div>
      <Stepper
        current="export"
        projectId={id}
        reached={["proposal", "generate", "playground", "export"]}
      />

      <h1 className="text-2xl font-semibold tracking-tight text-slate-100">
        Export
      </h1>
      <p className="mt-1 text-sm text-slate-400">
        Download a complete, pip-installable package — server, tests, README, and
        a Claude Desktop config snippet.
      </p>

      <div className="mt-6 grid gap-4 md:grid-cols-3">
        {/* Download — active */}
        <div className="card flex flex-col p-5">
          <div className="mb-2 text-2xl">📦</div>
          <h3 className="font-medium text-slate-100">Download package</h3>
          <p className="mt-1 flex-1 text-sm text-slate-400">
            Zip with <span className="font-mono text-xs">server.py</span>,{" "}
            <span className="font-mono text-xs">pyproject.toml</span>, tests and
            README.
          </p>
          <a
            href={api.downloadUrl(id)}
            className="btn-primary mt-4"
            download
          >
            Download .zip
          </a>
        </div>

        {/* GitHub — v3 */}
        <div className="card flex flex-col p-5 opacity-70">
          <div className="mb-2 text-2xl">🐙</div>
          <h3 className="font-medium text-slate-100">Push to GitHub</h3>
          <p className="mt-1 flex-1 text-sm text-slate-400">
            Create a repo under your account via OAuth.
          </p>
          <button disabled className="btn-ghost mt-4">
            Coming in v3
          </button>
        </div>

        {/* Deploy — v3 */}
        <div className="card flex flex-col p-5 opacity-70">
          <div className="mb-2 text-2xl">🚀</div>
          <h3 className="font-medium text-slate-100">Hosted endpoint</h3>
          <p className="mt-1 flex-1 text-sm text-slate-400">
            One-click HTTP endpoint with a per-server URL + token.
          </p>
          <button disabled className="btn-ghost mt-4">
            Coming in v3
          </button>
        </div>
      </div>

      {claudeConfig && (
        <div className="mt-8">
          <h2 className="mb-3 text-sm font-medium text-slate-300">
            Use it with Claude Desktop
          </h2>
          <p className="mb-3 text-sm text-slate-400">
            Add this to your{" "}
            <span className="font-mono text-xs">claude_desktop_config.json</span>{" "}
            (point <span className="font-mono text-xs">args</span> at the
            downloaded <span className="font-mono text-xs">server.py</span>):
          </p>
          <CodeViewer content={claudeConfig.content} filename="claude_desktop_config.json" />
        </div>
      )}

      <div className="mt-8 flex gap-3">
        <Link to={`/p/${id}/playground`} className="btn-ghost">
          ← Back to playground
        </Link>
        <Link to="/dashboard" className="btn-ghost">
          Done — back to dashboard
        </Link>
      </div>
    </div>
  );
}
