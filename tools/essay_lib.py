"""Shared data model and weight math for the rime essay pipeline."""

from __future__ import annotations

import os
from bisect import bisect_left, bisect_right
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class Pair:
    preferred: str
    variant: str
    scope: str
    type: str
    source: str
    note: str = ""


def load_pairs(path: str) -> list[Pair]:
    pairs: list[Pair] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) < 5:
                continue
            parts += [""] * (6 - len(parts))
            pairs.append(
                Pair(
                    parts[0],
                    parts[1],
                    parts[2],
                    parts[3],
                    parts[4],
                    parts[5],
                )
            )
    return pairs


def dump_pairs(pairs: Iterable[Pair], path: str) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        for p in pairs:
            f.write(
                "\t".join(
                    [p.preferred, p.variant, p.scope, p.type, p.source, p.note]
                )
                + "\n"
            )
    os.replace(tmp, path)


def load_essay(path: str) -> dict[str, float]:
    data: dict[str, float] = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line:
                continue
            key, value = line.split("\t")[:2]
            weight = float(value)
            if key not in data or weight > data[key]:
                data[key] = weight
    return data


def format_weight(value: float) -> str:
    value = float(value)
    if value == int(value):
        return str(int(value))
    return f"{value:.1f}".rstrip("0").rstrip(".")


class RankTable:
    """Descending rank index over a list of weights."""

    def __init__(self, values: Iterable[float]):
        self._values = sorted((float(v) for v in values), reverse=True)
        self._neg = [-v for v in self._values]

    def rank(self, value: float) -> int:
        """Number of values strictly greater than ``value``."""
        return bisect_left(self._neg, -float(value))

    def value_at(self, rank: int) -> float:
        if not self._values:
            return 0.0
        index = max(0, min(int(rank), len(self._values) - 1))
        return self._values[index]

    def next_lower(self, value: float) -> float | None:
        """Largest value strictly smaller than ``value``, or ``None``."""
        index = bisect_right(self._neg, -float(value))
        if index >= len(self._values):
            return None
        return self._values[index]


def _target_weight(table: RankTable, weight: float, gap: int) -> float:
    target = table.value_at(table.rank(weight) + gap)
    if target >= weight:
        lower = table.next_lower(weight)
        if lower is not None and lower > 0.0:
            return lower
        return max(1.0, weight * 0.5)
    return max(1.0, target)


def derive_phrase_pairs(essay: dict[str, float], pairs: list[Pair]) -> list[Pair]:
    """Create orthographic phrase pairs from approved character pairs.

    Only one character is substituted per phrase, so the result stays
    reviewable and does not explode combinatorially.
    """
    mapping: dict[str, str] = {}
    for p in pairs:
        if p.scope == "char" and p.type == "ortho":
            mapping[p.variant] = p.preferred

    derived: list[Pair] = []
    seen: set[tuple[str, str]] = set()
    for key in essay:
        if len(key) < 2:
            continue
        for index, char in enumerate(key):
            replacement = mapping.get(char)
            if not replacement:
                continue
            alternative = key[:index] + replacement + key[index + 1 :]
            pair_key = (alternative, key)
            if alternative == key or pair_key in seen:
                continue
            seen.add(pair_key)
            derived.append(
                Pair(alternative, key, "phrase", "ortho", "derived", "")
            )
    return derived


def apply_pairs(
    essay: dict[str, float],
    pairs: list[Pair],
    page_size: int = 5,
    gap_pages: int = 3,
    phrase_gap_pages: int = 10,
    passes: int = 3,
) -> tuple[dict[str, float], list[dict]]:
    """Align each pair's two weights, keeping both entries.

    Preferred weights are fixed first, then variant targets are recomputed
    against the live distribution for a few passes so later pairs do not
    silently undo earlier ones.
    """
    out = dict(essay)
    preferred_keys = {p.preferred for p in pairs}
    variant_owners: dict[str, set[str]] = {}
    for p in pairs:
        variant_owners.setdefault(p.variant, set()).add(p.preferred)
    conflicted = {k for k in preferred_keys if k in variant_owners}
    conflicted |= {
        key for key, owners in variant_owners.items() if len(owners) > 1
    }

    reading: list[Pair] = []
    active: list[Pair] = []
    skipped: list[Pair] = []
    conflicts: list[Pair] = []
    for p in pairs:
        if p.type == "reading":
            reading.append(p)
        elif p.preferred in conflicted or p.variant in conflicted:
            conflicts.append(p)
        elif p.preferred not in essay and p.variant not in essay:
            skipped.append(p)
        else:
            active.append(p)

    preferred_weight: dict[str, float] = {}
    for p in active:
        weight = max(essay.get(p.preferred, 0.0), essay.get(p.variant, 0.0))
        if weight <= 0.0:
            weight = 10.0
        preferred_weight[p.preferred] = max(
            preferred_weight.get(p.preferred, 0.0), weight
        )
    for key, weight in preferred_weight.items():
        out[key] = weight

    for p in reading:
        wp = out.get(p.preferred)
        wv = out.get(p.variant)
        if wp is None and wv is None:
            skipped.append(p)
            continue
        table = RankTable(out.values())
        base = max(wp or 0.0, wv or 0.0)
        floor = max(
            1.0, table.value_at(table.rank(base) + page_size * gap_pages * 2)
        )
        if wp == 0.0:
            out[p.preferred] = floor
        if wv == 0.0:
            out[p.variant] = floor

    for _ in range(max(1, passes)):
        table = RankTable(out.values())
        changed = False
        for p in active:
            weight = preferred_weight[p.preferred]
            pages = phrase_gap_pages if p.scope == "phrase" else gap_pages
            gap = page_size * pages * (2 if p.type == "regional" else 1)
            target = _target_weight(table, weight, gap)
            if out.get(p.variant) != target:
                changed = True
            out[p.variant] = target
        if not changed:
            break

    final = RankTable(out.values())
    report: list[dict] = []
    for p in active:
        weight = preferred_weight[p.preferred]
        target = out[p.variant]
        gap = final.rank(target) - final.rank(weight)
        pages = phrase_gap_pages if p.scope == "phrase" else gap_pages
        expected = page_size * pages * (2 if p.type == "regional" else 1)
        report.append(
            {
                "preferred": p.preferred,
                "variant": p.variant,
                "type": p.type,
                "action": "overshoot" if gap > expected else "ok",
                "weight": weight,
                "target": target,
                "gap": gap,
            }
        )
    for p in conflicts:
        report.append(
            {
                "preferred": p.preferred,
                "variant": p.variant,
                "type": p.type,
                "action": "conflict",
            }
        )
    for p in skipped:
        report.append(
            {
                "preferred": p.preferred,
                "variant": p.variant,
                "type": p.type,
                "action": "skip",
            }
        )
    for p in reading:
        if any(
            r["preferred"] == p.preferred and r["variant"] == p.variant
            for r in report
        ):
            continue
        report.append(
            {
                "preferred": p.preferred,
                "variant": p.variant,
                "type": p.type,
                "action": "ok",
            }
        )
    return out, report


def write_essay(path: str, data: dict[str, float]) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        for key in sorted(data):
            f.write(f"{key}\t{format_weight(data[key])}\n")
    os.replace(tmp, path)
