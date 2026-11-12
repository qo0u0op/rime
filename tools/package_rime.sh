#!/usr/bin/env bash
# Package only the files Rime needs into a directory (or a CI artifact).
#
# Usage: tools/package_rime.sh [OUT_DIR] [GRAM_DIR]
#   OUT_DIR   default: <repo>/dist/rime-config
#   GRAM_DIR  directory holding zh-*.gram (default: repo root)

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="${1:-$ROOT/dist/rime-config}"
GRAM_DIR="${2:-$ROOT}"

rm -rf "$OUT"
mkdir -p "$OUT"

copy_file() {
  local file="$1"
  [[ -f "$file" ]] && cp "$file" "$OUT/"
}

copy_file "$ROOT/essay.txt"
copy_file "$ROOT/grammar.yaml"
copy_file "$ROOT/rime.lua"
copy_file "$ROOT/LICENSE"

shopt -s nullglob
for pattern in '*.schema.yaml' '*.dict.yaml' '*.custom.yaml'; do
  for file in "$ROOT"/$pattern; do
    cp "$file" "$OUT/"
  done
done

[[ -d "$ROOT/lua" ]] && cp -a "$ROOT/lua" "$OUT/"

if [[ -d "$GRAM_DIR" ]]; then
  for file in "$GRAM_DIR"/*.gram; do
    cp "$file" "$OUT/"
  done
fi

for required in zh-hant-t-essay-bgw.gram zh-hant-t-essay-bgc.gram; do
  if [[ ! -s "$OUT/$required" ]]; then
    echo "missing required grammar model: $required" >&2
    exit 1
  fi
done

echo "packaged $(find "$OUT" -type f | wc -l) files -> $OUT"
du -sh "$OUT"
find "$OUT" -maxdepth 1 -type f -printf '%f\n' | sort
