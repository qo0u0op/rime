#!/usr/bin/env python3
"""Generate flypy_quick5.dict.yaml from luna_pinyin and cangjie5.

Implements the 小鶴雙拼 algebra with 飛鍵 (derive branches at exact rule
positions) and pairs it with the 倉頡速成 first/last code.
"""

from __future__ import annotations

import os
import re
import sys
import unicodedata
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

LUNA_PINYIN = os.path.join(ROOT, "luna_pinyin.dict.yaml")
CANGJIE5 = os.path.join(ROOT, "cangjie5.dict.yaml")
OUTPUT = os.path.join(ROOT, "flypy_quick5.dict.yaml")
READING_WEIGHTS = os.path.join(HERE, "reading_weights.tsv")
PAIRS = os.path.join(HERE, "essay_pairs.tsv")


def algebra_rules():
    """Return (type, pattern, replacement) in the order used by flypy_luna."""
    return [
        ("erase", r"^xx$", ""),
        ("derive", r"^([jqxy])u$", r"\1v"),
        ("derive", r"^([aoe])([ioun])$", r"\1\1\2"),
        ("xform", r"^([aoe])(ng)?$", r"\1\1\2"),
        ("xform", r"iu$", "Q"),
        ("xform", r"(.)ei$", r"\1W"),
        ("xform", r"uan$", "R"),
        ("xform", r"[uv]e$", "T"),
        ("xform", r"un$", "Y"),
        ("xform", r"^sh", "U"),
        ("xform", r"^ch", "I"),
        ("xform", r"^zh", "V"),
        ("xform", r"uo$", "O"),
        ("xform", r"ie$", "P"),
        ("xform", r"i?ong$", "S"),
        ("xform", r"ing$|uai$", "K"),
        ("xform", r"(.)ai$", r"\1D"),
        ("xform", r"(.)en$", r"\1F"),
        ("xform", r"(.)eng$", r"\1G"),
        ("xform", r"[iu]ang$", "L"),
        ("xform", r"(.)ang$", r"\1H"),
        ("xform", r"ian$", "M"),
        ("xform", r"(.)an$", r"\1J"),
        ("xform", r"(.)ou$", r"\1Z"),
        ("xform", r"[iu]a$", "X"),
        ("xform", r"iao$", "N"),
        ("xform", r"(.)ao$", r"\1C"),
        ("xform", r"ui$", "V"),
        ("xform", r"in$", "B"),
        ("xlit", "QWRTYUIOPSDFGHJKLZXCVBNM", "qwrtyuiopsdfghjklzxcvbnm"),
    ]


def pinyin_to_flypy(pinyin: str) -> set[str]:
    """Apply the 小鶴 rules, branching on every derive rule."""
    strings = {pinyin}
    for rule_type, pattern, replacement in algebra_rules():
        new_strings: set[str] = set()
        for text in strings:
            if rule_type == "erase":
                if not re.match(pattern, text):
                    new_strings.add(text)
            elif rule_type == "xform":
                new_strings.add(re.sub(pattern, replacement, text))
            elif rule_type == "derive":
                new_strings.add(text)
                if re.search(pattern, text):
                    new_strings.add(re.sub(pattern, replacement, text))
            elif rule_type == "xlit":
                new_strings.add(text.translate(str.maketrans(pattern, replacement)))
        strings = new_strings
        if not strings:
            break
    return {s for s in strings if len(s) >= 2}


def cangjie_quick(code: str) -> str | None:
    """First and last Cangjie letter; double a single-letter code."""
    code = code.strip()
    if not code:
        return None
    first = code[0]
    last = code[-1] if len(code) >= 2 else first
    return first + last


def is_cjk(char: str) -> bool:
    if char == "〇":
        return True
    try:
        return unicodedata.name(char, "").startswith("CJK UNIFIED IDEOGRAPH")
    except ValueError:
        return False


