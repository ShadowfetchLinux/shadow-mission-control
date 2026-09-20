#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PREFIX="${XDG_DATA_HOME:-$HOME/.local/share}"
BIN="${HOME}/.local/bin"

mkdir -p "$BIN"
cat >"$BIN/shadow-mission-control" <<EOF
#!/usr/bin/env bash
exec "${ROOT}/scripts/shadow-mission-control" "\$@"
EOF
chmod +x "$BIN/shadow-mission-control" "$ROOT/scripts/shadow-mission-control"

if [[ ! -d "${ROOT}/ui/dist" ]]; then
  (cd "$ROOT/ui" && npm install --no-fund --no-audit && npm run build)
fi

ICON_SRC="$ROOT/assets/shadow-mission-control.svg"
mkdir -p "$PREFIX/icons/hicolor/scalable/apps"
cp "$ICON_SRC" "$PREFIX/icons/hicolor/scalable/apps/shadow-mission-control.svg"

if command -v rsvg-convert >/dev/null 2>&1; then
  for size in 16 22 24 32 48 64 128 256 512; do
    dest="$PREFIX/icons/hicolor/${size}x${size}/apps"
    mkdir -p "$dest"
    rsvg-convert -w "$size" -h "$size" "$ICON_SRC" -o "$dest/shadow-mission-control.png"
  done
fi

mkdir -p "$PREFIX/applications"
sed "s|^Exec=.*|Exec=${BIN}/shadow-mission-control|; s|^TryExec=.*|TryExec=${BIN}/shadow-mission-control|" \
  "$ROOT/packaging/shadow-mission-control.desktop" > "$PREFIX/applications/shadow-mission-control.desktop"

if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database "$PREFIX/applications" >/dev/null 2>&1 || true
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
  gtk-update-icon-cache -q "$PREFIX/icons/hicolor" >/dev/null 2>&1 || true
fi

echo "Installed shadow-mission-control → ${BIN}/shadow-mission-control"
echo "Desktop entry → ${PREFIX}/applications/shadow-mission-control.desktop"
echo "Add ${BIN} to PATH if the command is not found."
