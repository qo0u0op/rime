"""Minimal streaming reader for the MOE xlsx export (no external deps)."""

from __future__ import annotations

import re
import zipfile
from typing import Iterator
from xml.etree import ElementTree as ET

NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
WANTED = {"字詞名", "多音排序", "注音一式", "釋義", "異體字"}


def _shared_strings(z: zipfile.ZipFile) -> list[str]:
    strings: list[str] = []
    with z.open("xl/sharedStrings.xml") as f:
        for _, el in ET.iterparse(f, events=("end",)):
            if el.tag == NS + "si":
                strings.append("".join(t.text or "" for t in el.iter(NS + "t")))
                el.clear()
    return strings


def _cell_value(cell, strings: list[str]) -> str:
    kind = cell.get("t")
    value = cell.find(NS + "v")
    if kind == "s" and value is not None:
        return strings[int(value.text or "0")]
    if kind == "inlineStr":
        inline = cell.find(NS + "is")
        if inline is not None:
            return "".join(t.text or "" for t in inline.iter(NS + "t"))
    if value is not None:
        return value.text or ""
    return ""


def _iter_raw_rows(z: zipfile.ZipFile) -> Iterator[dict[str, str]]:
    strings = _shared_strings(z)
    with z.open("xl/worksheets/sheet1.xml") as f:
        for _, el in ET.iterparse(f, events=("end",)):
            if el.tag != NS + "row":
                continue
            values: dict[str, str] = {}
            for cell in el.findall(NS + "c"):
                ref = cell.get("r") or ""
                match = re.match(r"([A-Z]+)", ref)
                if not match:
                    continue
                values[match.group(1)] = _cell_value(cell, strings)
            yield values
            el.clear()


def read_xlsx_rows(path: str) -> Iterator[dict[str, str]]:
    """Yield one dict per data row, keyed by the five wanted column names."""
    with zipfile.ZipFile(path) as z:
        header: dict[str, str] | None = None
        for raw in _iter_raw_rows(z):
            if header is None:
                header = {
                    letter: name
                    for letter, name in raw.items()
                    if name in WANTED
                }
                continue
            yield {
                name: raw.get(letter, "")
                for letter, name in header.items()
            }
