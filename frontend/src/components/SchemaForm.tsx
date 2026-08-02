import type { JsonSchemaProp, McpTool } from "../types";

export type ArgValues = Record<string, unknown>;

/** Build a form from the JSON schema the running MCP server advertises. */
export default function SchemaForm({
  tool,
  values,
  onChange,
}: {
  tool: McpTool;
  values: ArgValues;
  onChange: (v: ArgValues) => void;
}) {
  const props = tool.input_schema?.properties ?? {};
  const required = new Set(tool.input_schema?.required ?? []);
  const names = Object.keys(props);

  if (names.length === 0) {
    return <p className="text-sm text-slate-500">This tool takes no parameters.</p>;
  }

  return (
    <div className="space-y-4">
      {names.map((name) => (
        <Field
          key={name}
          name={name}
          schema={props[name]}
          required={required.has(name)}
          value={values[name]}
          onChange={(v) => onChange({ ...values, [name]: v })}
        />
      ))}
    </div>
  );
}

/** MCP schemas often express optionals as anyOf[{type}, {type:'null'}]. */
function primitiveType(schema: JsonSchemaProp): string {
  if (schema.anyOf?.length) {
    const first = schema.anyOf.find((s) => s.type && s.type !== "null");
    if (first?.type) return first.type;
  }
  if (Array.isArray(schema.type)) {
    return schema.type.find((t) => t !== "null") ?? "string";
  }
  return schema.type ?? "string";
}

function Field({
  name,
  schema,
  required,
  value,
  onChange,
}: {
  name: string;
  schema: JsonSchemaProp;
  required: boolean;
  value: unknown;
  onChange: (v: unknown) => void;
}) {
  const type = primitiveType(schema ?? {});
  const label = (
    <label className="label mb-1 flex items-center gap-2 normal-case tracking-normal">
      <span className="font-mono text-xs text-slate-200">{name}</span>
      <span className="text-[10px] uppercase text-slate-500">{type}</span>
      {required && <span className="text-[10px] text-forge-400">required</span>}
    </label>
  );

  if (type === "object" || type === "array") {
    return (
      <div>
        {label}
        <textarea
          className="input h-32 resize-y font-mono text-xs"
          placeholder={type === "array" ? "[]" : "{}"}
          value={
            typeof value === "string"
              ? value
              : value !== undefined
                ? JSON.stringify(value, null, 2)
                : ""
          }
          onChange={(e) => onChange(parseMaybeJson(e.target.value))}
        />
        {schema?.description && (
          <p className="mt-1 text-xs text-slate-500">{schema.description}</p>
        )}
      </div>
    );
  }

  if (type === "boolean") {
    return (
      <div>
        {label}
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
        {schema?.description && (
          <p className="mt-1 text-xs text-slate-500">{schema.description}</p>
        )}
      </div>
    );
  }

  const isNumber = type === "integer" || type === "number";
  return (
    <div>
      {label}
      <input
        className="input font-mono text-xs"
        type={isNumber ? "number" : "text"}
        value={value === undefined || value === null ? "" : String(value)}
        placeholder={schema?.description || type}
        onChange={(e) => {
          const raw = e.target.value;
          if (raw === "") return onChange(undefined);
          onChange(isNumber ? Number(raw) : raw);
        }}
      />
      {schema?.description && (
        <p className="mt-1 text-xs text-slate-500">{schema.description}</p>
      )}
    </div>
  );
}

function parseMaybeJson(text: string): unknown {
  if (text.trim() === "") return undefined;
  try {
    return JSON.parse(text);
  } catch {
    return text; // keep raw so the user can keep typing
  }
}
