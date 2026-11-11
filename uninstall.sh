#!/usr/bin/env bash
set -euo pipefail
rm -f \
  "${HOME}/.local/bin/dgo-home" \
  "${HOME}/.local/share/applications/dgo-home.desktop"
rm -rf "${HOME}/.local/share/dgo-home"
echo "Removed the program. Saved settings under ~/.config were left in place."
