"""Live host / GPU / model telemetry for Shadow Mission Control."""

from __future__ import annotations

import json
import os
import platform
import socket
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

HOME = Path.home()
INFERENCE_HINTS = (
    "ollama",
    "llama",
    "vllm",
    "invoke",
    "comfy",
    "lmstudio",
    "lm-studio",
    "whisper",
    "chatterbox",
    "sf-tts",
    "stable-diffusion",
    "diffusers",
    "text-generation",
    "kobold",
    "exllama",
    "sglang",
    "triton",
    "gguf",
)
SKIP_FS = {
    "tmpfs",
    "devtmpfs",
    "squashfs",
    "overlay",
    "efivarfs",
    "proc",
    "sysfs",
    "cgroup",
    "cgroup2",
    "devpts",
    "securityfs",
    "pstore",
    "bpf",
    "tracefs",
    "debugfs",
    "hugetlbfs",
    "mqueue",
    "fusectl",
    "rpc_pipefs",
    "autofs",
    "binfmt_misc",
    "configfs",
    "nsfs",
}
SKIP_MOUNT_PREFIX = ("/snap", "/run", "/proc", "/sys", "/dev")
WATCH_SYSTEM = ("docker.service", "nvidia-persistenced.service")
WATCH_USER = ("ollama.service", "sf-tts.service")
SERVICE_KEEP = (
    "docker",
    "ollama",
    "invoke",
    "lmstudio",
    "lm-studio",
    "comfy",
    "opencut",
    "nvidia-persist",
    "sf-tts",
    "shadow-mission",
)


def _read(path: str | Path) -> str | None:
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def _run(cmd: list[str], timeout: float = 1.4) -> str | None:
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout


