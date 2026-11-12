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


def apply_pairs(
    essay: dict[str, float],
    pairs: list[Pair],
    page_size: int = 5,
    gap_pages: int = 3,
) -> tuple[dict[str, float], list[dict]]:
    """Align each pair's two weights, keeping both entries.

    The rank table is built once from the original essay, so every target
    is measured against the same distribution.
    """
    out = dict(essay)
    table = RankTable(out.values())
    report: list[dict] = []

    for p in pairs:
        wp = out.get(p.preferred)
        wv = out.get(p.variant)
        entry = {
            "preferred": p.preferred,
            "variant": p.variant,
            "type": p.type,
        }

        if p.type == "reading":
            if wp is None and wv is None:
                entry["action"] = "skip"
                report.append(entry)
                continue
            base = max(wp or 0.0, wv or 0.0)
            floor = max(1.0, table.value_at(table.rank(base) + page_size * gap_pages * 2))
            if wp is None:
                pass
            elif wp == 0.0:
                out[p.preferred] = floor
            if wv is None:
                pass
            elif wv == 0.0:
                out[p.variant] = floor
            entry["action"] = "ok"
            report.append(entry)
            continue

        if wp is None and wv is None:
            entry["action"] = "skip"
            report.append(entry)
            continue

        weight = max(wp or 0.0, wv or 0.0)
        if weight <= 0.0:
            weight = 10.0
        gap = page_size * gap_pages * (2 if p.type == "regional" else 1)
        target = table.value_at(table.rank(weight) + gap)
        action = "ok"
        if target >= weight:
            lower = table.next_lower(weight)
            if lower is not None and lower > 0.0:
                target = lower
            else:
                target = max(1.0, weight * 0.5)
            action = "overshoot"

        out[p.preferred] = weight
        out[p.variant] = target
        entry["action"] = action
        entry["weight"] = weight
        entry["target"] = target
        entry["gap"] = table.rank(target) - table.rank(weight)
        report.append(entry)

    return out, report


def write_essay(path: str, data: dict[str, float]) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        for key in sorted(data):
            f.write(f"{key}\t{format_weight(data[key])}\n")
    os.replace(tmp, path)
