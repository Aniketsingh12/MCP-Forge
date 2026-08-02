import { useState } from "react";
import type { PollingConfig, ProposedTool } from "../types";
import { cx, methodColor } from "../lib/utils";

/** Config for submit → poll → result APIs (image/video generation, exports…). */
function PollingFields({
  polling,
  onChange,
}: {
  polling: PollingConfig;
  onChange: (p: PollingConfig) => void;
}) {
  const set = (patch: Partial<PollingConfig>) => onChange({ ...polling, ...patch });
  const field = (
    label: string,
    value: string | number,
    onEdit: (v: string) => void,
    hint?: string
  ) => (
    <div>
      <label className="label mb-1 normal-case tracking-normal">{label}</label>
      <input
        className="input font-mono text-xs"
        value={value}
        placeholder={hint}
        onChange={(e) => onEdit(e.target.value)}
      />
    </div>
  );

  return (
    <div className="mt-3 rounded-lg border border-sky-900/40 bg-sky-950/10 p-3">
      <p className="mb-3 text-xs text-slate-400">
        The tool submits the job, then polls until it finishes and returns the
        final result — so the agent never has to run the loop itself.
      </p>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {field("Job id field (in submit response)", polling.id_field, (v) =>
          set({ id_field: v }), "id"
        )}
        {field("Status path", polling.status_path, (v) => set({ status_path: v }),
          "/jobs/{job_id}"
        )}
        {field("Status field", polling.status_field, (v) => set({ status_field: v }),
          "status"
        )}
        {field("Success values (comma-sep)", polling.success_values.join(", "), (v) =>
          set({ success_values: v.split(",").map((s) => s.trim()).filter(Boolean) })
        )}
        {field("Failure values (comma-sep)", polling.failure_values.join(", "), (v) =>
          set({ failure_values: v.split(",").map((s) => s.trim()).filter(Boolean) })
        )}
        <div className="grid grid-cols-2 gap-2">
          {field("Interval (s)", polling.interval_seconds, (v) =>
            set({ interval_seconds: Number(v) || 0 })
          )}
          {field("Max polls", polling.max_attempts, (v) =>
            set({ max_attempts: Number(v) || 0 })
          )}
        </div>
      </div>
      {!polling.status_path && (
        <p className="mt-2 text-xs text-amber-400">
          A status path is required — without it this tool falls back to a plain
          single request.
        </p>
      )}
    </div>
  );
}

export default function ToolEditor({
  tool,
  onChange,
}: {
  tool: ProposedTool;
  onChange: (t: ProposedTool) => void;
}) {
  const [open, setOpen] = useState(false);
  const set = (patch: Partial<ProposedTool>) => onChange({ ...tool, ...patch });

  return (
    <div
      className={cx(
        "card overflow-hidden transition-opacity",
        !tool.enabled && "opacity-45"
      )}
    >
      <div className="flex items-start gap-3 p-4">
        <input
          type="checkbox"
          checked={tool.enabled}
          onChange={(e) => set({ enabled: e.target.checked })}
          className="mt-1 accent-forge-500"
          title="Include this tool"
        />

        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span
              className={"badge font-mono " + methodColor(tool.method)}
            >
              {tool.method}
            </span>
            <input
              value={tool.name}
              onChange={(e) =>
                set({ name: e.target.value.replace(/[^0-9a-zA-Z_]/g, "_") })
              }
              className="rounded border border-transparent bg-transparent px-1 py-0.5 font-mono text-sm text-forge-300 hover:border-line focus:border-forge-500/60 focus:outline-none"
            />
            <span className="truncate font-mono text-xs text-slate-500">
              {tool.path}
            </span>
          </div>

          <textarea
            value={tool.description}
            onChange={(e) => set({ description: e.target.value })}
            rows={1}
            className="mt-2 w-full resize-y rounded border border-transparent bg-transparent px-1 py-0.5 text-sm text-slate-300 hover:border-line focus:border-forge-500/60 focus:outline-none"
            placeholder="Tool description (what an agent reads to decide when to call it)"
          />

          <div className="mt-2 flex flex-wrap items-center gap-4 text-xs">
            <button
              onClick={() => setOpen((o) => !o)}
              className="text-slate-400 hover:text-slate-200"
            >
              {open ? "▾" : "▸"} {tool.params.length} param
              {tool.params.length !== 1 ? "s" : ""}
            </button>
            <label className="flex cursor-pointer items-center gap-1.5 text-slate-400">
              <input
                type="checkbox"
                checked={tool.confirm_required}
                onChange={(e) => set({ confirm_required: e.target.checked })}
                className="accent-forge-500"
              />
              confirm-required
              {tool.confirm_required && (
                <span className="badge border-amber-800/60 bg-amber-950/40 text-amber-300">
                  write
                </span>
              )}
            </label>
            <label
              className="flex cursor-pointer items-center gap-1.5 text-slate-400"
              title="For submit → poll → result APIs: the tool waits for the job and returns the final result."
            >
              <input
                type="checkbox"
                checked={tool.polling.enabled}
                onChange={(e) =>
                  set({ polling: { ...tool.polling, enabled: e.target.checked } })
                }
                className="accent-forge-500"
              />
              long-running job
              {tool.polling.enabled && (
                <span className="badge border-sky-800/60 bg-sky-950/40 text-sky-300">
                  polls
                </span>
              )}
            </label>
          </div>

          {tool.polling.enabled && (
            <PollingFields
              polling={tool.polling}
              onChange={(polling) => set({ polling })}
            />
          )}

          {open && tool.params.length > 0 && (
            <div className="mt-3 overflow-hidden rounded-lg border border-line">
              <table className="w-full text-left text-xs">
                <thead className="bg-ink-800 text-slate-400">
                  <tr>
                    <th className="px-3 py-1.5 font-medium">Name</th>
                    <th className="px-3 py-1.5 font-medium">Type</th>
                    <th className="px-3 py-1.5 font-medium">In</th>
                    <th className="px-3 py-1.5 font-medium">Req</th>
                  </tr>
                </thead>
                <tbody className="font-mono text-slate-300">
                  {tool.params.map((p) => (
                    <tr key={p.name} className="border-t border-line">
                      <td className="px-3 py-1.5">{p.name}</td>
                      <td className="px-3 py-1.5 text-slate-400">{p.type}</td>
                      <td className="px-3 py-1.5 text-slate-500">{p.location}</td>
                      <td className="px-3 py-1.5">
                        {p.required ? (
                          <span className="text-forge-400">yes</span>
                        ) : (
                          <span className="text-slate-600">no</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
