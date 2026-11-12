# rime-essay-tw Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 從 pacman 維護的 `essay.txt` 重生台灣字形優先、保留異體與跨區詞的 rime 頻率表，並用兩支新腳本產生 flypy 字表與詞組表。

**Architecture:** 一個純函式庫 `essay_lib.py` 負責 pair 模型與權重數學；`generate_essay.py` 是 CLI；兩支 flypy 腳本照 `generate_lisp_quick5*.py` 的模式產生 dict；`rime-essay-tw` 包裝器由 pacman hook 呼叫，只印提示不部署。

**Tech Stack:** Python 3.11+ 標準庫（`unittest`、`dataclasses`、`bisect`）、bash、pacman hook；dev-only 使用 `opencc`；MOE 原始資料用 stdlib 讀 xlsx。

**Spec:** `docs/superpowers/specs/2026-11-12-rime-essay-tw-design.md`（資料來源已改為 `dict_revised_2015_20260929.xlsx`）

## Global Constraints

- 不刪除、不歸零任何既有條目；只新增與調權重。
- essay 依 key 的 Unicode 碼位排序；同 key 取 `max`。
- `page_size = 5`；`ortho` gap = 15 名，`regional` gap = 30 名。
- `reading` 兩邊保持原值，只在 0 時給 floor。
- 產物寫入採原子替換（`.tmp` → `rename`）。
- hook **不得**呼叫 `fcitx5-remote`、不得重啟輸入法；只印訊息。
- 專案根目錄：`~/.local/share/fcitx5/rime`。
- 測試用 `python3 -m unittest discover -s tests -v`，不新增第三方依賴。

## Review Focus

- essay 同時有重複 key 時，必須取最大值，不得讓後出現的較小值覆蓋。
- pair 兩邊都不存在時，必須跳過並記入報告，不得憑空造字。
- 低頻同值區（權重 0/1）對齊時，必須終止並記 `overshoot`，不得無限迴圈。
- phrase 中若有字缺倉頡碼，只跳過該組合，不得讓整條詞消失。
- hook 在沒有使用者 session、或找不到 rime 目錄時，必須正常結束並印出原因。
- 同一輸入連跑兩次必須位元組相同（冪等）。

---

### Task 1: Pair 模型、essay I/O、名次表

**Files:**
- Create: `essay_lib.py`
- Create: `tests/__init__.py`
- Test: `tests/test_essay_lib.py`

**Interfaces:**
- Produces:
  - `@dataclass(frozen=True) Pair(preferred: str, variant: str, scope: str, type: str, source: str, note: str = "")`
  - `load_pairs(path: str) -> list[Pair]`
  - `dump_pairs(pairs: list[Pair], path: str) -> None`
  - `load_essay(path: str) -> dict[str, float]`
  - `format_weight(value: float) -> str`
  - `class RankTable: __init__(values); rank(value: float) -> int; value_at(rank: int) -> float; next_lower(value: float) -> float | None`

- [ ] **Step 1: 寫失敗測試**

```python
import os
import tempfile
import unittest
from essay_lib import Pair, RankTable, format_weight, load_essay, load_pairs

class TestEssayLib(unittest.TestCase):
    def test_load_essay_takes_max_for_duplicate_keys(self):
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write("甲\t3\n乙\t5\n甲\t9\n")
            path = f.name
        try:
            self.assertEqual(load_essay(path), {"甲": 9.0, "乙": 5.0})
        finally:
            os.unlink(path)

    def test_load_pairs_skips_comments_and_blank_lines(self):
        with tempfile.NamedTemporaryFile("w", suffix=".tsv", delete=False, encoding="utf-8") as f:
            f.write("# comment\n\n為\t爲\tchar\tortho\tmoe\t\n")
            path = f.name
        try:
            self.assertEqual(
                load_pairs(path),
                [Pair("為", "爲", "char", "ortho", "moe", "")],
            )
        finally:
            os.unlink(path)

    def test_rank_table_orders_descending(self):
        table = RankTable([10, 30, 20])
        self.assertEqual(table.rank(30), 0)
        self.assertEqual(table.rank(20), 1)
        self.assertEqual(table.rank(10), 2)
        self.assertEqual(table.value_at(1), 20)

    def test_next_lower_returns_strictly_smaller(self):
        table = RankTable([100, 100, 50, 1])
        self.assertEqual(table.next_lower(100), 50)
        self.assertIsNone(table.next_lower(1))

    def test_format_weight_keeps_integers_and_one_decimal(self):
        self.assertEqual(format_weight(1234.0), "1234")
        self.assertEqual(format_weight(1234.5), "1234.5")
        self.assertEqual(format_weight(0.0), "0")
```

