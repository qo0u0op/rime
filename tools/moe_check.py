#!/usr/bin/env python3
"""Build a checklist of MOE-standard pairs and the codes to type."""

from __future__ import annotations

import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from essay_lib import Pair, load_essay, load_pairs
from generate_flypy_quick5 import (
    CANGJIE5,
    LUNA_PINYIN,
    _cangjie_quicks,
    parse_dict,
    pinyin_to_flypy,
)
from generate_lisp_quick5 import pinyin_to_double_codes


def _percent(weight: str) -> float:
    if not weight:
        return 0.0
    try:
        return float(weight.rstrip("%"))
    except ValueError:
        return 0.0


def build_rows(
    pairs: list[Pair],
    luna: dict[str, list[tuple[str, str]]],
    cangjie: dict[str, list[tuple[str, str]]],
    essay: dict[str, float],
    limit: int | None = None,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for pair in pairs:
        if pair.scope != "char" or pair.type != "ortho":
            continue
        pref_pinyin = dict(luna.get(pair.preferred, []))
        var_pinyin = dict(luna.get(pair.variant, []))
        shared = set(pref_pinyin) & set(var_pinyin)
        if not shared:
            continue
        reading = max(shared, key=lambda p: _percent(pref_pinyin[p]))

        lisp_dp = sorted(pinyin_to_double_codes(reading))
        flypy_dp = sorted(pinyin_to_flypy(reading))
        if not lisp_dp or not flypy_dp:
            continue
        pref_cj = sorted(_cangjie_quicks(cangjie.get(pair.preferred, [])))
        var_cj = sorted(_cangjie_quicks(cangjie.get(pair.variant, [])))
        if not pref_cj or not var_cj:
            continue

        rows.append(
            {
                "preferred": pair.preferred,
                "variant": pair.variant,
                "reading": reading,
                "lisp_input": lisp_dp[0],
                "flypy_input": flypy_dp[0],
                "lisp_preferred": f"{lisp_dp[0]}/{pref_cj[0]}",
                "lisp_variant": f"{lisp_dp[0]}/{var_cj[0]}",
                "flypy_preferred": f"{flypy_dp[0]}/{pref_cj[0]}",
                "flypy_variant": f"{flypy_dp[0]}/{var_cj[0]}",
                "preferred_weight": essay.get(pair.preferred, 0.0),
            }
        )

    rows.sort(key=lambda row: -row["preferred_weight"])
    if limit:
        rows = rows[:limit]
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pairs", default=os.path.join(HERE, "essay_pairs.tsv"))
    parser.add_argument("--luna", default=LUNA_PINYIN)
    parser.add_argument("--cangjie", default=CANGJIE5)
    parser.add_argument("--essay", default=os.path.join(ROOT, "essay.txt"))
    parser.add_argument("--out", default=os.path.join(HERE, "moe_check.tsv"))
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args(argv)

    rows = build_rows(
        load_pairs(args.pairs),
        parse_dict(args.luna),
        parse_dict(args.cangjie),
        load_essay(args.essay),
        args.limit or None,
    )

    columns = [
        "preferred",
        "variant",
        "reading",
        "lisp_input",
        "flypy_input",
        "lisp_preferred",
        "lisp_variant",
        "flypy_preferred",
        "flypy_variant",
    ]
    with open(args.out, "w", encoding="utf-8", newline="\n") as f:
        f.write("# 輸入 lisp_input / flypy_input，主形應排在異體之前\n")
        f.write("\t".join(columns) + "\n")
        for row in rows:
            f.write("\t".join(str(row[c]) for c in columns) + "\n")

    print(f"{len(rows)} rows -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
