"""Icon assets, desktop entry, HUD favicons, and installer wiring."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SIZES = (16, 22, 24, 32, 48, 64, 96, 128, 256, 512)


def test_brand_assets_exist() -> None:
    assert (ROOT / "assets" / "shadow-mission-control.svg").is_file()
    assert (ROOT / "assets" / "shadow-mission-control.png").is_file()
    for size in SIZES:
        png = ROOT / "assets" / "icons" / f"{size}x{size}" / "shadow-mission-control.png"
        assert png.is_file(), f"missing {png.relative_to(ROOT)}"


def test_desktop_file_uses_icon_name() -> None:
    desktop = (ROOT / "packaging" / "shadow-mission-control.desktop").read_text(encoding="utf-8")
    assert "Icon=shadow-mission-control" in desktop
    assert "StartupWMClass=shadow-mission-control" in desktop


def test_hud_public_favicons_exist() -> None:
    public = ROOT / "ui" / "public"
    for name in (
        "icon.svg",
        "favicon.ico",
        "favicon-32.png",
        "favicon-48.png",
        "apple-touch-icon.png",
    ):
        assert (public / name).is_file(), f"missing ui/public/{name}"


def test_hud_html_references_favicons() -> None:
    html = (ROOT / "ui" / "index.html").read_text(encoding="utf-8")
    assert 'href="./favicon.ico"' in html
    assert 'href="./favicon-32.png"' in html
    assert 'href="./icon.svg"' in html
    assert 'href="./apple-touch-icon.png"' in html


def test_readme_shows_icon() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "assets/icons/128x128/shadow-mission-control.png" in readme


def test_installer_copies_prebuilt_pngs_without_rsvg() -> None:
    script = (ROOT / "scripts" / "install-linux.sh").read_text(encoding="utf-8")
    assert 'prebuilt="$ICON_DIR/${size}x${size}/shadow-mission-control.png"' in script
    assert 'if [[ -f "$prebuilt" ]]; then' in script
    assert "elif command -v rsvg-convert" in script
    assert "$PREFIX/pixmaps" in script
    sizes = script.split("for size in", 1)[1].split(";", 1)[0]
    for size in SIZES:
        assert str(size) in sizes
