#!/usr/bin/env python3
"""Extract variant evidence from the 電腦漢字字典 mdx for the approved pairs.

Requires the `readmdict` package (or set PYTHONPATH to a checkout).
The output is a review aid; it does not change ranking.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from typing import Iterable

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from essay_lib import Pair, load_pairs

VARIANT_RE = re.compile(r"([^\s()]+) \(U\+([0-9A-Fa-f]+)\)\s*((?:\[[^\]]+\]\s*)*)")


def parse_variants(text: str) -> list[tuple[str, str, list[str]]]:
    """Return (char, codepoint, source tags) from the 異體字 section."""
    clean = re.sub(r"`\d+`", "", text)
    clean = re.sub(r"<[^>]+>", " ", clean)
    marker = -1
    for token in ("異體字：", "異體字:"):
        marker = clean.find(token)
        if marker != -1:
            break
    if marker == -1:
        return []
    section = clean[marker + 4 :]
    end = section.find("關聯字")
    if end != -1:
        section = section[:end]
    result: list[tuple[str, str, list[str]]] = []
    for match in VARIANT_RE.finditer(section):
        char, code, raw_tags = match.groups()
        tags = re.findall(r"\[([^\]]+)\]", raw_tags)
        result.append((char, code.upper(), tags))
    return result


def build_evidence(
    pairs: Iterable[Pair],
    entries: dict[str, str],
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    evidence: list[dict[str, str]] = []
    missing: list[dict[str, str]] = []
    for pair in pairs:
        if pair.scope != "char" or pair.type != "ortho":
            continue
        text = entries.get(pair.variant)
        if not text:
            evidence.append(
                {
                    "preferred": pair.preferred,
                    "variant": pair.variant,
                    "moe": "no",
                    "sources": "",
                    "note": "variant not in 電腦漢字字典",
                }
            )
            continue
        found = [
            (char, tags)
            for char, _code, tags in parse_variants(text)
            if char == pair.preferred
        ]
        if not found:
            evidence.append(
                {
                    "preferred": pair.preferred,
                    "variant": pair.variant,
                    "moe": "no",
                    "sources": "",
                    "note": "preferred not listed as a variant",
                }
            )
            continue
        tags = found[0][1]
        moe = any("民國教育部" in tag for tag in tags)
        evidence.append(
            {
                "preferred": pair.preferred,
                "variant": pair.variant,
                "moe": "yes" if moe else "no",
                "sources": ";".join(tags),
                "note": "",
            }
        )
        for char, _code, tags in parse_variants(text):
            if char == pair.preferred:
                continue
            if any("民國教育部" in tag for tag in tags):
                missing.append(
                    {
                        "preferred": char,
                        "variant": pair.variant,
                        "sources": ";".join(tags),
                    }
                )
    return evidence, missing


def read_mdx_entries(path: str) -> dict[str, str]:
    try:
        from readmdict import MDX
    except ImportError as exc:
        raise SystemExit(
            "readmdict is required: pip install readmdict "
            "(or set PYTHONPATH to a checkout)"
        ) from exc
    mdx = MDX(path)
    return {
        key.decode("utf-8", "replace"): value.decode("utf-8", "replace")
        for key, value in mdx.items()
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mdx", required=True)
    parser.add_argument("--pairs", default=os.path.join(HERE, "essay_pairs.tsv"))
    parser.add_argument("--out", default=os.path.join(HERE, "evidence.tsv"))
    parser.add_argument(
        "--missing-out", default=os.path.join(HERE, "evidence_missing.tsv")
    )
    args = parser.parse_args(argv)

    evidence, missing = build_evidence(
        load_pairs(args.pairs), read_mdx_entries(args.mdx)
    )

    with open(args.out, "w", encoding="utf-8", newline="\n") as f:
        f.write("# preferred<TAB>variant<TAB>moe<TAB>sources<TAB>note\n")
        for row in evidence:
            f.write(
                "\t".join(
                    [
                        row["preferred"],
                        row["variant"],
                        row["moe"],
                        row["sources"],
                        row["note"],
                    ]
                )
                + "\n"
            )
    with open(args.missing_out, "w", encoding="utf-8", newline="\n") as f:
        f.write("# preferred<TAB>variant<TAB>sources\n")
        for row in missing:
            f.write(
                "\t".join([row["preferred"], row["variant"], row["sources"]])
                + "\n"
            )
    print(f"{len(evidence)} evidence rows -> {args.out}")
    print(f"{len(missing)} missing rows -> {args.missing_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
