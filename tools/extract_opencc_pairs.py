#!/usr/bin/env python3
"""Seed variant pairs from OpenCC.

Single characters come from OpenCC's t2tw (orthographic variants).
Multi-character phrases only take the regional branch (t2tw unchanged,
s2twp changed), because phrase orthography is generated later by applying
the approved character pairs.
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Callable

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from essay_lib import Pair, dump_pairs

Ortho = Callable[[str], str]
Regional = Callable[[str], str]


def derive_pair(text: str, ortho: Ortho, regional: Regional) -> Pair | None:
    scope = "char" if len(text) == 1 else "phrase"
    target = ortho(text)
    if target != text:
        return Pair(target, text, scope, "ortho", "opencc", "")
    target = regional(text)
    if target != text:
        return Pair(target, text, scope, "regional", "opencc", "")
    return None


def read_keys(path: str) -> set[str]:
    keys: set[str] = set()
    with open(path, encoding="utf-8") as f:
        lines = f.read().splitlines()

    start = 0
    for index, line in enumerate(lines):
        if line.strip() == "...":
            start = index + 1
            break

    for line in lines[start:]:
        if not line or line.startswith("#"):
            continue
        key = line.split("\t")[0]
        if key:
            keys.add(key)
    return keys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--essay", required=True)
    parser.add_argument("--luna", required=True)
    parser.add_argument("--out", default="essay_pairs_opencc.tsv")
    args = parser.parse_args(argv)

    import opencc

    t2tw = opencc.OpenCC("t2tw").convert
    s2twp = opencc.OpenCC("s2twp").convert

    keys = read_keys(args.essay) | read_keys(args.luna)
    chars = {k for k in keys if len(k) == 1}
    phrases = {k for k in keys if len(k) > 1}

    pairs: list[Pair] = []
    for char in sorted(chars):
        pair = derive_pair(char, t2tw, lambda text: text)
        if pair:
            pairs.append(pair)

    for phrase in sorted(phrases):
        if t2tw(phrase) != phrase:
            continue
        target = s2twp(phrase)
        if target != phrase:
            pairs.append(Pair(target, phrase, "phrase", "regional", "opencc", ""))

    dump_pairs(sorted(pairs, key=lambda p: (p.preferred, p.variant)), args.out)
    print(f"{len(pairs)} pairs -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