- [ ] **Step 2: 執行測試確認失敗**

Run: `python3 -m unittest tests.test_essay_lib -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'essay_lib'`

- [ ] **Step 3: 實作 `essay_lib.py`**

重點：
- `load_essay` 以 `max` 合併重複 key；值用 `float`。
- `RankTable` 內部把值反轉排序；`rank` 用 `bisect_left` 於負值列表（同值取第一個名次）。
- `next_lower` 回傳嚴格小於的最後一個值；沒有則 `None`。
- `format_weight`：整數不帶小數，其餘 `round(..., 1)` 後去尾零。

- [ ] **Step 4: 執行測試確認通過**

Run: `python3 -m unittest tests.test_essay_lib -v`
Expected: 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add essay_lib.py tests/__init__.py tests/test_essay_lib.py
git commit -m "feat(essay): add pair model and rank table"
```

---

### Task 2: 對齊演算法與 `generate_essay.py`

**Files:**
- Modify: `essay_lib.py`
- Create: `generate_essay.py`
- Test: `tests/test_generate_essay.py`

**Interfaces:**
- Consumes: `Pair`, `RankTable`, `load_essay`, `format_weight`
- Produces:
  - `apply_pairs(essay: dict[str, float], pairs: list[Pair], page_size: int = 5) -> tuple[dict[str, float], list[dict]]`
  - `write_essay(path: str, data: dict[str, float]) -> None`
  - CLI `python3 generate_essay.py --essay PATH --pairs PATH --out PATH --report PATH [--gap-pages 3] [--dry-run]`

- [ ] **Step 1: 寫失敗測試**

```python
import unittest
from essay_lib import Pair, apply_pairs

def pair(p="主", v="異", t="ortho", scope="char"):
    return Pair(p, v, scope, t, "test", "")

class TestApplyPairs(unittest.TestCase):
    def test_ortho_gap_is_fifteen_ranks(self):
        essay = {f"k{i:02d}": float(100 - i) for i in range(40)}
        essay["主"] = 90.0
        essay["異"] = 40.0
        out, _ = apply_pairs(essay, [pair()], page_size=5)
        self.assertEqual(out["主"], 90.0)
        from essay_lib import RankTable
        table = RankTable(list(essay.values()))
        self.assertEqual(table.rank(out["異"]) - table.rank(90.0), 15)

    def test_ortho_adds_missing_variant(self):
        essay = {"主": 100.0, "a": 50.0, "b": 40.0}
        out, _ = apply_pairs(essay, [pair("主", "缺")], page_size=5)
        self.assertIn("缺", out)
        self.assertLess(out["缺"], out["主"])

    def test_reading_keeps_both_weights(self):
        essay = {"妳": 2085.0, "嬭": 103.0, "x": 10.0}
        out, _ = apply_pairs(essay, [pair("妳", "嬭", "reading")], page_size=5)
        self.assertEqual(out["妳"], 2085.0)
        self.assertEqual(out["嬭"], 103.0)

    def test_reading_gives_floor_only_when_zero(self):
        essay = {"妳": 2085.0, "嬭": 0.0, "x": 10.0}
        out, _ = apply_pairs(essay, [pair("妳", "嬭", "reading")], page_size=5)
        self.assertGreater(out["嬭"], 0)

    def test_both_missing_is_skipped(self):
        out, report = apply_pairs({}, [pair("甲", "乙")], page_size=5)
        self.assertEqual(out, {})
        self.assertEqual(report[0]["action"], "skip")

    def test_tie_block_reports_overshoot(self):
        essay = {f"tie{i}": 100.0 for i in range(20)}
        essay.update({f"low{i}": 50.0 for i in range(200)})
        essay["主"] = 100.0
        essay["異"] = 100.0
        out, report = apply_pairs(essay, [pair()], page_size=5)
        self.assertLess(out["異"], out["主"])
        self.assertEqual(report[0]["action"], "overshoot")

    def test_idempotent(self):
        essay = {f"k{i}": float(i + 1) for i in range(60)}
        essay["主"] = 55.0
        essay["異"] = 5.0
        once, _ = apply_pairs(essay, [pair()], page_size=5)
        twice, _ = apply_pairs(once, [pair()], page_size=5)
        self.assertEqual(once, twice)
