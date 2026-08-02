import { Link, useLocation } from "react-router-dom";
import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { PublicConfig } from "../types";

export default function Layout({ children }: { children: React.ReactNode }) {
  const [cfg, setCfg] = useState<PublicConfig | null>(null);
  const loc = useLocation();

  useEffect(() => {
    api.config().then(setCfg).catch(() => setCfg(null));
  }, []);

  return (
    <div className="min-h-full">
      <header className="sticky top-0 z-20 border-b border-line bg-ink-950/80 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-5 py-3">
          <Link to="/" className="flex items-center gap-2.5">
            <ForgeMark />
            <div className="leading-none">
              <div className="font-semibold tracking-tight text-slate-100">
                MCP <span className="text-forge-500">Forge</span>
              </div>
              <div className="mt-0.5 text-[10px] uppercase tracking-widest text-slate-500">
                servers without the expertise
              </div>
            </div>
          </Link>

          <div className="flex items-center gap-3 text-xs">
            {cfg && (
              <span
                className="badge border-line bg-ink-800 text-slate-400"
                title="Model used only to polish tool descriptions; generation is deterministic."
              >
                <span
                  className={
                    "h-1.5 w-1.5 rounded-full " +
                    (cfg.llm_enabled ? "bg-emerald-400" : "bg-slate-500")
                  }
                />
                {cfg.llm_enabled ? `LLM: ${cfg.llm_model || cfg.llm_provider}` : "Template-only"}
              </span>
            )}
            {loc.pathname !== "/new" && (
              <Link to="/new" className="btn-primary">
                + New server
              </Link>
            )}
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-5 py-8">{children}</main>

      <footer className="mx-auto max-w-6xl px-5 pb-10 pt-4 text-center text-xs text-slate-600">
        OpenAPI spec → tested MCP server → download. Auth, transport & error
        handling from audited templates.
      </footer>
    </div>
  );
}

function ForgeMark() {
  return (
    <svg width="30" height="30" viewBox="0 0 32 32" fill="none" aria-hidden>
      <rect width="32" height="32" rx="8" fill="#0e1017" stroke="#242a3a" />
      {/* anvil */}
      <path
        d="M9 18h14l-2 3H11l-2-3Z"
        fill="#3a4157"
      />
      <rect x="14" y="21" width="4" height="3" rx="1" fill="#3a4157" />
      {/* spark */}
      <path
        d="M17 7l-3 6h3l-2 5 6-7h-3l2-4h-3Z"
        fill="#f59e0b"
      />
    </svg>
  );
}
