#!/usr/bin/env python3
"""Merge an upstream Rime dictionary into a local copy.

Rules:
- Header comes from the upstream file, except local overrides that are
  explicitly kept (`use_preset_vocabulary: false` on cangjie5).
- Entries come from upstream, in upstream order.
- Entries that exist only locally are appended, so a package update never
  deletes locally added characters.
- Old PUA mappings (U+E000..U+F8FF) that exist only locally are dropped;
  upstream replaced them with proper radicals.
- When both sides have the same (text, code) pair, upstream wins.
- Optional overrides force a weight for a (text, code) pair, e.g.
  `暫 zhan 100%`. See tools/dict_overrides.tsv.

Usage: merge_source_dict.py LOCAL UPSTREAM OUT [OVERRIDES]
"""

import os
import sys

KEEP_HEADER_OVERRIDES = ("use_preset_vocabulary",)
PUA_START = 0xE000
PUA_END = 0xF8FF


def split_dict(text):
    lines = text.splitlines()
    try:
        idx = lines.index("...")
    except ValueError:
        raise SystemExit("dictionary has no '...' separator")

    return lines[: idx + 1], lines[idx + 1 :]


def header_values(lines):
    values = {}
    for line in lines:
        if line.startswith("#") or ":" not in line:
            continue
        if line.startswith((" ", "\t")):
            continue
        key, _, value = line.partition(":")
        values[key.strip()] = value.strip()

    return values


def entry_key(line):
    if not line.strip() or line.lstrip().startswith("#"):
        return None
    fields = line.split("\t")
    if len(fields) < 2:
        return None

    return (fields[0], fields[1])


def is_pua(text):
    return len(text) == 1 and PUA_START <= ord(text) <= PUA_END


def load_overrides(path, dict_name):
    """Read `file<TAB>text<TAB>code<TAB>weight` rows for one dictionary."""
    if not path:
        return []

    rows = []
    with open(path, encoding="utf-8") as fh:
        for raw in fh:
            line = raw.rstrip("\n")
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            fields = line.split("\t")
            if len(fields) < 4:
                raise SystemExit(f"bad override row: {line!r}")
            if fields[0] != dict_name:
                continue
            rows.append((fields[1], fields[2], fields[3]))

    return rows


def apply_overrides(body, overrides):
    """Force a weight on each (text, code) pair; append the pair if missing."""
    applied = 0
    for text, code, weight in overrides:
        key = (text, code)
        found = False
        for index, line in enumerate(body):
            if entry_key(line) != key:
                continue
            fields = line.split("\t")
            body[index] = "\t".join([fields[0], fields[1], weight] + fields[3:])
            found = True
            applied += 1
        if not found:
            body.append("\t".join([text, code, weight]))
            applied += 1

    return applied


def merge(local_text, upstream_text, overrides=()):
    local_header, local_body = split_dict(local_text)
    upstream_header, upstream_body = split_dict(upstream_text)

    local_values = header_values(local_header)
    header = []
    for line in upstream_header:
        key = line.partition(":")[0].strip() if ":" in line else ""
        if key in KEEP_HEADER_OVERRIDES and key in local_values:
            line = f"{key}: {local_values[key]}"
        header.append(line)

    upstream_keys = set()
    body = []
    for line in upstream_body:
        key = entry_key(line)
        if key is not None:
            upstream_keys.add(key)
        body.append(line)

    kept = []
    dropped_pua = 0
    for line in local_body:
        key = entry_key(line)
        if key is None or key in upstream_keys:
            continue
        if is_pua(key[0]):
            dropped_pua += 1
            continue
        upstream_keys.add(key)
        kept.append(line)

    body.extend(kept)
    applied = apply_overrides(body, overrides)

    return "\n".join(header + body) + "\n", len(kept), dropped_pua, applied


def main(argv):
    if len(argv) not in (4, 5):
        raise SystemExit(__doc__.strip())

    local_path, upstream_path, out_path = argv[1:4]
    overrides_path = argv[4] if len(argv) == 5 else None

    with open(local_path, encoding="utf-8") as fh:
        local_text = fh.read()
    with open(upstream_path, encoding="utf-8") as fh:
        upstream_text = fh.read()

    overrides = load_overrides(overrides_path, os.path.basename(local_path))
    merged, kept, dropped_pua, applied = merge(local_text, upstream_text, overrides)

    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(merged)

    print(
        f"[merge] kept {kept} local-only, dropped {dropped_pua} obsolete PUA, "
        f"applied {applied} overrides from {local_path}",
        file=sys.stderr,
    )

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