```

- [ ] **Step 2: 執行測試確認失敗**

Run: `python3 -m unittest tests.test_generate_essay -v`
Expected: FAIL with `ImportError: cannot import name 'apply_pairs'`

- [ ] **Step 3: 實作 `apply_pairs`、`write_essay`、CLI**

規則（照 spec §8.2）：
- `ortho`：`w=max(wp,wv)`；`target=RankTable(原始 essay 值).value_at(rank(w)+page_size*3)`；若 `target>=w` 取 `next_lower(w)`；再不行取 `w*0.5`；記錄 `action` 為 `ok`、`overshoot` 或 `skip`。
- `regional`：同上但 gap = `page_size*6`。
- `reading`：兩邊原值不動；只把 0 補成 `max(1, value_at(rank(max)+page_size*6))`。
- 兩邊都不存在 → `skip`。
- `write_essay`：`sorted(data.items(), key=lambda kv: kv[0])`，寫 `.tmp` 後 `os.replace`。

CLI 需讀 `--gap-pages`（預設 3）並輸出 `essay_report.txt`（純文字統計）。

- [ ] **Step 4: 執行測試確認通過**

Run: `python3 -m unittest tests.test_generate_essay -v`
Expected: 7 tests PASS

- [ ] **Step 5: 手動煙霧測試**

Run:
`python3 generate_essay.py --essay /usr/share/rime-data/essay.txt --pairs /dev/null --out /tmp/opencode/essay-smoke.txt --report /tmp/opencode/essay-smoke.txt.report`
Expected: 產出檔與上游筆數相同、排序正確

- [ ] **Step 6: Commit**

```bash
git add essay_lib.py generate_essay.py tests/test_generate_essay.py
git commit -m "feat(essay): align variant weights within three pages"
```

---

### Task 3: MOE pair 抽取器（xlsx 原始資料）

**Files:**
- Create: `tools/extract_moe_pairs.py`
- Create: `tools/xlsx_rows.py`
- Test: `tests/test_extract_moe.py`

**Interfaces:**
- Produces:
  - `read_xlsx_rows(path: str) -> Iterator[dict[str, str]]`（只取 `字詞名`、`多音排序`、`注音一式`、`釋義`、`異體字` 五欄）
  - `parse_moe_rows(rows: Iterable[dict[str, str]]) -> tuple[list[Pair], list[Pair]]`
    （回傳 `auto_pairs`、`review_pairs`）
  - CLI `python3 tools/extract_moe_pairs.py --xlsx PATH --auto-out essay_pairs.tsv --review-out essay_pairs_review.tsv`

- [ ] **Step 1: 寫失敗測試（用 row dict，不讀 xlsx）**

```python
import unittest
from tools.extract_moe_pairs import parse_moe_rows

