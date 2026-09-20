from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "server"))

from collector import Collector, _host  # noqa: E402


def test_host_snapshot_has_no_username_field() -> None:
    host = _host()
    assert "user" not in host
    assert "kernel" in host
    assert "uptimeSec" in host


def test_sample_returns_expected_panels() -> None:
    snap = Collector().sample()
    for key in ("cpu", "gpu", "vram", "ram", "disk", "net", "temps", "models", "docker", "services"):
        assert key in snap
    assert "user" not in snap["host"]
    assert snap["gpu"].get("uuid") is None
