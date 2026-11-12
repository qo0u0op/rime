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