ROWS = [
    {"字詞名": "裡", "多音排序": "0", "注音一式": "ㄌㄧˇ", "釋義": "內部。", "異體字": ""},
    {"字詞名": "裏", "多音排序": "0", "注音一式": "", "釋義": "「裡」的異體字。", "異體字": "異體字"},
    {"字詞名": "妳", "多音排序": "0", "注音一式": "ㄋㄧˇ", "釋義": "女性的第二人稱。", "異體字": ""},
    {"字詞名": "妳", "多音排序": "0", "注音一式": "", "釋義": "「嬭」的異體字。", "異體字": "異體字"},
]

class TestMoe(unittest.TestCase):
    def test_pure_variant_is_auto(self):
        auto, review = parse_moe_rows(ROWS)
        self.assertIn(("裡", "裏"), [(p.preferred, p.variant) for p in auto])
        self.assertEqual(review, [])

    def test_head_with_own_reading_goes_to_review(self):
        auto, review = parse_moe_rows(ROWS)
        self.assertIn(("嬭", "妳"), [(p.preferred, p.variant) for p in review])
        self.assertNotIn(("嬭", "妳"), [(p.preferred, p.variant) for p in auto])

    def test_unparsable_definition_is_skipped(self):
        auto, review = parse_moe_rows([{"字詞名": "X", "多音排序": "0", "注音一式": "", "釋義": "沒有關係", "異體字": "異體字"}])
        self.assertEqual((auto, review), ([], []))
```

- [ ] **Step 2: 執行測試確認失敗**

Run: `python3 -m unittest tests.test_extract_moe -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'tools'`

- [ ] **Step 3: 實作**

- `tools/xlsx_rows.py`：用 `zipfile` + `xml.etree.ElementTree.iterparse` 串流讀 `xl/sharedStrings.xml` 與 `xl/worksheets/sheet1.xml`；回傳以欄名為 key 的 dict。不需要 openpyxl。
- `tools/extract_moe_pairs.py`：
  - 以 regex `「(.{1,12}?)」的異體字` 解析 `釋義`。
  - `Pair(preferred=X, variant=字詞名, scope="char", source="moe")`。
  - 同一個 `字詞名` 若有「非旗標且 `注音一式` 非空」的列 → `review`，type=`reading`；否則 `auto`，type=`ortho`。
  - 輸出 TSV：`preferred<TAB>variant<TAB>scope<TAB>type<TAB>source<TAB>note`。

- [ ] **Step 4: 執行測試確認通過**

Run: `python3 -m unittest tests.test_extract_moe -v`
Expected: 3 tests PASS

- [ ] **Step 5: 用真實 xlsx 煙霧測試**

Run:
`python3 tools/extract_moe_pairs.py --xlsx "/home/d0w0b/Downloads/dictsource/dict_revised_2015_20260929/dict_revised_2015_20260929.xlsx" --auto-out /tmp/opencode/moe_auto.tsv --review-out /tmp/opencode/moe_review.tsv`
Expected: auto ≈ 1,421 筆、review ≈ 60 筆；`grep -P "^為\t爲" /tmp/opencode/moe_auto.tsv` 有結果

- [ ] **Step 6: Commit**

```bash
git add tools/__init__.py tools/xlsx_rows.py tools/extract_moe_pairs.py tests/test_extract_moe.py
git commit -m "feat(tools): extract MOE variant pairs from xlsx"
```

### Task 4: OpenCC pair 抽取器與 pair 種子

**Files:**
- Create: `tools/extract_opencc_pairs.py`
- Create: `essay_pairs.tsv`
- Create: `essay_pairs_review.tsv`
- Test: `tests/test_extract_opencc.py`

**Interfaces:**
- Produces:
  - `derive_pair(text: str, ortho, regional) -> Pair | None`
    （`ortho`/`regional` 是 `Callable[[str], str]`）
- CLI `python3 tools/extract_opencc_pairs.py --essay PATH --luna PATH --out PATH`

- [ ] **Step 1: 寫失敗測試（注入假轉換器）**

```python
import unittest
from tools.extract_opencc_pairs import derive_pair

