#!/usr/bin/env python3
"""Extract the TW-ABCN standard-character classes from the xlsx export."""

from __future__ import annotations

import argparse
import os
import re
import sys
import zipfile
from xml.etree import ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


def _shared_strings(z: zipfile.ZipFile) -> list[str]:
    strings: list[str] = []
    with z.open("xl/sharedStrings.xml") as f:
        for _, el in ET.iterparse(f, events=("end",)):
            if el.tag == NS + "si":
                strings.append("".join(t.text or "" for t in el.iter(NS + "t")))
                el.clear()
    return strings


def read_abcn_rows(path: str) -> list[dict[str, str]]:
    with zipfile.ZipFile(path) as z:
        strings = _shared_strings(z)
        rows: list[dict[str, str]] = []
        with z.open("xl/worksheets/sheet1.xml") as f:
            for _, el in ET.iterparse(f, events=("end",)):
                if el.tag != NS + "row":
                    continue
                values: dict[str, str] = {}
                for cell in el.findall(NS + "c"):
                    match = re.match(r"([A-Z]+)", cell.get("r") or "")
                    if not match:
                        continue
                    kind = cell.get("t")
                    value = cell.find(NS + "v")
                    inline = cell.find(NS + "is")
                    if kind == "s" and value is not None:
                        text = strings[int(value.text or "0")]
                    elif kind == "inlineStr" and inline is not None:
                        text = "".join(
                            t.text or "" for t in inline.iter(NS + "t")
                        )
                    elif value is not None:
                        text = value.text or ""
                    else:
                        text = ""
                    values[match.group(1)] = text
                rows.append(values)
                el.clear()
    return rows


def parse_abcn_rows(rows: list[dict[str, str]]) -> dict[str, tuple[str, str]]:
    table: dict[str, tuple[str, str]] = {}
    for row in rows[1:]:
        char = (row.get("B") or "").strip()
        number = (row.get("C") or "").strip()
        if not char or not number:
            continue
        table[char] = (number[0], number)
    return table


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--xlsx", required=True)
    parser.add_argument("--out", default=os.path.join(HERE, "abcn.tsv"))
    args = parser.parse_args(argv)

    table = parse_abcn_rows(read_abcn_rows(args.xlsx))
    with open(args.out, "w", encoding="utf-8", newline="\n") as f:
        f.write("# char<TAB>class(A/B/C/N)<TAB>number\n")
        for char in sorted(table):
            cls, number = table[char]
            f.write(f"{char}\t{cls}\t{number}\n")
    print(f"{len(table)} characters -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
