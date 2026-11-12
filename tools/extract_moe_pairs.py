#!/usr/bin/env python3
"""Extract variant pairs from the MOE dictionary xlsx export."""

from __future__ import annotations

import argparse
import collections
import os
import re
import sys
from typing import Iterable

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from essay_lib import Pair, dump_pairs
from xlsx_rows import read_xlsx_rows

VARIANT_RE = re.compile(r"「(.{1,12}?)」的異體字")


def _is_placeholder(text: str) -> bool:
    """True for user-defined-area characters and image placeholders."""
    if not text:
        return False
    for char in text:
        code = ord(char)
        if 0xE000 <= code <= 0xF8FF or 0xF0000 <= code <= 0xFFFFF:
            return True
    return bool(re.search(r"&[0-9A-Fa-f]+.*\.(?:gif|png)", text))


def parse_moe_rows(
    rows: Iterable[dict[str, str]],
) -> tuple[list[Pair], list[Pair]]:
    by_head: dict[str, list[dict[str, str]]] = collections.defaultdict(list)
    for row in rows:
        head = (row.get("字詞名") or "").strip()
        if head:
            by_head[head].append(row)

    auto: list[Pair] = []
    review: list[Pair] = []
    seen: set[tuple[str, str]] = set()

    for head, group in by_head.items():
        if _is_placeholder(head):
            continue
        flagged = [r for r in group if (r.get("異體字") or "").strip()]
        if not flagged:
            continue
        # A head that also has its own reading is a dual-use character.
        has_reading = any(
            not (r.get("異體字") or "").strip()
            and (r.get("注音一式") or "").strip()
            for r in group
        )
        for row in flagged:
            match = VARIANT_RE.search(row.get("釋義") or "")
            if not match:
                continue
            preferred = match.group(1)
            if _is_placeholder(preferred):
                continue
            key = (preferred, head)
            if key in seen:
                continue
            seen.add(key)
            pair = Pair(
                preferred,
                head,
                "char",
                "reading" if has_reading else "ortho",
                "moe",
                "",
            )
            (review if has_reading else auto).append(pair)

    return auto, review


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--xlsx", required=True)
    parser.add_argument("--auto-out", default="essay_pairs.tsv")
    parser.add_argument("--review-out", default="essay_pairs_review.tsv")
    args = parser.parse_args(argv)

    if not os.path.exists(args.xlsx):
        print(f"xlsx not found: {args.xlsx}", file=sys.stderr)
        return 2

    auto, review = parse_moe_rows(read_xlsx_rows(args.xlsx))
    dump_pairs(auto, args.auto_out)
    dump_pairs(review, args.review_out)
    print(f"auto: {len(auto)} -> {args.auto_out}")
    print(f"review: {len(review)} -> {args.review_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