def ortho(text):
    return {"裏面": "裡面"}.get(text, text)

def regional(text):
    return {"軟件": "軟體"}.get(text, text)

class TestOpenCC(unittest.TestCase):
    def test_ortho_wins_over_regional(self):
        p = derive_pair("裏面", ortho, regional)
        self.assertEqual((p.preferred, p.variant, p.type), ("裡面", "裏面", "ortho"))

    def test_regional_when_ortho_unchanged(self):
        p = derive_pair("軟件", ortho, regional)
        self.assertEqual((p.preferred, p.variant, p.type), ("軟體", "軟件", "regional"))

    def test_identity_returns_none(self):
        self.assertIsNone(derive_pair("吃飯", ortho, regional))
```

- [ ] **Step 2: 執行測試確認失敗**

Run: `python3 -m unittest tests.test_extract_opencc -v`
Expected: FAIL with `ImportError`

- [ ] **Step 3: 實作與產生種子**

- `derive_pair`：先 `ortho(text)`；有變 → `ortho`；否則 `regional(text)`；有變 → `regional`；都沒有 → `None`。
- `main`：用 `opencc.OpenCC("t2tw")` 與 `opencc.OpenCC("s2twp")`（Python 套件），對 essay 與 luna 的 key 求 pair；輸出 TSV。
- 執行：
  ```
  python3 tools/extract_opencc_pairs.py --essay /usr/share/rime-data/essay.txt --luna luna_pinyin.dict.yaml --out /tmp/opencode/opencc_pairs.tsv
  ```
- 人工檢查後，把 OpenCC 的 41 條字對與 MOE auto 合併成 `essay_pairs.tsv`（`source` 欄位保留 `opencc`／`moe`），其餘寫入 `essay_pairs_review.tsv`。合併用下列片段（同 key 取 MOE 優先）：
  ```python
  import glob
  from essay_lib import load_pairs, dump_pairs
  pairs = {}
  for path in glob.glob("/tmp/opencode/*_pairs.tsv"):
      for p in load_pairs(path):
          key = (p.preferred, p.variant)
          if key not in pairs or p.source == "moe":
              pairs[key] = p
  dump_pairs(sorted(pairs.values(), key=lambda p: (p.preferred, p.variant)), "essay_pairs.tsv")
  ```
- 這一步的產物要 commit；日後重跑只做 diff。

- [ ] **Step 4: 執行測試確認通過**

Run: `python3 -m unittest tests.test_extract_opencc -v`
Expected: 3 tests PASS

- [ ] **Step 5: 驗證種子**

Run: `grep -c $'\t' essay_pairs.tsv`
Expected: ≥ 41（OpenCC 字對）且包含 `為\t爲`、`裡\t裏`、`著\t着`、`麵\t麪`、`吃\t喫`

- [ ] **Step 6: Commit**

```bash
git add tools/extract_opencc_pairs.py tests/test_extract_opencc.py essay_pairs.tsv essay_pairs_review.tsv
git commit -m "feat(tools): seed variant pairs from OpenCC and MOE"
```

---

### Task 5: flypy 字表產生器

**Files:**
- Create: `generate_flypy_quick5.py`
- Test: `tests/test_flypy_chars.py`

**Interfaces:**
- Produces:
  - `pinyin_to_flypy(pinyin: str) -> set[str]`
  - `cangjie_quick(code: str) -> str | None`
  - `parse_dict(path: str) -> dict[str, list[tuple[str, str]]]`
  - `generate_char_entries(luna: dict, cangjie: dict) -> list[tuple[str, str, str]]`
  - CLI 輸出 `flypy_quick5.dict.yaml`

- [ ] **Step 1: 寫失敗測試**

```python
import unittest
from generate_flypy_quick5 import cangjie_quick, pinyin_to_flypy

