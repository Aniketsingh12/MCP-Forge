import { Link } from "react-router-dom";
import { cx } from "../lib/utils";

const STEPS = [
  { key: "input", label: "Input" },
  { key: "proposal", label: "Tools" },
  { key: "generate", label: "Generate" },
  { key: "playground", label: "Playground" },
  { key: "export", label: "Export" },
] as const;

type StepKey = (typeof STEPS)[number]["key"];

export default function Stepper({
  current,
  projectId,
  reached,
}: {
  current: StepKey;
  projectId?: string;
  reached: StepKey[];
}) {
  const currentIndex = STEPS.findIndex((s) => s.key === current);

  return (
    <nav className="mb-8 flex items-center gap-1 overflow-x-auto">
      {STEPS.map((step, i) => {
        const done = i < currentIndex;
        const active = step.key === current;
        const canLink =
          projectId && (reached.includes(step.key) || done) && !active;
        const to =
          step.key === "input"
            ? "/new"
            : `/p/${projectId}/${step.key === "proposal" ? "proposal" : step.key}`;

        const content = (
          <div
            className={cx(
              "flex items-center gap-2 whitespace-nowrap rounded-lg px-3 py-1.5 text-sm transition-colors",
              active && "bg-forge-500/10 text-forge-400 ring-1 ring-forge-500/30",
              !active && done && "text-slate-300",
              !active && !done && "text-slate-500"
            )}
          >
            <span
              className={cx(
                "flex h-5 w-5 items-center justify-center rounded-full text-[11px] font-semibold",
                active && "bg-forge-500 text-ink-950",
                !active && done && "bg-emerald-500/20 text-emerald-300",
                !active && !done && "bg-ink-700 text-slate-500"
              )}
            >
              {done ? "✓" : i + 1}
            </span>
            {step.label}
          </div>
        );

        return (
          <div key={step.key} className="flex items-center">
            {canLink ? <Link to={to}>{content}</Link> : content}
            {i < STEPS.length - 1 && (
              <div className="mx-1 h-px w-5 bg-line" aria-hidden />
            )}
          </div>
        );
      })}
    </nav>
  );
}
