from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "server"))

from app import parse_args  # noqa: E402
import app as app_mod  # noqa: E402


def test_parse_args_defaults_to_loopback() -> None:
    args = parse_args([])
    assert args.host == "127.0.0.1"
    assert args.port == 7420


def test_refuses_non_loopback_bind() -> None:
    try:
        app_mod.main(["--host", "0.0.0.0"])
    except SystemExit as exc:
        assert exc.code == 2
    else:
        raise AssertionError("expected SystemExit for non-loopback bind")