class TestFlypyCodes(unittest.TestCase):
    def test_zhong(self):
        self.assertEqual(pinyin_to_flypy("zhong"), {"vs"})

    def test_shi(self):
        self.assertEqual(pinyin_to_flypy("shi"), {"ui"})

    def test_zhuang(self):
        self.assertEqual(pinyin_to_flypy("zhuang"), {"vl"})

    def test_qu_derives_two_codes(self):
        self.assertEqual(pinyin_to_flypy("qu"), {"qu", "qv"})

    def test_nv(self):
        self.assertEqual(pinyin_to_flypy("nv"), {"nv"})

    def test_cangjie_quick(self):
        self.assertEqual(cangjie_quick("lwg"), "lg")
        self.assertEqual(cangjie_quick("l"), "ll")
        self.assertIsNone(cangjie_quick(""))
```

- [ ] **Step 2: 執行測試確認失敗**

Run: `python3 -m unittest tests.test_flypy_chars -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: 實作**

- 複製 `generate_lisp_quick5.py` 的 `algebra_rules()` 引擎（erase/xform/derive/xlit）。
- 把規則換成 `flypy_luna.schema.yaml` 第 117–146 行的 30 條小鶴規則，函式改名 `pinyin_to_flypy`。
- `cangjie_quick` 與 `parse_dict` 直接沿用 lisp 版邏輯。
- `generate_char_entries`：只取 luna∩cangjie 的單字；每個 pinyin × dp × cj quick 產生 `(字, "dp/cj", luna_weight)`；權重空字串照抄。
- 輸出標頭與 lisp 版相同，但 `name: flypy_quick5`。

- [ ] **Step 4: 執行測試確認通過**

Run: `python3 -m unittest tests.test_flypy_chars -v`
Expected: 6 tests PASS

- [ ] **Step 5: 產生並比對**

Run:
`python3 generate_flypy_quick5.py`
Expected: 產生 `flypy_quick5.dict.yaml`；檢查 `裏` 的碼為 `li/yv`、`裡` 為 `li/lg`、`中` 含 `vs/ll`

- [ ] **Step 6: Commit**

```bash
git add generate_flypy_quick5.py tests/test_flypy_chars.py flypy_quick5.dict.yaml
git commit -m "feat(flypy): generate character table from luna and cangjie"
```

---

### Task 6: flypy 詞組表與 schema

**Files:**
- Create: `generate_flypy_quick5_phrases.py`
- Modify: `flypy_quick5.schema.yaml:36-43`
- Test: `tests/test_flypy_phrases.py`

**Interfaces:**
- Produces:
  - `parse_phrases(path: str) -> list[tuple[str, list[str]]]`
  - `phrase_codes(phrase: str, syllables: list[str], cangjie: dict, pairs: list[Pair]) -> list[tuple[str, str]]`
  - CLI 輸出 `flypy_quick5_phrases.dict.yaml`

- [ ] **Step 1: 寫失敗測試（fixture 字串）**

```python
import unittest
from essay_lib import Pair
from generate_flypy_quick5_phrases import phrase_codes

CANGJIE = {
    "時": [("agdi", "")], "中": [("l", "")],
    "裏": [("ywgv", "")], "裡": [("lwg", "")], "面": [("mwsl", "")],
}

class TestPhraseCodes(unittest.TestCase):
    def test_basic_phrase(self):
        self.assertIn(("時中", "ui/ai vs/ll"), phrase_codes("時中", ["shi", "zhong"], CANGJIE, []))

    def test_variant_spelling_added(self):
        pairs = [Pair("裡", "裏", "char", "ortho", "test", "")]
        got = phrase_codes("裏面", ["li", "mian"], CANGJIE, pairs)
        self.assertIn(("裏面", "li/yv ml"), [c for c in got if c[0] == "裏面"])
        self.assertIn("裡面", [c[0] for c in got])

    def test_missing_cangjie_skips_only_that_char(self):
        got = phrase_codes("時X", ["shi", "zhong"], CANGJIE, [])
        self.assertEqual(got, [])
```

