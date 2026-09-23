# Install

## Requirements

- Linux
- Python 3.10+
- Node.js 18+ (first HUD build only)
- Optional: NVIDIA driver + `nvidia-smi`, Docker CLI, systemd

## One-shot

```bash
git clone https://github.com/Shadowfetchapps/shadow-mission-control.git
cd shadow-mission-control
chmod +x scripts/install-linux.sh scripts/shadow-mission-control
./scripts/install-linux.sh
```

The installer:

1. Writes `~/.local/bin/shadow-mission-control`
2. Builds `ui/dist` if it is missing
3. Installs the icon (SVG plus PNG sizes from `assets/icons`) and desktop entry under `~/.local/share`

Make sure `~/.local/bin` is on your `PATH`.

## Manual

```bash
cd ui && npm install && npm run build
python3 server/app.py --port 7420
```

Then open <http://127.0.0.1:7420>.

## Environment

| Variable | Meaning | Default |
| --- | --- | --- |
| `SMC_PORT` | Loopback port | `7420` |
| `SMC_HOST` | Bind host | `127.0.0.1` |
| `XDG_STATE_HOME` | Launcher state directory parent | `~/.local/state` |

`SMC_HOST` is rejected unless it is loopback.

## Uninstall

```bash
rm -f ~/.local/bin/shadow-mission-control
rm -f ~/.local/share/applications/shadow-mission-control.desktop
rm -f ~/.local/share/pixmaps/shadow-mission-control.png
rm -f ~/.local/share/icons/hicolor/scalable/apps/shadow-mission-control.svg
rm -f ~/.local/share/icons/hicolor/*/apps/shadow-mission-control.png
rm -rf ~/.local/state/shadow-mission-control
```

Remove the clone when you no longer want the source.

## GitHub social preview

`assets/social-preview.png` is a 1280×640 Open Graph image. GitHub does not pick it up from the repo automatically. A maintainer must upload it under **Settings → Social preview**.
