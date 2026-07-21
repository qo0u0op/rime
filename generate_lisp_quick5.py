#!/usr/bin/env python3
"""
Generate lisp_quick5.dict.yaml from luna_pinyin.dict.yaml and cangjie5.dict.yaml.

Implements the lisp (Colemak-DH adapted 大牛双拼) algebra rules with 飛鍵技術
(derive branches at exact rule positions).
"""

import re
import sys
import unicodedata
from collections import defaultdict

LISP_YAML = "lisp.yaml"
LUNA_PINYIN = "luna_pinyin.dict.yaml"
CANGJIE5 = "cangjie5.dict.yaml"
OUTPUT = "lisp_quick5.dict.yaml"

# ---------------------------------------------------------------------------
# 1. Algebra engine: simulate lisp.yaml speller rules in order
# ---------------------------------------------------------------------------

def algebra_rules():
  """
  Return list of (type, pattern, replacement) in EXACT order from lisp.yaml.
  """
  return [
    ("erase", r"^xx$", ""),
    ("xform", r"^([aoe].*)$", r"U\1"),
    ("derive", r"^([jqxy])u(.*)$", r"\1v\2"),
    ("derive", r"^po$", "pe"),
    ("xform", r"^sh", "E"),
    ("derive", r"^E", "V"),
    ("xform", r"^zh", "O"),
    ("derive", r"^O", "A"),
    ("xform", r"^ch", "I"),
    ("xform", r"ian$", "H"),
    ("derive", r"H", "Q"),  # only applies to ian-derived H (uai→H is after this derive)
    ("xform", r"ui$", "Y"),
    ("derive", r"Y", "V"),
    ("xform", r"iang$", "G"),
    ("xform", r"iao$", "P"),
    ("xform", r"uang$|ve$", "X"),
    ("xform", r"uan$", "Z"),
    ("xform", r"(.)eng$|van$", r"\1N"),
    ("xform", r"ua$", "Q"),
    ("xform", r"(.)ei$|vn$", r"\1W"),
    ("xform", r"ou$", "R"),
    ("xform", r"iu$", "B"),
    ("xform", r"er$", "U"),
    ("xform", r"uo$", "O"),
    ("xform", r"ie$", "J"),
    ("xform", r"(.)ao$", r"\1C"),
    ("xform", r"(.)an$", r"\1S"),
    ("xform", r"(.)ang$", r"\1F"),
    ("xform", r"uai$", "H"),
    ("xform", r"ing$", "L"),
    ("xform", r"(.)ai$|ue$", r"\1M"),
    ("xform", r"(.)en$|ia$", r"\1T"),
    ("xform", r"i?ong$", "K"),
    ("xform", r"in$", "Y"),
    ("xform", r"un$", "D"),
    ("xlit", "QWFPBJLUYARSTGMNEIOZXCDVKH", "qwfpbjluyarstgmneiozxcdvkh"),
  ]


def pinyin_to_double_codes(pinyin):
  """
  Apply algebra rules in order, branching on derive.
  Returns set of double-pinyin codes (lowercase).
  """
  strings = {pinyin}

  for rule_type, pattern, replacement in algebra_rules():
    new_strings = set()
    for s in strings:
      if rule_type == "erase":
        if not re.match(pattern, s):
          new_strings.add(s)
      elif rule_type == "xform":
        new_strings.add(re.sub(pattern, replacement, s))
      elif rule_type == "derive":
        new_strings.add(s)
        if re.search(pattern, s):
          new_strings.add(re.sub(pattern, replacement, s))
      elif rule_type == "xlit":
        trans = str.maketrans(pattern, replacement)
        new_strings.add(s.translate(trans))
    strings = new_strings
    if not strings:
      break

  # Filter out any that are not 2+ letters (some edge cases produce empty)
  return {s for s in strings if len(s) >= 2}


# ---------------------------------------------------------------------------
# 2. Helper: quick Cangjie code (首尾碼, single-code double)
# ---------------------------------------------------------------------------

