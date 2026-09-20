import { useEffect, useRef, useState } from "react";
import type { History, Snapshot } from "./types";

const EMPTY: History = { cpu: [], gpu: [], vram: [], ram: [], rx: [], tx: [] };
const MAX = 60;

function push(list: number[], value: number): number[] {
  const next = list.length >= MAX ? list.slice(list.length - MAX + 1) : list.slice();
  next.push(value);
  return next;
}

export function useMetrics() {
  const [snap, setSnap] = useState<Snapshot | null>(null);
  const [history, setHistory] = useState<History>(EMPTY);
  const [live, setLive] = useState(false);
  const hist = useRef<History>(EMPTY);

  useEffect(() => {
    let stop = false;
    let es: EventSource | null = null;
    let poll: number | undefined;

    const apply = (data: Snapshot) => {
      if (stop) return;
      setSnap(data);
      const vramPct =
        data.vram.usedMiB && data.vram.totalMiB ? (data.vram.usedMiB / data.vram.totalMiB) * 100 : 0;
      const ramPct = data.ram.totalBytes ? (data.ram.usedBytes / data.ram.totalBytes) * 100 : 0;
      const rx = data.net.interfaces.reduce((a, i) => a + i.rxBps, 0);
      const tx = data.net.interfaces.reduce((a, i) => a + i.txBps, 0);
      hist.current = {
        cpu: push(hist.current.cpu, data.cpu.usage),
        gpu: push(hist.current.gpu, data.gpu.util ?? 0),
        vram: push(hist.current.vram, vramPct),
        ram: push(hist.current.ram, ramPct),
        rx: push(hist.current.rx, rx),
        tx: push(hist.current.tx, tx),
      };
      setHistory({ ...hist.current });
      setLive(true);
    };

    const startPoll = () => {
      const tick = () => {
        fetch("/api/metrics")
          .then((r) => r.json())
          .then(apply)
          .catch(() => setLive(false));
      };
      tick();
      poll = window.setInterval(tick, 2000);
    };

    try {
      es = new EventSource("/api/stream");
      es.onmessage = (ev) => {
        try {
          apply(JSON.parse(ev.data) as Snapshot);
        } catch {
          /* ignore bad frames */
        }
      };
      es.onerror = () => {
        es?.close();
        es = null;
        if (!poll) startPoll();
      };
    } catch {
      startPoll();
    }

    const watchdog = window.setTimeout(() => {
      if (!hist.current.cpu.length) startPoll();
    }, 2500);

    return () => {
      stop = true;
      es?.close();
      if (poll) window.clearInterval(poll);
      window.clearTimeout(watchdog);
    };
  }, []);

  return { snap, history, live };
}