- [ ] **Step 2: 執行測試確認失敗**

Run: `python3 -m unittest tests.test_flypy_phrases -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: 實作**

- `parse_phrases` 只讀 `#以下爲詞組` 之後、syllable 數等於字數的條目（照 lisp 版）。
- `phrase_codes`：每位字取 dp 集合 × cj 集合，`product` 展開；code 以空格連接。
- 變體寫法：對 phrase 的每個字套 `ortho` 字對（`scope=="char"`），用同一組 syllables、變體字的 cangjie 重算；只做單一替換，避免組合爆炸。
- schema 加：
  ```yaml
    import_tables:
      - flypy_quick5_phrases
  ```

- [ ] **Step 4: 執行測試確認通過**

Run: `python3 -m unittest tests.test_flypy_phrases -v`
Expected: 3 tests PASS

- [ ] **Step 5: 產生並驗證 schema**

Run:
`python3 generate_flypy_quick5_phrases.py`
`grep -A 2 "import_tables" flypy_quick5.schema.yaml`
Expected: 產生 `flypy_quick5_phrases.dict.yaml`，schema 有 `flypy_quick5_phrases`

- [ ] **Step 6: Commit**

```bash
git add generate_flypy_quick5_phrases.py flypy_quick5.schema.yaml tests/test_flypy_phrases.py flypy_quick5_phrases.dict.yaml
git commit -m "feat(flypy): add phrase table with variant spellings"
```

---

### Task 7: pacman hook 與包裝器

**Files:**
- Create: `rime-essay-tw`
- Create: `91-rime-essay-tw.hook`
- Create: `install-hook.sh`
- Test: `tests/test_hook.py`

**Interfaces:**
- `rime-essay-tw [--dry-run] [--root PATH] [--user NAME]`
- 環境變數：`RIME_ESSAY_TW_DRY_RUN=1`、`RIME_ESSAY_TW_ROOT`（預設 `/home`）
- 輸出格式：`[rime-essay-tw] 已更新 PATH（OLD → NEW 條）`

- [ ] **Step 1: 寫失敗測試**

```python
import os, subprocess, tempfile, unittest

class TestHook(unittest.TestCase):
    def test_dry_run_prints_message_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            rime = os.path.join(tmp, "u", ".local/share/fcitx5/rime")
            os.makedirs(rime)
            env = dict(os.environ, RIME_ESSAY_TW_DRY_RUN="1", RIME_ESSAY_TW_ROOT=tmp)
            r = subprocess.run(
                ["./rime-essay-tw", "--user", "u"],
                capture_output=True, text=True, env=env,
            )
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("已更新", r.stdout)
            self.assertEqual(os.listdir(rime), [])

    def test_missing_rime_dir_reports_and_exits_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = dict(os.environ, RIME_ESSAY_TW_DRY_RUN="1", RIME_ESSAY_TW_ROOT=tmp)
            r = subprocess.run(["./rime-essay-tw", "--user", "nobody"], capture_output=True, text=True, env=env)
            self.assertEqual(r.returncode, 0)
            self.assertIn("找不到", r.stdout)
```

- [ ] **Step 2: 執行測試確認失敗**

Run: `python3 -m unittest tests.test_hook -v`
Expected: FAIL with `FileNotFoundError`

- [ ] **Step 3: 實作**

- `rime-essay-tw`：
  - `set -euo pipefail`；解析 `--dry-run`、`--root`、`--user`。
  - 找 `$ROOT/*/.local/share/fcitx5/rime`；沒有就印「找不到 rime 目錄」並 `exit 0`。
  - `--dry-run` 只印訊息；否則 `runuser -u "$u" -- python3 generate_essay.py ...`。
  - **不呼叫** `fcitx5-remote`。
