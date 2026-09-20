# Security

Shadow Mission Control is a local workstation HUD.

## Network

- The HTTP server refuses to bind anything except loopback (`127.0.0.1`, `localhost`, or `::1`).
- There are no outbound product analytics, crash reporters, or update pings.
- Optional local probes (Ollama, LM Studio, Invoke, Docker) use `127.0.0.1` only.

## Data

- The published source does not contain home paths, usernames, emails, tokens, or GPU UUIDs.
- Live snapshots stay in memory. They are not written to disk by the server.
- Browser profile data created by the launcher lives under `~/.local/state/shadow-mission-control/` on the machine that runs it.

## What the HUD can see

Anything a local user can already see with `/proc`, `nvidia-smi`, `docker ps`, and `systemctl`. Treat the loopback HTTP port like any other local service: do not proxy it to the public internet.

## Reporting

Open a GitHub issue on this repository for security reports that do not include secrets. Do not attach logs that contain private host data.
