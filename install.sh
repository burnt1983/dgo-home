#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
SHARE="${HOME}/.local/share/dgo-home"
BIN="${HOME}/.local/bin"
APPS="${HOME}/.local/share/applications"
mkdir -p "$SHARE" "$BIN" "$APPS"
install -m 0755 "$ROOT/dgo_home.py" "$SHARE/dgo_home.py"
ln -sfn "$SHARE/dgo_home.py" "$BIN/dgo-home"
cat > "$APPS/dgo-home.desktop" <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=DGO Home
Comment=Home lights, plugs, and speaker
Exec=${BIN}/dgo-home
Terminal=false
Categories=Utility;
StartupNotify=true
StartupWMClass=dgo_home
EOF
echo "Installed."
echo "  Run: dgo-home"
echo "  It does not start at login."
