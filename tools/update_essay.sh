#!/usr/bin/env bash
# Regenerate essay.txt (Taiwan-first) from the upstream rime-essay, with a
# fallback to the pacman copy when the network is unavailable.
#
# Usage: tools/update_essay.sh [--source auto|upstream|system] [--dry-run]
#
#   auto      try upstream, fall back to /usr/share/rime-data/essay.txt (default)
#   upstream  require the download to succeed
#   system    use the pacman copy only
#
# The pacman hook calls it without arguments, so a failed download never
# blocks a package upgrade.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SYSTEM_ESSAY="/usr/share/rime-data/essay.txt"
URL="${RIME_ESSAY_URL:-https://raw.githubusercontent.com/rime/rime-essay/master/essay.txt}"
SOURCE="auto"
DRY_RUN=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --source)
      SOURCE="${2:-}"
      shift 2
      ;;
    --source=*)
      SOURCE="${1#*=}"
      shift
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    *)
      echo "usage: tools/update_essay.sh [--source auto|upstream|system] [--dry-run]" >&2
      exit 2
      ;;
  esac
done

case "$SOURCE" in
  auto|upstream|system) ;;
  *)
    echo "[essay] unknown source: $SOURCE (expected auto, upstream, or system)" >&2
    exit 2
    ;;
esac

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

# Avoid two hooks competing for the same output.
exec 9>"${TMPDIR:-/tmp}/rime-essay-tw.lock"
if ! flock -n 9; then
  echo "[essay] another run is in progress; skipping"
  exit 0
fi

valid_essay() {
  local file="$1"
  [[ -s "$file" ]] || return 1
  [[ "$(wc -c <"$file")" -ge 1000000 ]] || return 1
  awk -F'\t' '
    NF != 2 || $2 !~ /^[0-9]+(\.[0-9]+)?$/ { bad++ }
    END { exit (bad > 0 || NR < 300000) ? 1 : 0 }
  ' "$file"
}

ESSAY=""
if [[ "$SOURCE" != "system" ]]; then
  echo "[essay] fetching upstream: $URL"
  if curl -fsSL --connect-timeout 10 --max-time 60 --retry 3 --retry-delay 2 \
    -o "$TMP_DIR/upstream.txt" "$URL" && valid_essay "$TMP_DIR/upstream.txt"; then
    ESSAY="$TMP_DIR/upstream.txt"
    echo "[essay] source: upstream ($(wc -l <"$ESSAY") entries)"
  else
    echo "[essay] upstream unavailable or invalid" >&2
    if [[ "$SOURCE" == "upstream" ]]; then
      exit 1
    fi
  fi
fi

if [[ -z "$ESSAY" ]]; then
  if [[ ! -s "$SYSTEM_ESSAY" ]]; then
    echo "[essay] missing $SYSTEM_ESSAY" >&2
    exit 1
  fi
  ESSAY="$SYSTEM_ESSAY"
  echo "[essay] source: pacman ($(wc -l <"$ESSAY") entries)"
fi

if [[ "$DRY_RUN" == "1" ]]; then
  echo "[essay] dry run; essay.txt not written"
  exit 0
fi

if [[ "$ESSAY" == "$TMP_DIR/upstream.txt" ]]; then
  ESSAY_LABEL="upstream:$URL"
else
  ESSAY_LABEL="system:$SYSTEM_ESSAY"
fi

python3 "$ROOT/tools/generate_essay.py" \
  --essay "$ESSAY" \
  --pairs "$ROOT/tools/essay_pairs.tsv" \
  --out "$TMP_DIR/essay.txt" \
  --report "$TMP_DIR/essay_report.txt"

# Keep the report reproducible: replace the temp path with a stable label.
python3 - "$TMP_DIR/essay_report.txt" "$ESSAY_LABEL" <<'PY'
import sys

path, label = sys.argv[1], sys.argv[2]
with open(path, encoding="utf-8") as fh:
    lines = fh.readlines()
lines[0] = f"essay: {label}\n"
with open(path, "w", encoding="utf-8") as fh:
    fh.writelines(lines)
PY

mv "$TMP_DIR/essay.txt" "$ROOT/essay.txt"
mv "$TMP_DIR/essay_report.txt" "$ROOT/tools/essay_report.txt"

echo "[essay] wrote $ROOT/essay.txt"
echo "[essay] redeploy Rime to apply (fcitx5: restart or 選單「部署」)"
