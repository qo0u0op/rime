#!/usr/bin/env bash
# Sync the Cangjie/Luna source files from the pacman packages, then
# regenerate the flypy/lisp dictionaries.
#
# Relationship with the system files:
#   cangjie5.dict.yaml, cangjie5.schema.yaml  copied as-is from /usr/share/rime-data
#   luna_pinyin.dict.yaml                    merged + tools/dict_overrides.tsv
#
# The Luna merge is additive (upstream wins, local-only non-PUA entries are
# kept, obsolete local PUA entries are dropped) and the overrides file is the
# only local dictionary edit, because *.custom.yaml cannot patch .dict.yaml.
#
# Usage: tools/update_sources.sh [--dry-run]
# The pacman hook calls it without arguments.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SYSTEM="/usr/share/rime-data"
DRY_RUN=0
[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=1

COPIED_FILES=(
  cangjie5.dict.yaml
  cangjie5.schema.yaml
)
MERGED_FILES=(
  luna_pinyin.dict.yaml
)

for file in "${COPIED_FILES[@]}" "${MERGED_FILES[@]}"; do
  if [[ ! -f "$SYSTEM/$file" ]]; then
    echo "[rime-sources] missing $SYSTEM/$file" >&2
    exit 1
  fi
done

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

merge_one() {
  local file="$1" out="$2"
  python3 "$ROOT/tools/merge_source_dict.py" \
    "$ROOT/$file" "$SYSTEM/$file" "$out" "$ROOT/tools/dict_overrides.tsv"
}

for file in "${MERGED_FILES[@]}"; do
  merge_one "$file" "$TMP_DIR/$file"
  if cmp -s "$ROOT/$file" "$TMP_DIR/$file"; then
    echo "[rime-sources] $file: unchanged"
    continue
  fi
  if [[ "$DRY_RUN" == "1" ]]; then
    echo "[rime-sources] $file: would change"
    diff -u "$ROOT/$file" "$TMP_DIR/$file" | head -40 || true
  fi
done

for file in "${COPIED_FILES[@]}"; do
  if cmp -s "$ROOT/$file" "$SYSTEM/$file"; then
    echo "[rime-sources] $file: unchanged"
    continue
  fi
  if [[ "$DRY_RUN" == "1" ]]; then
    echo "[rime-sources] $file: would be replaced by $SYSTEM/$file"
    diff -u "$ROOT/$file" "$SYSTEM/$file" | head -40 || true
  fi
done

if [[ "$DRY_RUN" == "1" ]]; then
  exit 0
fi

for file in "${MERGED_FILES[@]}"; do
  merge_one "$file" "$TMP_DIR/$file"
  cp "$TMP_DIR/$file" "$ROOT/$file"
done

for file in "${COPIED_FILES[@]}"; do
  cp "$SYSTEM/$file" "$ROOT/$file"
done

cd "$ROOT"
python3 tools/generate_flypy_quick5.py
python3 tools/generate_flypy_quick5_phrases.py
python3 tools/generate_lisp_quick5.py
python3 tools/generate_lisp_quick5_phrases.py

echo "[rime-sources] synced sources and regenerated flypy/lisp tables"

if git -C "$ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  git -C "$ROOT" diff --stat || true
fi

echo "[rime-sources] review and commit, then redeploy Rime"
