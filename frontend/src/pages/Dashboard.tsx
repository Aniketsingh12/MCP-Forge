import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api/client";
import type { ProjectState } from "../types";
import { statusColor, timeAgo } from "../lib/utils";

export default function Dashboard() {
  const [projects, setProjects] = useState<ProjectState[] | null>(null);
  const nav = useNavigate();

  const load = () => api.listProjects().then(setProjects);
  useEffect(() => {
    load();
  }, []);

  const remove = async (id: string, name: string) => {
    if (!confirm(`Delete "${name}"? This cannot be undone.`)) return;
    await api.deleteProject(id);
    load();
  };

  const resumeLink = (p: ProjectState) => {
    if (p.generate_result) return `/p/${p.id}/generate`;
    if (p.parse_result) return `/p/${p.id}/proposal`;
    return `/p/${p.id}/proposal`;
  };

  return (
    <div>
      <div className="mb-8 flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-slate-100">
            Your servers
          </h1>
          <p className="mt-1 text-sm text-slate-400">
            Describe an integration with an OpenAPI spec, get a working MCP
            server — generated, tested, and downloadable.
          </p>
        </div>
      </div>

      {projects === null ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {[0, 1, 2].map((i) => (
            <div key={i} className="card h-32 animate-pulse" />
          ))}
        </div>
      ) : projects.length === 0 ? (
        <EmptyState onCreate={() => nav("/new")} />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {projects.map((p) => {
            const toolCount = p.parse_result?.tools.filter((t) => t.enabled).length ?? 0;
            return (
              <div key={p.id} className="card group flex flex-col p-4">
                <div className="flex items-start justify-between">
                  <Link
                    to={resumeLink(p)}
                    className="font-medium text-slate-100 hover:text-forge-400"
                  >
                    {p.name}
                  </Link>
                  <span className={"badge " + statusColor(p.status)}>
                    {p.status}
                  </span>
                </div>
                <div className="mt-3 flex-1 text-sm text-slate-400">
                  {p.parse_result ? (
                    <>
                      <div className="font-mono text-xs text-slate-500">
                        {p.parse_result.base_url || "no base url"}
                      </div>
                      <div className="mt-1">{toolCount} tool(s)</div>
                    </>
                  ) : (
                    <span className="text-slate-500">No spec yet</span>
                  )}
                </div>
                <div className="mt-4 flex items-center justify-between border-t border-line pt-3 text-xs text-slate-500">
                  <span>{timeAgo(p.updated_at)}</span>
                  <div className="flex items-center gap-2">
                    <Link
                      to={resumeLink(p)}
                      className="text-forge-500 hover:text-forge-400"
                    >
                      Open →
                    </Link>
                    <button
                      onClick={() => remove(p.id, p.name)}
                      className="text-slate-500 opacity-0 transition-opacity hover:text-red-400 group-hover:opacity-100"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function EmptyState({ onCreate }: { onCreate: () => void }) {
  return (
    <div className="card flex flex-col items-center justify-center px-6 py-16 text-center">
      <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-forge-500/10 text-3xl">
        🔨
      </div>
      <h2 className="text-lg font-medium text-slate-100">
        Forge your first MCP server
      </h2>
      <p className="mt-1 max-w-md text-sm text-slate-400">
        Paste an OpenAPI spec. We map every operation to a tool, generate a full
        server from audited templates, and let you test it live before you
        download.
      </p>
      <button onClick={onCreate} className="btn-primary mt-6">
        + New server
      </button>
    </div>
  );
}
