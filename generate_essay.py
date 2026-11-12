#!/usr/bin/env python3
"""Regenerate a Taiwan-first rime essay from the upstream frequency list."""

from __future__ import annotations

import argparse
import os
import sys

from essay_lib import apply_pairs, load_essay, load_pairs, write_essay

HERE = os.path.dirname(os.path.abspath(__file__))


def build_report(args, input_count, output_count, report):
    ok = sum(1 for r in report if r["action"] == "ok")
    overshoot = [r for r in report if r["action"] == "overshoot"]
    skipped = [r for r in report if r["action"] == "skip"]
    lines = [
        f"essay: {args.essay}",
        f"pairs: {args.pairs}",
        f"input entries: {input_count}",
        f"output entries: {output_count}",
        f"pairs applied: {ok}",
        f"overshoot: {len(overshoot)}",
        f"skipped: {len(skipped)}",
        "",
        "--- overshoot ---",
    ]
    for r in overshoot:
        lines.append(
            f"{r['preferred']} -> {r['variant']}\t"
            f"weight={r.get('weight')} target={r.get('target')} gap={r.get('gap')}"
        )
    lines += ["", "--- skipped ---"]
    for r in skipped:
        lines.append(f"{r['preferred']} -> {r['variant']}")
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--essay", default="/usr/share/rime-data/essay.txt")
    parser.add_argument("--pairs", default=os.path.join(HERE, "essay_pairs.tsv"))
    parser.add_argument("--out", default=os.path.join(HERE, "essay.txt"))
    parser.add_argument("--report", default=os.path.join(HERE, "essay_report.txt"))
    parser.add_argument("--page-size", type=int, default=5)
    parser.add_argument("--gap-pages", type=int, default=3)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    essay = load_essay(args.essay)
    pairs = load_pairs(args.pairs) if os.path.exists(args.pairs) else []
    out, report = apply_pairs(
        essay, pairs, page_size=args.page_size, gap_pages=args.gap_pages
    )
    text = build_report(args, len(essay), len(out), report)

    if args.dry_run:
        print(text)
        return 0

    write_essay(args.out, out)
    with open(args.report, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    print(
        f"wrote {args.out} ({len(essay)} -> {len(out)} entries), "
        f"{len(pairs)} pairs"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
