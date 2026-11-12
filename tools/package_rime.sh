#!/usr/bin/env bash
# Package only the files Rime needs.
#
# Usage: tools/package_rime.sh [OUT_DIR] [GRAM_DIR] [all|flypy|lisp]
#   OUT_DIR   default: <repo>/dist/rime-config
#   GRAM_DIR  directory holding zh-*.gram (default: repo root)
#   VARIANT   all (default), flypy, or lisp
#
# all   : every schema in the repo (lisp + flypy)
# flypy : common files + flypy_* schemas/dicts; schema_list = flypy_quick5
# lisp  : common files + lisp_* schemas/dicts; schema_list = lisp_quick5

set -euo pipefail
shopt -s nullglob

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="${1:-$ROOT/dist/rime-config}"
GRAM_DIR="${2:-$ROOT}"
VARIANT="${3:-all}"

case "$VARIANT" in
  all|flypy|lisp) ;;
  *)
    echo "unknown variant: $VARIANT (expected all, flypy, or lisp)" >&2
    exit 2
    ;;
esac

rm -rf "$OUT"
mkdir -p "$OUT"

copy_file() {
  local file="$1"
  [[ -f "$file" ]] && cp "$file" "$OUT/"
}

# Files both variants need at runtime.
for file in \
  essay.txt \
  grammar.yaml \
  rime.lua \
  LICENSE \
  cangjie5.dict.yaml \
  luna_pinyin.dict.yaml \
  latex.schema.yaml \
  latex.dict.yaml; do
  copy_file "$ROOT/$file"
done

[[ -d "$ROOT/lua" ]] && cp -a "$ROOT/lua" "$OUT/"

if [[ "$VARIANT" == "all" ]]; then
  for pattern in '*.schema.yaml' '*.dict.yaml' '*.custom.yaml'; do
    for file in "$ROOT"/$pattern; do
      cp "$file" "$OUT/"
    done
  done
else
  if [[ "$VARIANT" == "flypy" ]]; then
    schema="flypy_quick5"
    for file in \
      flypy_luna.schema.yaml \
      flypy_quick5.schema.yaml \
      flypy_quick5.custom.yaml \
      flypy_quick5.dict.yaml \
      flypy_quick5_phrases.dict.yaml \
      flypy_self.schema.yaml \
      flypy_self.dict.yaml; do
      copy_file "$ROOT/$file"
    done
  else
    schema="lisp_quick5"
    for file in \
      lisp.schema.yaml \
      lisp_quick5.schema.yaml \
      lisp_quick5.custom.yaml \
      lisp_quick5.dict.yaml \
      lisp_quick5_phrases.dict.yaml; do
      copy_file "$ROOT/$file"
    done
  fi

  # Keep the user's other custom settings, but restrict schema_list.
  awk -v sel="$schema" '
    /^  schema_list:/ {
      print
      print "    - schema: " sel
      skip = 1
      next
    }
    skip && /^  [^ ]/ { skip = 0 }
    skip && /^    - schema:/ { next }
    { print }
  ' "$ROOT/default.custom.yaml" > "$OUT/default.custom.yaml"
fi

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

case "$VARIANT" in
  all)
    [[ -s "$OUT/flypy_quick5.dict.yaml" && -s "$OUT/lisp_quick5.dict.yaml" ]] || {
      echo "all package is missing a schema dict" >&2
      exit 1
    }
    ;;
  flypy)
    [[ -s "$OUT/flypy_quick5.dict.yaml" ]] || exit 1
    [[ ! -e "$OUT/lisp_quick5.dict.yaml" ]] || {
      echo "flypy package unexpectedly contains lisp" >&2
      exit 1
    }
    ;;
  lisp)
    [[ -s "$OUT/lisp_quick5.dict.yaml" ]] || exit 1
    [[ ! -e "$OUT/flypy_quick5.dict.yaml" ]] || {
      echo "lisp package unexpectedly contains flypy" >&2
      exit 1
    }
    ;;
esac

echo "packaged [$VARIANT] $(find "$OUT" -type f | wc -l) files -> $OUT"
du -sh "$OUT"
find "$OUT" -maxdepth 1 -type f -printf '%f\n' | sort
