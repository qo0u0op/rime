#!/usr/bin/env bash
# Package only the files Rime needs.
#
# Usage: tools/package_rime.sh [OUT_DIR] [all|flypy|lisp] [desktop|mobile]
#   OUT_DIR   default: <repo>/dist/rime-config
#   VARIANT   all (default), flypy, or lisp
#   PLATFORM  desktop (default) or mobile
#
# The octagram .gram models are NOT bundled; install them separately from
# https://github.com/lotem/rime-octagram-data
#
# desktop : keeps latex + cangjie_comment switch
# mobile  : overlays tools/mobile/*.custom.yaml (no latex, no extended_charset/ascii_punct),
#           adds trime.custom.yaml / hamster.app.yaml / cangjie5.schema.yaml,
#           and drops latex.schema.yaml / latex.dict.yaml

set -euo pipefail
shopt -s nullglob

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="${1:-$ROOT/dist/rime-config}"
VARIANT="${2:-all}"
PLATFORM="${3:-desktop}"

case "$VARIANT" in
  all|flypy|lisp) ;;
  *)
    echo "unknown variant: $VARIANT (expected all, flypy, or lisp)" >&2
    exit 2
    ;;
esac

case "$PLATFORM" in
  desktop|mobile) ;;
  *)
    echo "unknown platform: $PLATFORM (expected desktop or mobile)" >&2
    exit 2
    ;;
esac

rm -rf "$OUT"
mkdir -p "$OUT"

copy_file() {
  local file="$1"
  [[ -f "$file" ]] && cp "$file" "$OUT/"
}

# Files every package needs.
for file in \
  essay.txt \
  grammar.yaml \
  rime.lua \
  LICENSE \
  cangjie5.dict.yaml \
  luna_pinyin.dict.yaml \
  default.custom.yaml; do
  copy_file "$ROOT/$file"
done

[[ -d "$ROOT/lua" ]] && cp -a "$ROOT/lua" "$OUT/"

# Platform-only files.
if [[ "$PLATFORM" == "desktop" ]]; then
  copy_file "$ROOT/latex.schema.yaml"
  copy_file "$ROOT/latex.dict.yaml"
else
  copy_file "$ROOT/trime.custom.yaml"
  copy_file "$ROOT/hamster.app.yaml"
  copy_file "$ROOT/cangjie5.schema.yaml"
fi

# Scheme files.
if [[ "$VARIANT" == "all" ]]; then
  for pattern in '*.schema.yaml' '*.dict.yaml' '*.custom.yaml'; do
    for file in "$ROOT"/$pattern; do
      cp "$file" "$OUT/"
    done
  done
else
  if [[ "$VARIANT" == "flypy" ]]; then
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
    for file in \
      lisp.schema.yaml \
      lisp_quick5.schema.yaml \
      lisp_quick5.custom.yaml \
      lisp_quick5.dict.yaml \
      lisp_quick5_phrases.dict.yaml; do
      copy_file "$ROOT/$file"
    done
  fi
fi

# Platform adjustments after the glob copy.
if [[ "$PLATFORM" == "mobile" ]]; then
  rm -f "$OUT/latex.schema.yaml" "$OUT/latex.dict.yaml"
  if [[ -f "$ROOT/tools/mobile/flypy_quick5.custom.yaml" ]]; then
    if [[ "$VARIANT" == "all" || "$VARIANT" == "flypy" ]]; then
      cp "$ROOT/tools/mobile/flypy_quick5.custom.yaml" "$OUT/"
    fi
  fi
  if [[ -f "$ROOT/tools/mobile/lisp_quick5.custom.yaml" ]]; then
    if [[ "$VARIANT" == "all" || "$VARIANT" == "lisp" ]]; then
      cp "$ROOT/tools/mobile/lisp_quick5.custom.yaml" "$OUT/"
    fi
  fi
else
  rm -f "$OUT/trime.custom.yaml" "$OUT/hamster.app.yaml" "$OUT/cangjie5.schema.yaml"
fi

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

if [[ "$PLATFORM" == "desktop" ]]; then
  [[ -s "$OUT/latex.schema.yaml" ]] || { echo "desktop package missing latex" >&2; exit 1; }
  [[ ! -e "$OUT/trime.custom.yaml" ]] || { echo "desktop package contains mobile UI" >&2; exit 1; }
else
  [[ -s "$OUT/trime.custom.yaml" ]] || { echo "mobile package missing trime config" >&2; exit 1; }
  [[ ! -e "$OUT/latex.schema.yaml" ]] || { echo "mobile package contains latex" >&2; exit 1; }
  if grep -q 'translator_latex' "$OUT/flypy_quick5.custom.yaml" 2>/dev/null; then
    echo "mobile flypy custom still references latex" >&2
    exit 1
  fi
fi

echo "packaged [$VARIANT/$PLATFORM] $(find "$OUT" -type f | wc -l) files -> $OUT"
du -sh "$OUT"
find "$OUT" -maxdepth 1 -type f -printf '%f\n' | sort