def parse_dict(path: str) -> dict[str, list[tuple[str, str]]]:
    entries: dict[str, list[tuple[str, str]]] = defaultdict(list)
    in_header = True
    with open(path, encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if in_header:
                if stripped == "...":
                    in_header = False
                continue
            parts = stripped.split("\t")
            if len(parts) < 2:
                continue
            char, code = parts[0], parts[1].split()[0]
            weight = parts[2] if len(parts) >= 3 else ""
            if len(char) == 1 and is_cjk(char):
                entries[char].append((code, weight))
    return entries


def _cangjie_quicks(codes: list[tuple[str, str]]) -> set[str]:
    has_normal = any(
        not code.startswith("x") and not code.startswith("z") for code, _ in codes
    )
    quicks: set[str] = set()
    for code, _ in codes:
        if code.startswith("x") or code.startswith("z"):
            if has_normal:
                continue
            code = re.sub(r"^[xz]+", "", code)
            if not code:
                continue
        quick = cangjie_quick(code)
        if quick and len(quick) == 2 and all("a" <= c <= "z" for c in quick):
            quicks.add(quick)
    return quicks


def load_reading_weights(path: str) -> dict[tuple[str, str], str]:
    overrides: dict[tuple[str, str], str] = {}
    if not os.path.exists(path):
        return overrides
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) < 3:
                continue
            overrides[(parts[0], parts[1])] = parts[2]
    return overrides


def load_variants(path: str) -> set[str]:
    """Characters that should use the essay variant band, not luna percentages."""
    variants: set[str] = set()
    if not os.path.exists(path):
        return variants
    with open(path, encoding="utf-8") as f:
        for line in f:
            if not line or line.startswith("#"):
                continue
            parts = line.rstrip("\n").split("\t")
            if len(parts) >= 4 and parts[2] == "char" and parts[3] == "ortho":
                variants.add(parts[1])
    return variants


def generate_char_entries(
    luna: dict[str, list[tuple[str, str]]],
    cangjie: dict[str, list[tuple[str, str]]],
    overrides: dict[tuple[str, str], str] | None = None,
    variants: set[str] | None = None,
) -> list[tuple[str, str, str]]:
    overrides = overrides or {}
    variants = variants or set()
    entries: list[tuple[str, str, str]] = []
    seen: set[tuple[str, str]] = set()
    for char in sorted(set(luna) & set(cangjie)):
        quicks = _cangjie_quicks(cangjie[char])
        if not quicks:
            continue
        for pinyin, weight in luna[char]:
            weight = overrides.get((char, pinyin), weight)
            if (char, pinyin) not in overrides and char in variants:
                weight = ""
            for dp in sorted(pinyin_to_flypy(pinyin)):
                for quick in sorted(quicks):
                    key = (char, f"{dp}/{quick}")
                    if key in seen:
                        continue
                    seen.add(key)
                    entries.append((char, key[1], weight))
    return entries


def main() -> int:
    print(f"Parsing {LUNA_PINYIN} ...")
    luna = parse_dict(LUNA_PINYIN)
    print(f"Parsing {CANGJIE5} ...")
    cangjie = parse_dict(CANGJIE5)

    overrides = load_reading_weights(READING_WEIGHTS)
    variants = load_variants(PAIRS)
    entries = generate_char_entries(luna, cangjie, overrides, variants)
    entries.sort(key=lambda row: (row[0], row[1]))

    header = f"""# Rime dictionary
# encoding: utf-8
#
# flypy_quick5 - 小鶴雙拼＋倉頡速成輔助碼
#
# Generated by generate_flypy_quick5.py
# Source: {LUNA_PINYIN}, {CANGJIE5}
#

---
name: flypy_quick5
version: "0.1"
sort: by_weight
use_preset_vocabulary: true
import_tables:
  - flypy_quick5_phrases
...

"""
    with open(OUTPUT, "w", encoding="utf-8", newline="\n") as f:
        f.write(header)
        for char, code, weight in entries:
            line = f"{char}\t{code}"
            if weight:
                line += f"\t{weight}"
            f.write(line + "\n")

    print(f"Generated {len(entries)} entries -> {OUTPUT}")
    print(f"Total unique characters: {len({row[0] for row in entries})}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
