#!/usr/bin/env python3
"""List MOE variants that are not in the TW-ABCN standard-character table."""

from __future__ import annotations

import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from essay_lib import load_essay, load_pairs


def load_abcn(path: str) -> set[str]:
    chars: set[str] = set()
    if not os.path.exists(path):
        return chars
    with open(path, encoding="utf-8") as f:
        for line in f:
            if not line or line.startswith("#"):
                continue
            chars.add(line.split("\t")[0])
    return chars


def load_evidence(path: str) -> dict[tuple[str, str], tuple[str, str]]:
    evidence: dict[tuple[str, str], tuple[str, str]] = {}
    if not os.path.exists(path):
        return evidence
    with open(path, encoding="utf-8") as f:
        for line in f:
            if not line or line.startswith("#"):
                continue
            parts = line.rstrip("\n").split("\t")
            if len(parts) >= 4:
                evidence[(parts[0], parts[1])] = (parts[2], parts[3])
    return evidence


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pairs", default=os.path.join(HERE, "essay_pairs.tsv"))
    parser.add_argument("--abcn", default=os.path.join(HERE, "abcn.tsv"))
    parser.add_argument("--evidence", default=os.path.join(HERE, "evidence.tsv"))
    parser.add_argument(
        "--essay", default="/usr/share/rime-data/essay.txt"
    )
    parser.add_argument(
        "--out", default=os.path.join(HERE, "variants_not_in_abcn.tsv")
    )
    args = parser.parse_args(argv)

    abcn = load_abcn(args.abcn)
    evidence = load_evidence(args.evidence)
    upstream = load_essay(args.essay)
    rows = []
    seen = set()
    for pair in load_pairs(args.pairs):
        if pair.scope != "char" or pair.type != "ortho":
            continue
        if pair.variant in abcn or pair.variant in "爲裏着衆":
            continue
        if pair.variant in seen:
            continue
        seen.add(pair.variant)
        moe, sources = evidence.get((pair.preferred, pair.variant), ("", ""))
        rows.append(
            (
                pair.variant,
                pair.preferred,
                int(upstream.get(pair.variant, 0)),
                moe,
                sources,
            )
        )
    rows.sort(key=lambda row: -row[2])

    with open(args.out, "w", encoding="utf-8", newline="\n") as f:
        f.write("# variant\tpreferred\tupstream_weight\tmoe_evidence\tsources\n")
        for row in rows:
            f.write("\t".join(map(str, row)) + "\n")
    print(f"{len(rows)} variants -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
