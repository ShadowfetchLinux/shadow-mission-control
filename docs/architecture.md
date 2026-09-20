# Architecture

```
launcher (scripts/shadow-mission-control)
    │
    ├─ python3 server/app.py          loopback HTTP
    │     ├─ /api/health
    │     ├─ /api/metrics             one JSON snapshot
    │     ├─ /api/stream              SSE, 1 Hz
    │     └─ /                        Vite-built HUD from ui/dist
    │
    └─ Chromium --app or xdg-open
```

## Collector

`server/collector.py` samples host metrics every second on a daemon thread.

- CPU / RAM / disk / net / temps come from `/proc` and sysfs.
- GPU comes from `nvidia-smi` when present. GPU UUIDs are not queried.
- Model runtimes are detected by local HTTP health checks and process names.
- Docker and systemd are optional. Failures stay in-panel.

Snapshots stay in memory. The HUD never writes metrics to disk.

## UI

`ui/` is Vite + React. `useMetrics` prefers `EventSource /api/stream` and falls back to polling `/api/metrics`.

## Isolation

The HTTP server refuses non-loopback binds. There is no remote configuration, no auth provider, and no phone-home URL.