def cangjie_quick(code):
  """Extract first and last Cangjie letter; double if single-letter."""
  code = code.strip()
  if not code:
    return None
  first = code[0]
  if len(code) >= 2:
    last = code[-1]
  else:
    last = first
  return first + last


# ---------------------------------------------------------------------------
# 3. CJK character detection (all extension blocks)
# ---------------------------------------------------------------------------

def is_cjk(char):
  """Check if char is a CJK Unified Ideograph (all extensions) or 〇."""
  if char == '〇':
    return True
  try:
    return unicodedata.name(char, '').startswith('CJK UNIFIED IDEOGRAPH')
  except ValueError:
    return False


# ---------------------------------------------------------------------------
# 4. Parse dict YAML (simple TSV parser, skips YAML header)
# ---------------------------------------------------------------------------

def parse_dict(path):
  """
  Parse a Rime .dict.yaml file.
  Returns dict: {char: [(code, weight)]} for single-character entries.
  Skips YAML header (lines before `...` on its own line).
  Skips multi-character words (2+ CJK chars).
  """
  entries = defaultdict(list)
  in_header = True

  with open(path, "r", encoding="utf-8") as f:
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
      char, code = parts[0], parts[1]
      weight = parts[2] if len(parts) >= 3 else ""

      # Single CJK character only (all extension blocks)
      if len(char) == 1 and is_cjk(char):
        entries[char].append((code, weight))

  return entries


# ---------------------------------------------------------------------------
# 5. Main
# ---------------------------------------------------------------------------

def main():
  print("Parsing luna_pinyin.dict.yaml ...")
  pinyin_map = parse_dict(LUNA_PINYIN)
  print(f"  {len(pinyin_map)} unique characters")

  print("Parsing cangjie5.dict.yaml ...")
  cangjie_map = parse_dict(CANGJIE5)
  print(f"  {len(cangjie_map)} unique characters")

  # Cross-reference
  common = set(pinyin_map) & set(cangjie_map)
  print(f"  {len(common)} characters in both")
  print(f"  {len(pinyin_map) - len(common)} in luna_pinyin only (skipped)")
  print(f"  {len(cangjie_map) - len(common)} in cangjie5 only (skipped)")

  # Generate entries
  output_lines = []
  seen = set()
  duplicates = 0

  for char in sorted(common):
    cj_codes = cangjie_map[char]
    cj_quicks = set()
    for code, _ in cj_codes:
      qc = cangjie_quick(code)
      if qc and len(qc) == 2 and all('a' <= c <= 'z' for c in qc):
        cj_quicks.add(qc)

    pinyins = pinyin_map[char]
    for pinyin, weight in pinyins:
      dp_codes = pinyin_to_double_codes(pinyin)
      if not dp_codes:
        continue
      for dp in dp_codes:
        for qc in cj_quicks:
          code_entry = f"{dp}'{qc}"
          key = (char, code_entry)
          if key in seen:
            duplicates += 1
            continue
          seen.add(key)
          line = f"{char}\t{code_entry}"
          if weight:
            line += f"\t{weight}"
          output_lines.append(line)

  print(f"Generated {len(output_lines)} entries ({duplicates} duplicates skipped)")

  # Sort: by char, then by code
  output_lines.sort(key=lambda x: (x.split("\t")[0], x.split("\t")[1]))

  # Write output
  header = f"""# Rime dictionary
# encoding: utf-8
#
# lisp_quick5 - 闊碼雙拼＋倉頡速成輔助碼
#
# Generated by generate_lisp_quick5.py
# Source: {LUNA_PINYIN}, {CANGJIE5}
#

---
name: lisp_quick5
version: "0.1"
sort: by_weight
use_preset_vocabulary: true
...

"""
  with open(OUTPUT, "w", encoding="utf-8") as f:
    f.write(header)
    for line in output_lines:
      f.write(line + "\n")

  print(f"Written to {OUTPUT}")

  # Stats
  total_chars = len(set(line.split("\t")[0] for line in output_lines))
  print(f"Total unique characters: {total_chars}")


if __name__ == "__main__":
  main()