- `91-rime-essay-tw.hook`：`When = PostTransaction`、`Exec = /usr/local/bin/rime-essay-tw`。
- `install-hook.sh`：安裝到 `/usr/local/bin` 與 `/etc/pacman.d/hooks`，支援 `--uninstall`。

- [ ] **Step 4: 執行測試確認通過**

Run: `python3 -m unittest tests.test_hook -v`
Expected: 2 tests PASS

- [ ] **Step 5: Commit**

```bash
git add rime-essay-tw 91-rime-essay-tw.hook install-hook.sh tests/test_hook.py
git commit -m "feat(hook): regenerate essay on rime-essay updates"
```

---

### Task 8: 端到端重生與驗收

**Files:**
- Modify: `essay.txt`（產物）
- Modify: `flypy_quick5.dict.yaml`、`flypy_quick5_phrases.dict.yaml`（產物）
- Create: `essay_report.txt`
- Create: `README-essay-tw.md`（操作說明）

**Interfaces:**
- Consumes: 前七個任務的全部 CLI。

- [ ] **Step 1: 重生 essay**

Run:
`python3 generate_essay.py --essay /usr/share/rime-data/essay.txt --pairs essay_pairs.tsv --out essay.txt --report essay_report.txt`
Expected: `essay.txt` 筆數 ≥ 上游；`essay_report.txt` 有 pair 統計與 `overshoot` 清單

- [ ] **Step 2: 驗收核心對**

Run:
`python3 - <<'EOF'`
（讀 `essay.txt`，檢查 `為`、`爲`、`裡`、`裏`、`著`、`着` 的權重與名次差）
Expected: `為 > 爲`、`裡 > 裏`、`著 > 着`，且差距 ≤ 15 名（或列在 `overshoot`）

- [ ] **Step 3: 重生兩張 flypy 表**

Run:
`python3 generate_flypy_quick5.py && python3 generate_flypy_quick5_phrases.py`
Expected: 兩檔產生，`裏` 的碼含 `yv`、`裡` 含 `lg`

- [ ] **Step 4: 冪等檢查**

Run:
`sha256sum essay.txt > /tmp/opencode/essay.sha`
`python3 generate_essay.py --essay /usr/share/rime-data/essay.txt --pairs essay_pairs.tsv --out essay.txt --report essay_report.txt`
`sha256sum -c /tmp/opencode/essay.sha`
Expected: `OK`

- [ ] **Step 5: 全套測試**

Run: `python3 -m unittest discover -s tests -v`
Expected: 全部 PASS

- [ ] **Step 6: 撰寫操作說明並 Commit**

`README-essay-tw.md` 內容：如何重生、如何看報告、如何停用 hook、如何回滾。

```bash
git add essay.txt essay_report.txt flypy_quick5.dict.yaml flypy_quick5_phrases.dict.yaml README-essay-tw.md
git commit -m "chore(essay): regenerate Taiwan-first tables"
```

---

## Self-Review

**Spec coverage：**
- §8 essay 演算法 → Task 1、2
- §8.3 讀音判定 → Task 3
- §8.4 phrase → Task 6（dict 層）＋ Task 2（essay 層）
- §9 dict 生成 → Task 5、6
- §10 hook → Task 7
- §11 驗證 → Task 8
- §12 回滾 → README（Task 8）
- §13 風險 → 已反映在 `overshoot`、`skip`、`reading` 測試

**Placeholder scan：** 無 TBD；所有函式都有簽名與測試。

**Type consistency：** `Pair` 欄位在 Task 1 定義，Task 3/4/6 共用；`apply_pairs` 回傳 `(dict, report)` 在 Task 2 定義並在 Task 8 使用。
