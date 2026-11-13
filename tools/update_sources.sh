#!/usr/bin/env bash
# Update the local Cangjie/Luna source dicts from the pacman packages,
# then regenerate the flypy/lisp dictionaries.
#
# The merge is additive: upstream entries win, but entries that exist only
# locally (PUA / compatibility ideographs) are kept. Local header overrides
# such as `use_preset_vocabulary: false` are preserved.
#
# Usage: tools/update_sources.sh [--dry-run]
# The pacman hook calls it without arguments.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SYSTEM="/usr/share/rime-data"
DRY_RUN=0
[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=1

SOURCE_DICTS=(
  cangjie5.dict.yaml
  luna_pinyin.dict.yaml
)
PASSTHROUGH_FILES=(
  cangjie5.schema.yaml
)

for file in "${SOURCE_DICTS[@]}" "${PASSTHROUGH_FILES[@]}"; do
  if [[ ! -f "$SYSTEM/$file" ]]; then
    echo "[rime-sources] missing $SYSTEM/$file" >&2
    exit 1
  fi
done

merge_one() {
  local file="$1" out="$2"
  python3 "$ROOT/tools/merge_source_dict.py" \
    "$ROOT/$file" "$SYSTEM/$file" "$out" "$ROOT/tools/dict_overrides.tsv"
}

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

changed=0
for file in "${SOURCE_DICTS[@]}"; do
  merge_one "$file" "$TMP_DIR/$file"
  if cmp -s "$ROOT/$file" "$TMP_DIR/$file"; then
    echo "[rime-sources] $file: unchanged"
    continue
  fi
  changed=1
  if [[ "$DRY_RUN" == "1" ]]; then
    echo "[rime-sources] $file: would change"
    diff -u "$ROOT/$file" "$TMP_DIR/$file" | head -30 || true
  fi
done

for file in "${PASSTHROUGH_FILES[@]}"; do
  if cmp -s "$ROOT/$file" "$SYSTEM/$file"; then
    echo "[rime-sources] $file: unchanged"
    continue
  fi
  changed=1
  if [[ "$DRY_RUN" == "1" ]]; then
    echo "[rime-sources] $file: differs from $SYSTEM/$file"
    diff -u "$ROOT/$file" "$SYSTEM/$file" | head -30 || true
  fi
done

if [[ "$DRY_RUN" == "1" ]]; then
  exit 0
fi

if [[ "$changed" == "0" ]]; then
  echo "[rime-sources] sources already up to date; regenerating tables"
else
  for file in "${SOURCE_DICTS[@]}"; do
    merge_one "$file" "$TMP_DIR/$file"
    cp "$TMP_DIR/$file" "$ROOT/$file"
  done

  # Schema files are copied only when the local copy is still pristine;
  # local edits are never overwritten.
  for file in "${PASSTHROUGH_FILES[@]}"; do
    local_file="$ROOT/$file"
    if [[ -f "$local_file" ]] && ! cmp -s "$local_file" "$SYSTEM/$file"; then
      if git -C "$ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1 &&
        git -C "$ROOT" diff --quiet -- "$file"; then
        cp "$SYSTEM/$file" "$local_file"
      else
        echo "[rime-sources] $file: local edits, not overwritten" >&2
      fi
    else
      cp "$SYSTEM/$file" "$local_file"
    fi
  done
fi

cd "$ROOT"
python3 tools/generate_flypy_quick5.py
python3 tools/generate_flypy_quick5_phrases.py
python3 tools/generate_lisp_quick5.py
python3 tools/generate_lisp_quick5_phrases.py

echo "[rime-sources] updated source dicts and regenerated flypy/lisp tables"

if git -C "$ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  git -C "$ROOT" diff --stat || true
fi

echo "[rime-sources] review and commit, then redeploy Rime"
