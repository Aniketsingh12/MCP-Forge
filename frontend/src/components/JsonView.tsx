export default function JsonView({ value }: { value: unknown }) {
  let text: string;
  try {
    text =
      typeof value === "string" ? value : JSON.stringify(value, null, 2);
  } catch {
    text = String(value);
  }
  return (
    <pre className="max-h-[50vh] overflow-auto rounded-lg border border-line bg-ink-950 p-3 font-mono text-[12.5px] leading-relaxed text-slate-200">
      {text}
    </pre>
  );
}
