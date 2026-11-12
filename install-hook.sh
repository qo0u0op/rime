#!/usr/bin/env bash
# Install or remove the rime-essay-tw pacman hook (run as root).

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN="/usr/local/bin/rime-essay-tw"
HOOK="/etc/pacman.d/hooks/91-rime-essay-tw.hook"

if [[ "${1:-}" == "--uninstall" ]]; then
  rm -f "$BIN" "$HOOK"
  echo "removed $BIN and $HOOK"
  exit 0
fi

install -Dm755 "$HERE/rime-essay-tw" "$BIN"
install -Dm644 "$HERE/91-rime-essay-tw.hook" "$HOOK"
echo "installed $BIN and $HOOK"
echo "the hook runs after rime-essay is installed or upgraded"
