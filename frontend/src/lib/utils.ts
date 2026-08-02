export function cx(...parts: Array<string | false | null | undefined>): string {
  return parts.filter(Boolean).join(" ");
}

export function methodColor(method: string): string {
  switch (method.toUpperCase()) {
    case "GET":
      return "border-emerald-800/60 bg-emerald-950/40 text-emerald-300";
    case "POST":
      return "border-sky-800/60 bg-sky-950/40 text-sky-300";
    case "PUT":
    case "PATCH":
      return "border-amber-800/60 bg-amber-950/40 text-amber-300";
    case "DELETE":
      return "border-red-800/60 bg-red-950/40 text-red-300";
    default:
      return "border-line bg-ink-800 text-slate-300";
  }
}

export function statusColor(status: string): string {
  switch (status) {
    case "draft":
      return "border-line bg-ink-800 text-slate-400";
    case "proposed":
      return "border-sky-800/60 bg-sky-950/40 text-sky-300";
    case "generated":
      return "border-forge-700/60 bg-forge-700/10 text-forge-400";
    case "tested":
      return "border-emerald-800/60 bg-emerald-950/40 text-emerald-300";
    default:
      return "border-line bg-ink-800 text-slate-400";
  }
}

export function timeAgo(iso: string): string {
  const then = new Date(iso).getTime();
  const secs = Math.max(1, Math.floor((Date.now() - then) / 1000));
  const units: [number, string][] = [
    [60, "s"],
    [60, "m"],
    [24, "h"],
    [365, "d"],
  ];
  let value = secs;
  let unit = "s";
  for (const [div, u] of units) {
    if (value < div) {
      unit = u;
      break;
    }
    value = Math.floor(value / div);
    unit = u;
  }
  return `${value}${unit} ago`;
}
