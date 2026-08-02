import { useState } from "react";

export default function CodeViewer({
  content,
  filename,
}: {
  content: string;
  filename?: string;
}) {
  const [copied, setCopied] = useState(false);
  const lines = content.replace(/\n$/, "").split("\n");

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      /* clipboard may be blocked */
    }
  };

  return (
    <div className="overflow-hidden rounded-lg border border-line bg-ink-950">
      <div className="flex items-center justify-between border-b border-line bg-ink-900 px-3 py-1.5">
        <span className="font-mono text-xs text-slate-400">{filename}</span>
        <button
          onClick={copy}
          className="rounded px-2 py-0.5 text-xs text-slate-400 hover:bg-ink-700 hover:text-slate-200"
        >
          {copied ? "Copied" : "Copy"}
        </button>
      </div>
      <div className="max-h-[60vh] overflow-auto">
        <pre className="min-w-full font-mono text-[12.5px] leading-relaxed">
          <code className="block">
            {lines.map((line, i) => (
              <div key={i} className="flex">
                <span className="sticky left-0 select-none border-r border-line bg-ink-950 px-3 py-0 text-right text-slate-600">
                  {i + 1}
                </span>
                <span className="whitespace-pre px-4 text-slate-200">
                  {line || " "}
                </span>
              </div>
            ))}
          </code>
        </pre>
      </div>
    </div>
  );
}