def _http_json(url: str, timeout: float = 0.35) -> Any | None:
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
        if not raw:
            return None
        return json.loads(raw.decode("utf-8", errors="replace"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError, ValueError):
        return None


def _http_ok(url: str, timeout: float = 0.35) -> bool:
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 500
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def _num(value: str | None) -> float | None:
    if value is None:
        return None
    text = value.strip().replace("%", "").replace("MiB", "").replace("W", "").replace("MHz", "")
    if text in {"", "[N/A]", "N/A", "[Not Supported]", "Not Supported"}:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _cpu_times() -> tuple[dict[str, tuple[int, int]], str]:
    text = _read("/proc/stat") or ""
    cores: dict[str, tuple[int, int]] = {}
    model = "CPU"
    for line in text.splitlines():
        if not line.startswith("cpu"):
            continue
        parts = line.split()
        if len(parts) < 5:
            continue
        nums = [int(x) for x in parts[1:8]]
        idle = nums[3] + (nums[4] if len(nums) > 4 else 0)
        total = sum(nums)
        cores[parts[0]] = (idle, total)
    info = _read("/proc/cpuinfo") or ""
    for line in info.splitlines():
        if line.startswith("model name"):
            model = line.split(":", 1)[1].strip()
            break
    return cores, model


def _freqs() -> tuple[dict[int, float], float | None]:
    freqs: dict[int, float] = {}
    max_mhz: float | None = None
    base = Path("/sys/devices/system/cpu")
    for entry in sorted(base.glob("cpu[0-9]*")):
        try:
            idx = int(entry.name[3:])
        except ValueError:
            continue
        cur = _read(entry / "cpufreq/scaling_cur_freq")
        if cur:
            freqs[idx] = int(cur.strip()) / 1000.0
        if max_mhz is None:
            raw_max = _read(entry / "cpufreq/cpuinfo_max_freq") or _read(entry / "cpufreq/scaling_max_freq")
            if raw_max:
                max_mhz = int(raw_max.strip()) / 1000.0
    return freqs, max_mhz


def _meminfo() -> dict[str, int]:
    out: dict[str, int] = {}
    text = _read("/proc/meminfo") or ""
    for line in text.splitlines():
        if ":" not in line:
            continue
        key, rest = line.split(":", 1)
        bits = rest.split()
        if not bits:
            continue
        try:
            out[key] = int(bits[0]) * 1024
        except ValueError:
            continue
    return out


def _diskstats() -> dict[str, tuple[int, int]]:
    text = _read("/proc/diskstats") or ""
    stats: dict[str, tuple[int, int]] = {}
    for line in text.splitlines():
        parts = line.split()
        if len(parts) < 14:
            continue
        name = parts[2]
        if name.startswith(("loop", "ram", "sr", "zram", "dm-")):
            continue
        if name.startswith("nvme") and "p" in name[4:]:
            continue
        if name[:2] in {"sd", "hd", "vd", "xd"} and name[-1].isdigit():
            continue
        try:
            rsect = int(parts[5])
            wsect = int(parts[9])
        except ValueError:
            continue
        if rsect == 0 and wsect == 0:
            continue
        stats[name] = (rsect * 512, wsect * 512)
    return stats


def _mounts() -> list[dict[str, Any]]:
    text = _read("/proc/mounts") or ""
    seen: set[str] = set()
    mounts: list[dict[str, Any]] = []
    for line in text.splitlines():
        parts = line.split()
        if len(parts) < 3:
            continue
        source, target, fstype = parts[0], parts[1], parts[2]
        if fstype in SKIP_FS:
            continue
        if not source.startswith("/dev"):
            continue
        if target.startswith(SKIP_MOUNT_PREFIX):
            continue
        if target in seen:
            continue
        seen.add(target)
        try:
            st = os.statvfs(target)
        except OSError:
            continue
        total = st.f_frsize * st.f_blocks
        free = st.f_frsize * st.f_bavail
        if total <= 0:
            continue
        mounts.append(
            {
                "target": target,
                "source": source,
                "fstype": fstype,
                "usedBytes": total - free,
                "totalBytes": total,
            }
        )
    mounts.sort(key=lambda m: m["target"])
    return mounts


def _netdev() -> dict[str, tuple[int, int]]:
    text = _read("/proc/net/dev") or ""
    stats: dict[str, tuple[int, int]] = {}
    for line in text.splitlines()[2:]:
        if ":" not in line:
            continue
        name, rest = line.split(":", 1)
        iface = name.strip()
        if iface.startswith(("lo", "veth", "br-", "tun", "tap", "virbr")):
            continue
        fields = rest.split()
        if len(fields) < 10:
            continue
        stats[iface] = (int(fields[0]), int(fields[8]))
    return stats


def _temps() -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    hwmon = Path("/sys/class/hwmon")
    if not hwmon.exists():
        return items
    for chip in sorted(hwmon.glob("hwmon*")):
        chip_name = (_read(chip / "name") or chip.name).strip()
        kind = "other"
        low = chip_name.lower()
        if "k10" in low or "coretemp" in low or "zenpower" in low or "cpu" in low:
            kind = "cpu"
        elif "nvme" in low or "drivetemp" in low or "hdd" in low:
            kind = "drive"
        elif "nvidia" in low or "gpu" in low:
            kind = "gpu"
        elif "iwl" in low or "wifi" in low:
            kind = "wifi"
        elif "acpitz" in low or "wmi" in low:
            kind = "board"
        for temp in sorted(chip.glob("temp*_input")):
            raw = _read(temp)
            if not raw:
                continue
            try:
                celsius = int(raw.strip()) / 1000.0
            except ValueError:
                continue
            if celsius <= 0 or celsius > 120:
                continue
            label = (_read(str(temp).replace("_input", "_label")) or "").strip()
            pretty = {
                "k10temp": "CPU (Tctl)",
                "nvme": "NVMe",
                "iwlwifi_1_2": "Wi-Fi",
                "gigabyte_wmi": "Board",
                "acpitz_0": "ACPI",
                "acpitz_1": "ACPI",
            }.get(chip_name, chip_name)
            if label and chip_name.startswith("nvme"):
                pretty = f"NVMe {label}"
            elif label and kind == "cpu":
                pretty = f"CPU ({label})"
            elif label and kind == "board" and "wmi" in low:
                pretty = f"Board {label}"
            items.append(
                {
                    "id": f"{chip.name}:{temp.name}",
                    "label": pretty,
                    "celsius": round(celsius, 1),
                    "kind": kind,
                }
            )
    return items


def _nvidia() -> dict[str, Any]:
    out = _run(
        [
            "nvidia-smi",
            "--query-gpu=name,utilization.gpu,utilization.memory,memory.used,memory.total,temperature.gpu,clocks.current.graphics,clocks.current.memory,power.draw,power.limit,fan.speed,pstate",
            "--format=csv,noheader,nounits",
        ]
    )
    if out is None:
        return {
            "gpu": {"available": False, "error": "nvidia-smi unavailable"},
            "vram": {"available": False, "usedMiB": None, "totalMiB": None},
            "processes": [],
        }
    line = out.strip().splitlines()[0] if out.strip() else ""
    cols = [c.strip() for c in line.split(",")]
    while len(cols) < 12:
        cols.append("")
    gpu = {
        "available": True,
        "name": cols[0] or "NVIDIA GPU",
        "util": _num(cols[1]),
        "memUtil": _num(cols[2]),
        "clockMhz": _num(cols[6]),
        "memClockMhz": _num(cols[7]),
        "powerW": _num(cols[8]),
        "powerLimitW": _num(cols[9]),
        "fanPct": _num(cols[10]),
        "tempC": _num(cols[5]),
        "pstate": cols[11] or None,
    }
    vram = {
        "available": True,
        "usedMiB": _num(cols[3]),
        "totalMiB": _num(cols[4]),
    }
    procs_raw = _run(
        [
            "nvidia-smi",
            "--query-compute-apps=pid,process_name,used_gpu_memory",
            "--format=csv,noheader,nounits",
        ]
    )
    processes: list[dict[str, Any]] = []
    if procs_raw:
        for row in procs_raw.splitlines():
            bits = [b.strip() for b in row.split(",")]
            if len(bits) < 3:
                continue
            try:
                pid = int(bits[0])
            except ValueError:
                continue
            cmdline = _read(f"/proc/{pid}/cmdline") or ""
            first = cmdline.split("\x00")[0].strip()
            comm = (_read(f"/proc/{pid}/comm") or "").strip()
            name = Path(first).name if first else (comm or Path(bits[1]).name or bits[1])
            mem = _num(bits[2]) or 0
            hay = bits[1].lower()
            inference = any(h in hay for h in INFERENCE_HINTS)
            processes.append(
                {
                    "pid": pid,
                    "name": name[:80],
                    "memMiB": mem,
                    "inference": inference,
                }
            )
    return {"gpu": gpu, "vram": vram, "processes": processes}


def _docker() -> dict[str, Any]:
    raw = _run(
        [
            "docker",
            "ps",
            "--format",
            "{{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}",
        ]
    )
    if raw is None:
        return {"available": False, "error": "docker unavailable", "containers": []}
    containers = []
    for line in raw.splitlines():
        parts = line.split("\t")
        while len(parts) < 4:
            parts.append("")
        containers.append(
            {
                "name": parts[0],
                "image": parts[1],
                "status": parts[2],
                "ports": parts[3],
            }
        )
    return {"available": True, "containers": containers}


def _systemctl_show(scope: str, unit: str) -> dict[str, Any] | None:
    cmd = ["systemctl", "show", unit, "--property=Id,ActiveState,SubState,Description", "--no-pager"]
    if scope == "user":
        cmd.insert(1, "--user")
    raw = _run(cmd, timeout=0.8)
    if raw is None:
        return None
    data = {"name": unit, "scope": scope, "active": "unknown", "sub": "", "description": unit}
    for line in raw.splitlines():
        if "=" not in line:
            continue
        key, val = line.split("=", 1)
        if key == "Id" and val:
            data["name"] = val
        elif key == "ActiveState":
            data["active"] = val
        elif key == "SubState":
            data["sub"] = val
        elif key == "Description":
            data["description"] = val
    if data["active"] == "unknown" and "not-found" in raw:
        return None
    return data


def _systemctl_list(scope: str, state: str) -> list[str]:
    cmd = ["systemctl", "list-units", "--type=service", f"--state={state}", "--no-pager", "--no-legend"]
    if scope == "user":
        cmd.insert(1, "--user")
    raw = _run(cmd, timeout=0.9)
    if not raw:
        return []
    names = []
    for line in raw.splitlines():
        for bit in line.split():
            name = bit.lstrip("●●")
            if name.endswith(".service"):
                names.append(name)
                break
    return names


def _services() -> list[dict[str, Any]]:
    found: dict[tuple[str, str], dict[str, Any]] = {}

    def add(scope: str, unit: str) -> None:
        key = (scope, unit)
        if key in found:
            return
        if "cursor" in unit or unit.endswith(".scope"):
            return
        info = _systemctl_show(scope, unit)
        if info:
            found[key] = info

    for unit in WATCH_SYSTEM:
        add("system", unit)
    for unit in WATCH_USER:
        add("user", unit)
    for scope in ("system", "user"):
        for unit in _systemctl_list(scope, "failed"):
            add(scope, unit)
        for unit in _systemctl_list(scope, "running"):
            low = unit.lower()
            if any(k in low for k in SERVICE_KEEP):
                add(scope, unit)
    items = list(found.values())
    rank = {"failed": 0, "activating": 1, "active": 2, "inactive": 3}
    items.sort(key=lambda s: (rank.get(s["active"], 9), s["scope"], s["name"]))
    return items[:24]


def _lmstudio_models() -> list[str]:
    names: list[str] = []
    roots = [
        HOME / ".lmstudio" / "hub" / "models",
        HOME / ".lmstudio" / "models",
        HOME / ".lmstudio" / ".internal" / "bundled-models",
    ]
    for root in roots:
        if not root.exists():
            continue
        for gguf in root.rglob("*.gguf"):
            names.append(gguf.stem)
    return sorted(set(names))


def _proc_match(needles: tuple[str, ...]) -> bool:
    proc = Path("/proc")
    try:
        entries = list(proc.iterdir())
    except OSError:
        return False
    for entry in entries:
        if not entry.name.isdigit():
            continue
        try:
            raw = (entry / "cmdline").read_bytes()
        except OSError:
            continue
        cmd = raw.replace(b"\x00", b" ").decode("utf-8", errors="ignore").lower()
        if any(n in cmd for n in needles):
            return True
    return False


def _models(gpu_procs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    runtimes: list[dict[str, Any]] = []

    ollama_ps = _http_json("http://127.0.0.1:11434/api/ps")
    ollama_tags = _http_json("http://127.0.0.1:11434/api/tags")
    ollama_up = ollama_ps is not None or ollama_tags is not None
    loaded = []
    if isinstance(ollama_ps, dict):
        loaded = [m.get("name") or m.get("model") for m in ollama_ps.get("models", []) if isinstance(m, dict)]
        loaded = [m for m in loaded if m]
    installed = []
    if isinstance(ollama_tags, dict):
        installed = [m.get("name") for m in ollama_tags.get("models", []) if isinstance(m, dict) and m.get("name")]
    runtimes.append(
        {
            "id": "ollama",
            "name": "Ollama",
            "status": "running" if loaded else ("idle" if ollama_up else "offline"),
            "endpoint": "127.0.0.1:11434",
            "detail": f"{len(installed)} installed" if installed else ("server up" if ollama_up else "not listening"),
            "models": loaded or installed[:6],
        }
    )

    lm_models = _lmstudio_models()
    lm_api = _http_json("http://127.0.0.1:1234/v1/models")
    lm_proc = _proc_match(("lm-studio", "lmstudio"))
    lm_loaded = []
    if isinstance(lm_api, dict):
        lm_loaded = [m.get("id") for m in lm_api.get("data", []) if isinstance(m, dict) and m.get("id")]
    lm_present = (HOME / ".lmstudio").exists()
    if lm_present or lm_proc or lm_api is not None:
        status = "running" if lm_loaded or lm_api is not None else ("idle" if lm_proc else ("installed" if lm_present else "offline"))
        runtimes.append(
            {
                "id": "lmstudio",
                "name": "LM Studio",
                "status": status,
                "endpoint": "127.0.0.1:1234",
                "detail": "local server" if lm_api is not None else ("app present" if lm_present else "offline"),
                "models": lm_loaded or lm_models[:6],
            }
        )

    invoke_root = HOME / "invokeai"
    invoke_up = _http_ok("http://127.0.0.1:9090/")
    invoke_proc = _proc_match(("invokeai", "invoke-ai", "invokeai-web"))
    if invoke_root.exists() or invoke_up or invoke_proc:
        runtimes.append(
            {
                "id": "invoke",
                "name": "Invoke AI",
                "status": "running" if invoke_up or invoke_proc else "installed",
                "endpoint": "127.0.0.1:9090",
                "detail": "web UI" if invoke_up else ("installed" if invoke_root.exists() else "offline"),
                "models": [],
            }
        )

    tts = _http_json("http://127.0.0.1:9130/health") or _http_json("http://127.0.0.1:9130/v1/models")
    tts_health = _http_json("http://127.0.0.1:9130/health")
    tts_models = _http_json("http://127.0.0.1:9130/v1/models")
    names = []
    if isinstance(tts_models, dict):
        names = [m.get("id") for m in tts_models.get("data", []) if isinstance(m, dict) and m.get("id")]
    loaded_flag = isinstance(tts_health, dict) and bool(tts_health.get("loaded"))
    if tts is not None or tts_health is not None:
        runtimes.append(
            {
                "id": "sf-tts",
                "name": "Shadowfetch Voice Studio",
                "status": "running" if loaded_flag or names else "idle",
                "endpoint": "127.0.0.1:9130",
                "detail": (tts_health or {}).get("device") if isinstance(tts_health, dict) else "Chatterbox",
                "models": names or (["chatterbox"] if loaded_flag else []),
            }
        )

    opencut = _http_ok("http://127.0.0.1:3000/")
    if opencut:
        runtimes.append(
            {
                "id": "opencut",
                "name": "OpenCut",
                "status": "running",
                "endpoint": "127.0.0.1:3000",
                "detail": "local editor",
                "models": [],
            }
        )

    extra = [p for p in gpu_procs if p.get("inference")]
    if extra:
        runtimes.append(
            {
                "id": "gpu-inference",
                "name": "GPU inference procs",
                "status": "running",
                "detail": f"{len(extra)} compute process(es)",
                "models": [f"{p['name']} #{p['pid']}" for p in extra[:8]],
            }
        )
    return runtimes


def _host() -> dict[str, Any]:
    uptime = 0.0
    raw = _read("/proc/uptime")
    if raw:
        try:
            uptime = float(raw.split()[0])
        except (ValueError, IndexError):
            uptime = 0.0
    return {
        "hostname": socket.gethostname(),
        "kernel": platform.release(),
        "uptimeSec": uptime,
    }


class Collector:
    def __init__(self) -> None:
        self._prev_cpu, _ = _cpu_times()
        self._prev_disk = _diskstats()
        self._prev_net = _netdev()
        self._prev_ts = time.time()
        self.snapshot: dict[str, Any] = {}
        self.sample()

    def _rates(self, prev: dict[str, tuple[int, int]], cur: dict[str, tuple[int, int]], dt: float) -> dict[str, tuple[float, float]]:
        out: dict[str, tuple[float, float]] = {}
        if dt <= 0:
            dt = 1.0
        for name, (a, b) in cur.items():
            pa, pb = prev.get(name, (a, b))
            out[name] = (max(0.0, (a - pa) / dt), max(0.0, (b - pb) / dt))
        return out

    def sample(self) -> dict[str, Any]:
        now = time.time()
        dt = max(0.2, now - self._prev_ts)
        cpu_now, model = _cpu_times()
        disk_now = _diskstats()
        net_now = _netdev()
        cpu_rates = self._rates(self._prev_cpu, cpu_now, dt)
        disk_rates = self._rates(self._prev_disk, disk_now, dt)
        net_rates = self._rates(self._prev_net, net_now, dt)

        def usage(key: str) -> float:
            if key not in cpu_now or key not in self._prev_cpu:
                return 0.0
            idle, total = cpu_now[key]
            pidle, ptotal = self._prev_cpu[key]
            dtot = total - ptotal
            didle = idle - pidle
            if dtot <= 0:
                return 0.0
            return max(0.0, min(100.0, (1.0 - didle / dtot) * 100.0))

        freqs, freq_max = _freqs()
        per_core = []
        for key in sorted(cpu_now, key=lambda k: (k != "cpu", k)):
            if key == "cpu":
                continue
            try:
                idx = int(key[3:])
            except ValueError:
                continue
            per_core.append(
                {
                    "id": idx,
                    "usage": round(usage(key), 1),
                    "freqMhz": round(freqs[idx], 0) if idx in freqs else None,
                }
            )

        mem = _meminfo()
        total = mem.get("MemTotal", 0)
        available = mem.get("MemAvailable", mem.get("MemFree", 0))
        swap_total = mem.get("SwapTotal", 0)
        swap_free = mem.get("SwapFree", 0)
        nv = _nvidia()
        temps = _temps()
        if nv["gpu"].get("available") and nv["gpu"].get("tempC") is not None:
            temps.insert(
                0,
                {
                    "id": "nvidia:gpu",
                    "label": "GPU",
                    "celsius": nv["gpu"]["tempC"],
                    "kind": "gpu",
                },
            )
        load = [0.0, 0.0, 0.0]
        load_raw = _read("/proc/loadavg")
        if load_raw:
            bits = load_raw.split()
            try:
                load = [float(bits[0]), float(bits[1]), float(bits[2])]
            except (ValueError, IndexError):
                pass

        used_mhz = None
        if freqs:
            used_mhz = sum(freqs.values()) / len(freqs)

        snap = {
            "ts": now,
            "host": _host(),
            "cpu": {
                "model": model,
                "cores": len(per_core),
                "usage": round(usage("cpu"), 1),
                "load": load,
                "freqMhz": round(used_mhz, 0) if used_mhz else None,
                "freqMaxMhz": round(freq_max, 0) if freq_max else None,
                "perCore": per_core,
                "available": True,
            },
            "gpu": nv["gpu"],
            "vram": nv["vram"],
            "ram": {
                "usedBytes": max(0, total - available),
                "availableBytes": available,
                "totalBytes": total,
                "swapUsedBytes": max(0, swap_total - swap_free),
                "swapTotalBytes": swap_total,
            },
            "disk": {
                "io": [
                    {"name": name, "readBps": rates[0], "writeBps": rates[1]}
                    for name, rates in sorted(disk_rates.items())
                ],
                "mounts": _mounts(),
            },
            "net": {
                "interfaces": [
                    {
                        "name": name,
                        "rxBps": rates[0],
                        "txBps": rates[1],
                        "rxBytes": net_now[name][0],
                        "txBytes": net_now[name][1],
                    }
                    for name, rates in sorted(net_rates.items())
                ]
            },
            "temps": {"items": temps},
            "gpuProcesses": nv["processes"],
            "docker": _docker(),
            "services": {"items": _services()},
        }
        snap["models"] = {"runtimes": _models(nv["processes"])}

        self._prev_cpu = cpu_now
        self._prev_disk = disk_now
        self._prev_net = net_now
        self._prev_ts = now
        self.snapshot = snap
        return snap
