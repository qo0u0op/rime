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

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from essay_lib import Pair, dump_pairs, load_pairs

Ortho = Callable[[str], str]
Regional = Callable[[str], str]


def apply_char_map(text: str, mapping: dict[str, str]) -> str:
    return "".join(mapping.get(char, char) for char in text)


def load_char_map(path: str) -> dict[str, str]:
    mapping: dict[str, str] = {}
    if not path or not os.path.exists(path):
        return mapping
    for pair in load_pairs(path):
        if pair.scope == "char" and pair.type == "ortho":
            mapping[pair.preferred] = pair.variant
            mapping[pair.variant] = pair.preferred
    return mapping


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
    parser.add_argument("--pairs", default="essay_pairs.tsv")
    parser.add_argument("--out", default="essay_pairs_opencc.tsv")
    parser.add_argument("--review-out", default="essay_pairs_opencc_review.tsv")
    args = parser.parse_args(argv)

    import opencc

    t2tw = opencc.OpenCC("t2tw").convert
    s2twp = opencc.OpenCC("s2twp").convert
    char_map = load_char_map(args.pairs)

    keys = read_keys(args.essay) | read_keys(args.luna)
    chars = {k for k in keys if len(k) == 1}
    phrases = {k for k in keys if len(k) > 1}

    pairs: list[Pair] = []
    for char in sorted(chars):
        pair = derive_pair(char, t2tw, lambda text: text)
        if pair:
            pairs.append(pair)

    phrase_pairs: dict[str, list[Pair]] = {}
    for phrase in sorted(phrases):
        if t2tw(phrase) != phrase:
            continue
        target = s2twp(phrase)
        if target == phrase:
            continue
        kind = "ortho" if apply_char_map(phrase, char_map) == target else "regional"
        phrase_pairs.setdefault(phrase, []).append(
            Pair(target, phrase, "phrase", kind, "opencc", "")
        )

    review: list[Pair] = []
    for variant, candidates in phrase_pairs.items():
        targets = {p.preferred for p in candidates}
        if len(targets) > 1:
            review.extend(candidates)
        else:
            pairs.extend(candidates)

    dump_pairs(sorted(pairs, key=lambda p: (p.preferred, p.variant)), args.out)
    dump_pairs(sorted(review, key=lambda p: (p.preferred, p.variant)), args.review_out)
    print(f"{len(pairs)} pairs -> {args.out}")
    print(f"{len(review)} review pairs -> {args.review_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
