import type { CSSProperties } from "react";

export function Card({
  title,
  source,
  children,
  wide,
}: {
  title: string;
  source: string;
  children: React.ReactNode;
  wide?: boolean;
}) {
  return (
    <section className={wide ? "card card-wide" : "card"}>
      <header className="card-head">
        <h2>{title}</h2>
        <span className="src" title={source}>
          {source}
        </span>
      </header>
      {children}
    </section>
  );
}

export function Gauge({
  value,
  label,
  color = "var(--accent)",
}: {
  value: number;
  label: string;
  color?: string;
}) {
  const pct = Math.max(0, Math.min(100, value));
  const r = 34;
  const c = 2 * Math.PI * r;
  const dash = (pct / 100) * c;
  return (
    <div className="gauge">
      <svg viewBox="0 0 88 88" width="88" height="88">
        <circle cx="44" cy="44" r={r} className="g-track" />
        <circle
          cx="44"
          cy="44"
          r={r}
          className="g-arc"
          style={{ stroke: color, strokeDasharray: `${dash} ${c}` } as CSSProperties}
        />
      </svg>
      <div className="g-read">
        <strong>{pct.toFixed(0)}</strong>
        <em>{label}</em>
      </div>
    </div>
  );
}

export function Spark({
  values,
  color = "#6ad7ef",
}: {
  values: number[];
  color?: string;
}) {
  const w = 140;
  const h = 36;
  if (values.length < 2) return <svg className="spark" width={w} height={h} />;
  const max = Math.max(...values, 1);
  const min = Math.min(...values, 0);
  const span = Math.max(1, max - min);
  const pts = values
    .map((v, i) => {
      const x = (i / (values.length - 1)) * (w - 2) + 1;
      const y = h - 3 - ((v - min) / span) * (h - 8);
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
  return (
    <svg className="spark" width={w} height={h} viewBox={`0 0 ${w} ${h}`}>
      <polyline points={pts} fill="none" stroke={color} strokeWidth="1.6" strokeLinejoin="round" />
    </svg>
  );
}

export function Meter({
  value,
  color = "var(--accent)",
}: {
  value: number;
  color?: string;
}) {
  const pct = Math.max(0, Math.min(100, value));
  return (
    <div className="meter">
      <i style={{ width: `${pct}%`, background: color }} />
    </div>
  );
}

export function fmtBytes(n: number): string {
  if (!Number.isFinite(n) || n < 0) return "—";
  const units = ["B", "KiB", "MiB", "GiB", "TiB"];
  let v = n;
  let i = 0;
  while (v >= 1024 && i < units.length - 1) {
    v /= 1024;
    i += 1;
  }
  return `${v >= 10 || i === 0 ? v.toFixed(0) : v.toFixed(1)} ${units[i]}`;
}

export function fmtRate(n: number): string {
  return `${fmtBytes(n)}/s`;
}

export function fmtUptime(sec: number): string {
  const s = Math.floor(sec);
  const d = Math.floor(s / 86400);
  const h = Math.floor((s % 86400) / 3600);
  const m = Math.floor((s % 3600) / 60);
  if (d) return `${d}d ${h}h`;
  if (h) return `${h}h ${m}m`;
  return `${m}m`;
}

export function chipClass(status: string): string {
  if (status === "running" || status === "active") return "chip ok";
  if (status === "failed") return "chip bad";
  if (status === "idle" || status === "installed") return "chip warn";
  return "chip dim";
}
