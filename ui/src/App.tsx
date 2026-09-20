import { Card, Gauge, Meter, Spark, chipClass, fmtBytes, fmtRate, fmtUptime } from "./widgets";
import { useMetrics } from "./useMetrics";

function heat(c: number): string {
  if (c >= 85) return "var(--danger)";
  if (c >= 70) return "var(--warning)";
  return "var(--info)";
}

export default function App() {
  const { snap, history, live } = useMetrics();
  if (!snap) {
    return (
      <div className="boot">
        <div className="boot-mark" />
        <p>ACQUIRING TELEMETRY</p>
      </div>
    );
  }

  const ramPct = snap.ram.totalBytes ? (snap.ram.usedBytes / snap.ram.totalBytes) * 100 : 0;
  const vramPct =
    snap.vram.usedMiB != null && snap.vram.totalMiB ? (snap.vram.usedMiB / snap.vram.totalMiB) * 100 : 0;
  const swapPct = snap.ram.swapTotalBytes
    ? (snap.ram.swapUsedBytes / snap.ram.swapTotalBytes) * 100
    : 0;
  const clock = new Date(snap.ts * 1000).toLocaleTimeString();

  return (
    <div className="hud">
      <header className="top">
        <div className="brand">
          <span className="mark" aria-hidden />
          <div>
            <p className="kicker">SHADOWFETCH</p>
            <h1>Mission Control</h1>
          </div>
        </div>
        <div className="meta">
          <span>{snap.host.hostname}</span>
          <span>up {fmtUptime(snap.host.uptimeSec)}</span>
          <span>{snap.host.kernel}</span>
        </div>
        <div className={`live ${live ? "on" : ""}`}>
          <i />
          {live ? "LIVE" : "HOLD"}
          <em>{clock}</em>
        </div>
      </header>

      <div className="grid">
        <Card title="CPU" source="/proc/stat · cpufreq · loadavg">
          <div className="row">
            <Gauge value={snap.cpu.usage} label="%" color="var(--accent)" />
            <div className="stack">
              <p className="model">{snap.cpu.model}</p>
              <p className="kv">
                <b>{snap.cpu.cores}</b> cores
                <span>
                  {snap.cpu.freqMhz ? `${Math.round(snap.cpu.freqMhz)} MHz` : "—"}
                  {snap.cpu.freqMaxMhz ? ` / ${Math.round(snap.cpu.freqMaxMhz)}` : ""}
                </span>
              </p>
              <p className="kv">
                load <b>{snap.cpu.load.map((n) => n.toFixed(2)).join("  ")}</b>
              </p>
              <Spark values={history.cpu} color="#b9b1ff" />
            </div>
          </div>
          <div className="cores">
            {snap.cpu.perCore.map((c) => (
              <div key={c.id} className="core" title={`cpu${c.id} ${c.usage}%`}>
                <Meter value={c.usage} color={c.usage > 85 ? "var(--danger)" : "var(--accent)"} />
              </div>
            ))}
          </div>
        </Card>

        <Card title="GPU" source="nvidia-smi query-gpu">
          {snap.gpu.available ? (
            <>
              <div className="row">
                <Gauge value={snap.gpu.util ?? 0} label="util" color="var(--info)" />
                <div className="stack">
                  <p className="model">{snap.gpu.name}</p>
                  <p className="kv">
                    gfx <b>{snap.gpu.clockMhz ? `${Math.round(snap.gpu.clockMhz)} MHz` : "—"}</b>
                    <span>mem {snap.gpu.memClockMhz ? `${Math.round(snap.gpu.memClockMhz)}` : "—"}</span>
                  </p>
                  <p className="kv">
                    {snap.gpu.powerW != null ? `${snap.gpu.powerW.toFixed(0)} W` : "—"}
                    {snap.gpu.powerLimitW != null ? ` / ${snap.gpu.powerLimitW.toFixed(0)} W` : ""}
                    <span>fan {snap.gpu.fanPct != null ? `${snap.gpu.fanPct}%` : "—"}</span>
                    <span>{snap.gpu.pstate || ""}</span>
                  </p>
                  <Spark values={history.gpu} color="#6ad7ef" />
                </div>
              </div>
            </>
          ) : (
            <p className="empty">{snap.gpu.error || "NVIDIA telemetry unavailable"}</p>
          )}
        </Card>

        <Card title="VRAM" source="nvidia-smi memory.used/total">
          {snap.vram.available ? (
            <>
              <div className="row">
                <Gauge value={vramPct} label="used" color="var(--warning)" />
                <div className="stack">
                  <p className="big">
                    {snap.vram.usedMiB != null ? Math.round(snap.vram.usedMiB) : "—"}
                    <small> / {snap.vram.totalMiB != null ? Math.round(snap.vram.totalMiB) : "—"} MiB</small>
                  </p>
                  <Meter value={vramPct} color="var(--warning)" />
                  <Spark values={history.vram} color="#f5c86b" />
                </div>
              </div>
            </>
          ) : (
            <p className="empty">No VRAM data</p>
          )}
        </Card>

        <Card title="RAM" source="/proc/meminfo">
          <div className="row">
            <Gauge value={ramPct} label="used" color="var(--ok)" />
            <div className="stack">
              <p className="big">
                {fmtBytes(snap.ram.usedBytes)}
                <small> / {fmtBytes(snap.ram.totalBytes)}</small>
              </p>
              <p className="kv">avail {fmtBytes(snap.ram.availableBytes)}</p>
              <p className="kv">
                swap {fmtBytes(snap.ram.swapUsedBytes)} / {fmtBytes(snap.ram.swapTotalBytes)}
              </p>
              <Meter value={swapPct} color="var(--danger)" />
              <Spark values={history.ram} color="#3ddc84" />
            </div>
          </div>
        </Card>

        <Card title="Temperatures" source="hwmon + nvidia-smi">
          <ul className="list">
            {snap.temps.items.length === 0 && <li className="empty">No sensors</li>}
            {snap.temps.items.map((t) => (
              <li key={t.id}>
                <span>{t.label}</span>
                <b style={{ color: heat(t.celsius) }}>{t.celsius.toFixed(1)}°C</b>
              </li>
            ))}
          </ul>
        </Card>

        <Card title="Disk" source="/proc/diskstats · statvfs mounts" wide>
          <div className="split">
            <div>
              <p className="sub">I/O</p>
              <ul className="list">
                {snap.disk.io.length === 0 && <li className="empty">No disk counters</li>}
                {snap.disk.io.map((d) => (
                  <li key={d.name}>
                    <span>{d.name}</span>
                    <em>
                      ↓ {fmtRate(d.readBps)} · ↑ {fmtRate(d.writeBps)}
                    </em>
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <p className="sub">Capacity</p>
              <ul className="list">
                {snap.disk.mounts.map((m) => {
                  const pct = m.totalBytes ? (m.usedBytes / m.totalBytes) * 100 : 0;
                  return (
                    <li key={m.target} className="mount">
                      <div>
                        <span>{m.target}</span>
                        <em>
                          {fmtBytes(m.usedBytes)} / {fmtBytes(m.totalBytes)}
                        </em>
                      </div>
                      <Meter value={pct} color={pct > 90 ? "var(--danger)" : "var(--info)"} />
                    </li>
                  );
                })}
              </ul>
            </div>
          </div>
        </Card>

        <Card title="Network" source="/proc/net/dev">
          <ul className="list">
            {snap.net.interfaces.map((n) => (
              <li key={n.name}>
                <span>{n.name}</span>
                <em>
                  rx {fmtRate(n.rxBps)} · tx {fmtRate(n.txBps)}
                </em>
              </li>
            ))}
          </ul>
          <div className="sparks">
            <Spark values={history.rx} color="#3ddc84" />
            <Spark values={history.tx} color="#ff6b7a" />
          </div>
        </Card>

        <Card title="AI models" source="Ollama · LM Studio · Invoke · local TTS · GPU procs" wide>
          <ul className="runtimes">
            {snap.models.runtimes.map((r) => (
              <li key={r.id}>
                <div className="rt-top">
                  <b>{r.name}</b>
                  <span className={chipClass(r.status)}>{r.status}</span>
                  {r.endpoint && <code>{r.endpoint}</code>}
                </div>
                <p>{r.detail}</p>
                {r.models.length > 0 && <p className="mods">{r.models.join(" · ")}</p>}
              </li>
            ))}
          </ul>
        </Card>

        <Card title="GPU processes" source="nvidia-smi compute apps">
          <ul className="list tight">
            {snap.gpuProcesses.length === 0 && <li className="empty">No compute processes</li>}
            {snap.gpuProcesses.map((p) => (
              <li key={p.pid}>
                <span>
                  {p.inference && <i className="dot" />}
                  {p.name}
                  <small> #{p.pid}</small>
                </span>
                <em>{Math.round(p.memMiB)} MiB</em>
              </li>
            ))}
          </ul>
        </Card>

        <Card title="Docker" source="docker ps">
          {!snap.docker.available ? (
            <p className="empty">{snap.docker.error || "Docker unavailable"}</p>
          ) : (
            <ul className="list tight">
              {snap.docker.containers.length === 0 && <li className="empty">No running containers</li>}
              {snap.docker.containers.map((c) => (
                <li key={c.name}>
                  <span>
                    {c.name}
                    <small> {c.image}</small>
                  </span>
                  <em>{c.status}</em>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card title="Services" source="systemctl user+system (curated)" wide>
          <ul className="list tight cols">
            {snap.services.items.map((s) => (
              <li key={`${s.scope}:${s.name}`}>
                <span>
                  <span className={chipClass(s.active)}>{s.active}</span>
                  {s.name}
                  <small> {s.scope}</small>
                </span>
                <em>{s.sub}</em>
              </li>
            ))}
          </ul>
        </Card>
      </div>
    </div>
  );
}
