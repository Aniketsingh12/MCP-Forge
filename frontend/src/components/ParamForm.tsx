import type { ProposedTool, ToolParam } from "../types";

export type ArgValues = Record<string, unknown>;

export default function ParamForm({
  tool,
  values,
  onChange,
}: {
  tool: ProposedTool;
  values: ArgValues;
  onChange: (v: ArgValues) => void;
}) {
  const set = (name: string, value: unknown) =>
    onChange({ ...values, [name]: value });

  if (tool.params.length === 0) {
    return (
      <p className="text-sm text-slate-500">
        This tool takes no parameters.
      </p>
    );
  }

  return (
    <div className="space-y-4">
      {tool.params.map((p) => (
        <Field key={p.name} param={p} value={values[p.name]} onChange={(v) => set(p.name, v)} />
      ))}
    </div>
  );
}

function Field({
  param,
  value,
  onChange,
}: {
  param: ToolParam;
  value: unknown;
  onChange: (v: unknown) => void;
}) {
  const labelEl = (
    <label className="label mb-1 flex items-center gap-2 normal-case tracking-normal">
      <span className="font-mono text-xs text-slate-200">{param.name}</span>
      <span className="text-[10px] uppercase text-slate-500">{param.location}</span>
      {param.required && <span className="text-[10px] text-forge-400">required</span>}
    </label>
  );

  if (param.location === "body" || param.type === "object" || param.type === "array") {
    return (
      <div>
        {labelEl}
        <textarea
          className="input h-32 resize-y font-mono text-xs"
          placeholder={param.type === "array" ? "[]" : "{}"}
          value={typeof value === "string" ? value : value ? JSON.stringify(value, null, 2) : ""}
          onChange={(e) => onChange(parseMaybeJson(e.target.value))}
        />
        {param.description && (
          <p className="mt-1 text-xs text-slate-500">{param.description}</p>
        )}
      </div>
    );
  }

  if (param.type === "boolean") {
    return (
      <div>
        {labelEl}
        <select
          className="input"
          value={value === undefined ? "" : String(value)}
          onChange={(e) =>
            onChange(e.target.value === "" ? undefined : e.target.value === "true")
          }
        >
          <option value="">—</option>
          <option value="true">true</option>
          <option value="false">false</option>
        </select>
      </div>
    );
  }

  const isNumber = param.type === "integer" || param.type === "number";
  return (
    <div>
      {labelEl}
      <input
        className="input font-mono text-xs"
        type={isNumber ? "number" : "text"}
        value={value === undefined || value === null ? "" : String(value)}
        placeholder={param.description || param.type}
        onChange={(e) => {
          const raw = e.target.value;
          if (raw === "") return onChange(undefined);
          onChange(isNumber ? Number(raw) : raw);
        }}
      />
      {param.description && (
        <p className="mt-1 text-xs text-slate-500">{param.description}</p>
      )}
    </div>
  );
}

function parseMaybeJson(text: string): unknown {
  if (text.trim() === "") return undefined;
  try {
    return JSON.parse(text);
  } catch {
    // keep raw string so the user can keep typing; backend will receive it
    return text;
  }
}
