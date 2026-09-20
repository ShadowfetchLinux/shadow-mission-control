export type Core = { id: number; usage: number; freqMhz: number | null };

export type Runtime = {
  id: string;
  name: string;
  status: "running" | "idle" | "offline" | "installed";
  endpoint?: string;
  detail?: string;
  models: string[];
};

export type Snapshot = {
  ts: number;
  host: { hostname: string; kernel: string; uptimeSec: number };
  cpu: {
    model: string;
    cores: number;
    usage: number;
    load: number[];
    freqMhz: number | null;
    freqMaxMhz: number | null;
    perCore: Core[];
    available: boolean;
  };
  gpu: {
    available: boolean;
    error?: string;
    name?: string;
    util: number | null;
    memUtil: number | null;
    clockMhz: number | null;
    memClockMhz: number | null;
    powerW: number | null;
    powerLimitW: number | null;
    fanPct: number | null;
    tempC: number | null;
    pstate?: string | null;
  };
  vram: { available: boolean; usedMiB: number | null; totalMiB: number | null };
  ram: {
    usedBytes: number;
    availableBytes: number;
    totalBytes: number;
    swapUsedBytes: number;
    swapTotalBytes: number;
  };
  disk: {
    io: { name: string; readBps: number; writeBps: number }[];
    mounts: { target: string; source: string; fstype: string; usedBytes: number; totalBytes: number }[];
  };
  net: {
    interfaces: { name: string; rxBps: number; txBps: number; rxBytes: number; txBytes: number }[];
  };
  temps: { items: { id: string; label: string; celsius: number; kind: string }[] };
  models: { runtimes: Runtime[] };
  gpuProcesses: { pid: number; name: string; memMiB: number; inference: boolean }[];
  docker: {
    available: boolean;
    error?: string;
    containers: { name: string; image: string; status: string; ports: string }[];
  };
  services: {
    items: { name: string; scope: string; active: string; sub: string; description: string }[];
  };
};

export type History = {
  cpu: number[];
  gpu: number[];
  vram: number[];
  ram: number[];
  rx: number[];
  tx: number[];
};
