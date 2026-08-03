import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import ForgeDiagram from "../components/ForgeDiagram";

export default function Landing() {
  const [projectCount, setProjectCount] = useState<number | null>(null);

  useEffect(() => {
    api
      .listProjects()
      .then((p) => setProjectCount(p.length))
      .catch(() => setProjectCount(null));
  }, []);

  return (
    <div className="-mt-4">
      {/* ---------------- hero ---------------- */}
      <section className="text-center">
        <p className="font-mono text-xs uppercase tracking-[0.2em] text-forge-500">
          MCP server generator
        </p>
        <h1 className="mx-auto mt-4 max-w-3xl font-display text-4xl font-bold leading-[1.1] tracking-tight text-slate-50 sm:text-5xl">
          The missing piece between
          <br className="hidden sm:block" /> your agent and your API.
        </h1>
        <p className="mx-auto mt-5 max-w-xl text-base leading-relaxed text-slate-400">
          Point MCP Forge at an OpenAPI spec or a Python library. Review the
          tools it proposes, then get a server that's already been tested over
          the real protocol.
        </p>

        <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
          <Link to="/new" className="btn-primary px-5 py-2.5">
            Forge a server
          </Link>
          <Link to="/new?sample=1" className="btn-ghost px-5 py-2.5">
            Try the sample spec
          </Link>
        </div>

        {projectCount !== null && projectCount > 0 && (
          <Link
            to="/dashboard"
            className="mt-5 inline-block text-sm text-slate-500 transition-colors hover:text-forge-400"
          >
            {projectCount} server{projectCount === 1 ? "" : "s"} in your
            workspace →
          </Link>
        )}
      </section>

      {/* ---------------- signature: the forge line ---------------- */}
      <section className="mt-12 sm:mt-16" aria-labelledby="how-heading">
        <h2 id="how-heading" className="sr-only">
          How an MCP server connects an agent to an API
        </h2>
        <ForgeDiagram />
      </section>

      {/* ---------------- the pipeline ---------------- */}
      <section className="mt-14 border-t border-line pt-10">
        <ol className="grid gap-px overflow-hidden rounded-xl border border-line bg-line sm:grid-cols-2 lg:grid-cols-5">
          {STAGES.map((s, i) => (
            <li key={s.title} className="bg-ink-900/70 p-5">
              <span className="font-mono text-xs text-forge-500">
                {String(i + 1).padStart(2, "0")}
              </span>
              <h3 className="mt-2 font-display text-sm font-semibold text-slate-100">
                {s.title}
              </h3>
              <p className="mt-1.5 text-xs leading-relaxed text-slate-400">
                {s.body}
              </p>
            </li>
          ))}
        </ol>
      </section>

      {/* ---------------- what you actually get ---------------- */}
      <section className="mt-14 grid gap-8 lg:grid-cols-[1fr_1.1fr] lg:items-center">
        <div>
          <h2 className="font-display text-2xl font-bold tracking-tight text-slate-50">
            You download a package, not a snippet.
          </h2>
          <p className="mt-3 text-sm leading-relaxed text-slate-400">
            Auth injection, transport, and error normalization come from audited
            templates — only the tool set reflects your API. Write actions are
            gated behind a confirm flag by default.
          </p>
          <ul className="mt-5 space-y-2 text-sm text-slate-400">
            {GUARANTEES.map((g) => (
              <li key={g} className="flex items-start gap-2.5">
                <span aria-hidden className="mt-1.5 text-forge-500">
                  ▸
                </span>
                {g}
              </li>
            ))}
          </ul>
        </div>

        <div className="overflow-hidden rounded-xl border border-line bg-ink-950">
          <div className="border-b border-line bg-ink-900 px-4 py-2 font-mono text-xs text-slate-500">
            stripe_mcp.zip
          </div>
          <pre className="overflow-x-auto p-4 font-mono text-xs leading-relaxed text-slate-300">
            {TREE}
          </pre>
        </div>
      </section>

      {/* ---------------- close ---------------- */}
      <section className="mt-14 rounded-xl border border-line bg-ink-900/70 px-6 py-10 text-center">
        <h2 className="font-display text-xl font-bold tracking-tight text-slate-50">
          Start with a spec you already have.
        </h2>
        <p className="mx-auto mt-2 max-w-md text-sm text-slate-400">
          Generation is deterministic — no model required, no API key to
          configure.
        </p>
        <Link to="/new" className="btn-primary mt-6 px-5 py-2.5">
          Forge a server
        </Link>
      </section>
    </div>
  );
}

const STAGES = [
  {
    title: "Describe",
    body: "Paste an OpenAPI spec, link one, or name an installed Python library.",
  },
  {
    title: "Review",
    body: "Every operation becomes a candidate tool. Rename, drop, and flag write actions.",
  },
  {
    title: "Generate",
    body: "Templates fill in auth, transport, and error handling. A validator gates the output.",
  },
  {
    title: "Call it",
    body: "The playground launches your server and drives it over real MCP, not a simulation.",
  },
  {
    title: "Ship",
    body: "Download the package, or paste the config straight into an MCP client.",
  },
];

const GUARANTEES = [
  "Runs on stdio — works with Claude Desktop, Cursor, and any MCP client.",
  "Tests included, so you can prove the tool surface before you trust it.",
  "Long-running jobs poll to completion and return the finished result.",
];

const TREE = `stripe_mcp/
├── server.py                  6 tools, auth wired
├── pyproject.toml             pip-installable
├── requirements.txt
├── README.md                  usage + client config
├── tests/test_server.py       tool surface smoke test
└── claude_desktop_config.json`;
