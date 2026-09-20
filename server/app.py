#!/usr/bin/env python3
"""Shadow Mission Control — localhost metrics API + static HUD."""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
UI_DIR = ROOT / "ui" / "dist"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 7420

if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from collector import Collector  # noqa: E402

collector = Collector()
_stop = threading.Event()
BIND_HOST = DEFAULT_HOST
BIND_PORT = DEFAULT_PORT


def _sampler() -> None:
    while not _stop.wait(1.0):
        try:
            collector.sample()
        except Exception:
            continue


class Handler(BaseHTTPRequestHandler):
    server_version = "ShadowMissionControl/1.0"

    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write("%s - %s\n" % (self.log_date_time_string(), fmt % args))

    def _cors(self) -> None:
        origin = self.headers.get("Origin", "")
        allowed = {
            f"http://127.0.0.1:{BIND_PORT}",
            f"http://localhost:{BIND_PORT}",
        }
        if origin in allowed:
            self.send_header("Access-Control-Allow-Origin", origin)
        self.send_header("Cache-Control", "no-store")

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(204)
        self._cors()
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/api/health":
            return self._json({"ok": True, "ts": time.time(), "port": BIND_PORT})
        if path == "/api/metrics":
            return self._json(collector.snapshot or collector.sample())
        if path == "/api/stream":
            return self._sse()
        return self._static(path)

    def _json(self, payload: object, status: int = 200) -> None:
        body = json.dumps(payload, default=str).encode("utf-8")
        self.send_response(status)
        self._cors()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _sse(self) -> None:
        self.send_response(200)
        self._cors()
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Connection", "keep-alive")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()
        try:
            while True:
                payload = json.dumps(collector.snapshot or {}, default=str)
                self.wfile.write(f"data: {payload}\n\n".encode("utf-8"))
                self.wfile.flush()
                time.sleep(1.0)
        except (BrokenPipeError, ConnectionResetError, OSError):
            return

    def _static(self, path: str) -> None:
        if not UI_DIR.is_dir():
            return self._json(
                {"error": "UI not built. Run: cd ui && npm install && npm run build"},
                503,
            )
        rel = "index.html" if path in {"", "/"} else path.lstrip("/")
        dest = (UI_DIR / rel).resolve()
        root = UI_DIR.resolve()
        if not str(dest).startswith(str(root)):
            self.send_error(403)
            return
        if dest.is_dir():
            dest = dest / "index.html"
        if not dest.is_file():
            dest = root / "index.html"
        if not dest.is_file():
            self.send_error(404)
            return
        data = dest.read_bytes()
        ctype = mimetypes.guess_type(str(dest))[0] or "application/octet-stream"
        self.send_response(200)
        self._cors()
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Shadow Mission Control local HUD server")
    parser.add_argument("--host", default=os.environ.get("SMC_HOST", DEFAULT_HOST))
    parser.add_argument("--port", type=int, default=int(os.environ.get("SMC_PORT", DEFAULT_PORT)))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    global BIND_HOST, BIND_PORT
    args = parse_args(argv)
    BIND_HOST = args.host
    BIND_PORT = args.port
    if BIND_HOST not in {"127.0.0.1", "localhost", "::1"}:
        print("Refusing to bind beyond loopback. Use 127.0.0.1, localhost, or ::1.", file=sys.stderr)
        raise SystemExit(2)
    thread = threading.Thread(target=_sampler, name="smc-sampler", daemon=True)
    thread.start()
    httpd = ThreadingHTTPServer((BIND_HOST, BIND_PORT), Handler)
    print(f"Shadow Mission Control  http://{BIND_HOST}:{BIND_PORT}", flush=True)
    try:
        httpd.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        pass
    finally:
        _stop.set()
        httpd.server_close()


if __name__ == "__main__":
    main()
