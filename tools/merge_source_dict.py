#!/usr/bin/env python3
"""Merge an upstream Rime dictionary into a local copy.

Rules:
- Header comes from the upstream file, except local overrides that are
  explicitly kept (`use_preset_vocabulary: false` on cangjie5).
- Entries come from upstream, in upstream order.
- Entries that exist only locally are appended, so a package update never
  deletes locally added characters (PUA / compatibility ideographs).
- When both sides have the same (text, code) pair, upstream wins.

Usage: merge_source_dict.py LOCAL UPSTREAM OUT
"""

import sys

KEEP_HEADER_OVERRIDES = ("use_preset_vocabulary",)


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


def merge(local_text, upstream_text):
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
    for line in local_body:
        key = entry_key(line)
        if key is None or key in upstream_keys:
            continue
        upstream_keys.add(key)
        kept.append(line)

    body.extend(kept)

    return "\n".join(header + body) + "\n", len(kept)


def main(argv):
    if len(argv) != 4:
        raise SystemExit(__doc__.strip())

    local_path, upstream_path, out_path = argv[1:]

    with open(local_path, encoding="utf-8") as fh:
        local_text = fh.read()
    with open(upstream_path, encoding="utf-8") as fh:
        upstream_text = fh.read()

    merged, kept = merge(local_text, upstream_text)

    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(merged)

    print(f"[merge] kept {kept} local-only entries from {local_path}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
