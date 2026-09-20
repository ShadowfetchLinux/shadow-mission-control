"""Fail if tracked files contain machine or personal markers."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {
    ".git",
    "node_modules",
    "dist",
    "__pycache__",
    ".pytest_cache",
    ".venv",
    "venv",
}
SKIP_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".woff", ".woff2"}
PATTERNS = (
    re.compile(r"/home/[A-Za-z0-9._-]+"),
    re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}"),
    re.compile(r"\b(?:ssh-rsa|ssh-ed25519|BEGIN (?:RSA |OPENSSH )?PRIVATE KEY)\b"),
)


def test_repo_has_no_personal_or_machine_markers() -> None:
    hits: list[str] = []
    for path in ROOT.rglob("*"):
        if any(part in SKIP_DIRS or part == "tests" for part in path.parts):
            continue
        if not path.is_file() or path.suffix.lower() in SKIP_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for pattern in PATTERNS:
            for match in pattern.finditer(text):
                rel = path.relative_to(ROOT)
                hits.append(f"{rel}: {match.group(0)}")
    assert hits == [], "Personal or machine markers found:\n" + "\n".join(hits)


def test_desktop_file_has_no_absolute_home() -> None:
    desktop = (ROOT / "packaging" / "shadow-mission-control.desktop").read_text(encoding="utf-8")
    assert "/home/" not in desktop
    assert "Exec=shadow-mission-control" in desktop
