# 腳本與產出手冊

這份文件說明 `tools/` 下每支腳本、它的輸入、輸出，以及哪些檔案只在上游更新時才需要。
日常使用只要看 [README-essay-tw.md](README-essay-tw.md)；這裡是維護與重新產生資料時的參考。

## 1. 執行環境

| 用途 | 需求 |
|---|---|
| Rime 執行 | `librime`、`fcitx5-rime`（或 ibus-rime） |
| 產生 essay／dict | Python 3.11+，只用標準庫 |
| pacman hook | `runuser`、`logger`、`flock` |
| `extract_opencc_pairs.py` | Python `opencc` 套件（或系統 `opencc`） |
| `extract_evidence.py` | Python `readmdict` 套件 |
| `extract_moe_pairs.py`／`extract_abcn.py` | 原始 xlsx（Downloads） |

**Rime 執行期不需要 `opencc`、`readmdict`、xlsx 或 mdx。**
那些只是重新抽取對照資料時的工具。

## 2. 執行期（hook 會用到）

### `91-rime-essay-tw.hook`

pacman hook 本體，複製到 `/etc/pacman.d/hooks/` 即可。

```ini
[Trigger]
Operation = Install
Operation = Upgrade
Type = Package
Target = rime-essay

[Action]
Description = Regenerating Taiwan-first rime essay（重生台灣優先的 essay）
When = PostTransaction
Exec = /usr/bin/runuser -u d0w0b -- /usr/bin/python3 \
  /home/d0w0b/.local/share/fcitx5/rime/tools/generate_essay.py \
  --essay /usr/share/rime-data/essay.txt \
  --pairs /home/d0w0b/.local/share/fcitx5/rime/tools/essay_pairs.tsv \
  --out /home/d0w0b/.local/share/fcitx5/rime/essay.txt \
  --report /home/d0w0b/.local/share/fcitx5/rime/tools/essay_report.txt
```

- 只在 `rime-essay` 安裝／升級後執行。
- 以 `d0w0b` 身分寫入，避免 root 擁有的檔案。
- **不呼叫** `fcitx5-remote`、不重啟輸入法；只印出「請重新部署 Rime」。
- 需要：`generate_essay.py`、`essay_lib.py`、`essay_pairs.tsv`、`abcn.tsv`、
  `/usr/share/rime-data/essay.txt`。
- 產出：根目錄 `essay.txt`、`tools/essay_report.txt`。

## 3. 重生 essay

### `generate_essay.py`

從上游 essay 與已核可的對照表產生台灣優先的 `essay.txt`。

| 參數 | 預設 | 說明 |
|---|---|---|
| `--essay` | `/usr/share/rime-data/essay.txt` | 上游頻率表 |
| `--pairs` | `tools/essay_pairs.tsv` | 已核可的對照表 |
| `--out` | `<repo>/essay.txt` | 產出 |
| `--report` | `tools/essay_report.txt` | 報告 |
| `--abcn` | `tools/abcn.tsv` | A/B/C/N 字類；C 與 CJK 增補會壓到 `--rare-cap` |
| `--variant-cap` | `0.9` | 異體窄帶上限 |
| `--rare-cap` | `0.1` | 罕用／CJK 增補上限 |
| `--page-size` | `5` | 頁面大小（只用於 regional 詞的差距計算） |
| `--gap-pages` | `3` | 單字 regional 的差距（少用） |
| `--phrase-gap-pages` | `20` | 跨區詞的差距 |
| `--dry-run` | 關閉 | 只印報告，不寫檔 |

行為：

- 常用字（ABCN A/B/N，且不是異體/罕用）保留原權重；只有原本是 0 的抬到 1。
- 單字異體放進 `rare_cap + 0.1` 到 `variant_cap` 的窄帶（預設 0.2–0.9），
  依原權重、來源（`moe` > `evidence` > `opencc` > `derived`）、字元排序。
- C 罕用字與 CJK 增補區上限 `rare_cap`（預設 0.1）。
- 詞的異體寫法設為 0；主形保留權重。
- 跨區詞用 `--phrase-gap-pages`（預設 20 頁）。
- `reading`（讀音分化）兩邊不動，只在 0 時給下限。
- 同一字同時是某組主形與另一組異體時列為 `conflict`，跳過不強行對齊。
- 輸出依 key 排序、同 key 取最大值；原子寫入。

報告 `essay_report.txt` 的欄位：

```
input entries / output entries / added entries
pairs applied / char variants banded / phrase variants zeroed
overshoot / conflicts / skipped
--- overshoot ---
--- conflicts ---
--- skipped ---
--- core characters still at weight 0 ---
note: .gram is not regenerated
```

### `essay_lib.py`

共用函式庫，沒有 CLI。

- `Pair`：`preferred / variant / scope / type / source / note`。
- `load_pairs`、`dump_pairs`、`load_essay`、`format_weight`。
- `RankTable`：權重排名、下一個較小值。
- `apply_char_bands`：常用字保留、異體窄帶、罕用上限。
- `apply_pairs`：字/詞/讀音規則、衝突偵測、報告。
- `derive_phrase_pairs`：從已核可的字對產生詞形對照（單一字元替換）。
- `write_essay`：排序、格式化、原子寫入。

## 4. 重生字典

### `generate_flypy_quick5.py`

- 輸入：`luna_pinyin.dict.yaml`、`cangjie5.dict.yaml`、`tools/reading_weights.tsv`、
  `tools/essay_pairs.tsv`。
- 輸出：根目錄 `flypy_quick5.dict.yaml`（字表，約 52,000 行含標頭）。
- 小鶴雙拼代碼 + 倉頡速成碼；權重預設複製 luna 的百分比。
- 異體字（`essay_pairs.tsv` 的 `char/ortho` variant）不套 luna 百分比，
  直接使用 essay 的窄帶權重。
- 標頭含：
  ```yaml
  import_tables:
    - flypy_quick5_phrases
  ```
  （`import_tables` 是 **dict 標頭**設定，不是 schema translator 設定。）

### `generate_flypy_quick5_phrases.py`

- 輸入：`luna_pinyin.dict.yaml` 的 `#以下爲詞組`、`cangjie5.dict.yaml`、
  `tools/essay_pairs.tsv`。
- 輸出：根目錄 `flypy_quick5_phrases.dict.yaml`（39,945 行含標頭）。
- 每條 luna 詞產生 dp/cj 組合；再套已核可的字對產生另一種寫法
  （`着實`→`著實`）。只做單一字元替換，避免組合爆炸。
- 沒有 legacy 檔；輸出完全由 luna + 對照表決定。

### `generate_lisp_quick5.py`、`generate_lisp_quick5_phrases.py`

- 與 flypy 兩支同構，只是雙拼代數換成闊碼（Colemak-DH 大牛雙拼）。
- 輸出根目錄 `lisp_quick5.dict.yaml`、`lisp_quick5_phrases.dict.yaml`。
- 同樣在 dict 標頭 `import_tables` 詞組表，並套用 `reading_weights.tsv` 與異體帶。

## 5. 抽取與 QA（開發用，Rime 不需要）

### `extract_moe_pairs.py` + `xlsx_rows.py`

- 輸入：教育部《重編國語辭典》xlsx（Downloads）。
- 輸出：`essay_pairs.tsv`（auto）與 `essay_pairs_review.tsv`（review）。
- 解析 `字詞名`、`多音排序`、`注音一式`、`釋義`、`異體字`。
- `異體字` 欄是旗標；真正的正字在 `釋義` 的 `「X」的異體字`。
- 排除 PUA（使用者造字區）與 `&xxxx._104_0.gif`／`.png` 佔位字。
- 同一個字若另有自己的讀音列 → 進 review，type=`reading`；否則 auto，type=`ortho`。
- 手動重跑：
  ```bash
  python3 tools/extract_moe_pairs.py \
    --xlsx "/path/to/dict_revised_2015_20260929.xlsx" \
    --auto-out /tmp/moe_auto.tsv --review-out /tmp/moe_review.tsv
  ```
  不要直接覆蓋已核可的 `essay_pairs.tsv`；先輸出到 `/tmp` 再 diff。

### `extract_opencc_pairs.py`

- 輸入：上游 essay、`luna_pinyin.dict.yaml`、已核可的 `essay_pairs.tsv`（提供字對）。
- 需要 Python `opencc`。
- 輸出：`essay_pairs_opencc.tsv`（auto）與 `essay_pairs_opencc_review.tsv`（一對多）。
- 單字只取 `t2tw` 的 ortho 分支；多字詞只取 `t2tw` 不變、`s2twp` 有變的 regional 分支。
- 目標不存在於 essay/luna 的 regional 對會跳過。

### `extract_abcn.py`

- 輸入：《臺灣TW-ABCN正字甲乙丙表》xlsx（Downloads）。
- 輸出：`tools/abcn.tsv`（`char / A|B|C|N / 字號`）。
- 只讀 ABCN 工作表；`C` 類與 CJK 增補區會被 `generate_essay.py` 壓到 `rare_cap`。

### `extract_evidence.py`

- 輸入：《電腦漢字字典》mdx（OneDrive/Documents）。
- 需要 `readmdict`。
- 輸出：
  - `evidence.tsv`：`preferred / variant / moe(yes|no) / sources / note`
  - `evidence_missing.tsv`：字典有民國教育部標籤、但不在 `essay_pairs.tsv` 的候選對
- 這是**審核辅助**，不會自動改變排序。

### `list_variants_not_in_abcn.py`

- 輸入：`essay_pairs.tsv`、`abcn.tsv`、上游 essay、`evidence.tsv`。
- 輸出：`variants_not_in_abcn.tsv`
  （`variant / preferred / upstream_weight / moe_evidence / sources`）。
- 用來回答「除了 `爲、裏、着、衆`，還有哪些異體不在 ABCN」。

### `moe_check.py`

- 輸入：`essay_pairs.tsv`、`luna_pinyin.dict.yaml`、`cangjie5.dict.yaml`、`essay.txt`。
- 輸出：`moe_check.tsv`（`preferred / variant / reading / lisp_input / flypy_input / ...`）。
- 給你照著輸入、檢查主形是否排在異體之前。`--limit N` 可只取前 N 列。

## 6. 資料檔

| 檔案 | 產生者 | 消費者 | 執行期需要？ |
|---|---|---|---|
| `essay.txt` | `generate_essay.py` | Rime | 是 |
| `flypy_quick5.dict.yaml` | `generate_flypy_quick5.py` | Rime | 是 |
| `flypy_quick5_phrases.dict.yaml` | `generate_flypy_quick5_phrases.py` | Rime（dict 標頭 import） | 是 |
| `lisp_quick5.dict.yaml` | `generate_lisp_quick5.py` | Rime | 是 |
| `lisp_quick5_phrases.dict.yaml` | `generate_lisp_quick5_phrases.py` | Rime（dict 標頭 import） | 是 |
| `essay_pairs.tsv` | 人工／抽取器 | `generate_essay.py`、dict 產生器 | **是**（hook 需要） |
| `abcn.tsv` | `extract_abcn.py` | `generate_essay.py` | **是**（hook 需要） |
| `essay_pairs_review.tsv` | 抽取器／人工 | 人工 | 否 |
| `reading_weights.tsv` | 人工 | dict 產生器 | 否（只在重生 dict 時） |
| `evidence.tsv` / `evidence_missing.tsv` | `extract_evidence.py` | 人工 | 否 |
| `variants_not_in_abcn.tsv` | `list_variants_not_in_abcn.py` | 人工 | 否 |
| `moe_check.tsv` | `moe_check.py` | 人工 QA | 否 |
| `essay_report.txt` | `generate_essay.py`（含 hook） | 人工 | 否（每次重生覆蓋） |

`essay_pairs.tsv` 欄位：

```
preferred<TAB>variant<TAB>scope(char|phrase)<TAB>type(ortho|regional|reading)<TAB>source<TAB>note
```

`reading_weights.tsv` 欄位：

```
char<TAB>pinyin<TAB>weight
```

weight 可寫絕對值（`20000`）或百分比（`100%`）。目前只有 `參 san 100%`。

## 7. 外部字典與可移除檔案

以下**不在執行期使用**，只在重新抽取對照資料時需要：

- 教育部《重編國語辭典》xlsx → 只給 `extract_moe_pairs.py`
- 《臺灣TW-ABCN正字甲乙丙表》xlsx → 只給 `extract_abcn.py`
- 《電腦漢字字典》mdx → 只給 `extract_evidence.py`

一旦 `essay_pairs.tsv`、`abcn.tsv`、`evidence.tsv` 已產生並 commit，這些下載檔就可以移除；
hook 不會讀它們。若日後要重新抽取，再從原始來源取得即可。

| 檔案 | 可以移除？ | 說明 |
|---|---|---|
| `build/` | 可 | Rime 會重建 |
| `tools/essay_report.txt` | 可 | 每次重生覆蓋 |
| `tools/evidence*.tsv`、`variants_not_in_abcn.tsv`、`moe_check.tsv` | 可 | 審核／QA 快照 |
| `tools/essay_pairs_review.tsv` | 可 | 人工待審佇列；建議保留 |
| `tools/extract_*.py`、`xlsx_rows.py` | 可 | 不再重新抽取時可移除 |
| `tools/tests/`、`tools/docs/` | 可 | 開發用 |
| `tools/reading_weights.tsv` | 不可 | dict 產生器需要 |
| `tools/essay_pairs.tsv`、`tools/abcn.tsv` | **不可** | hook 需要 |
| `tools/generate_essay.py`、`tools/essay_lib.py` | **不可** | hook 需要 |
| 根目錄 `essay.txt`、四張 dict | 不可 | Rime 需要 |

hook 更新 essay 時只會覆寫 `essay.txt` 與 `essay_report.txt`；不會動
`essay_pairs.tsv`、`abcn.tsv`、`reading_weights.tsv` 或兩張 dict。

## 8. 測試

```bash
cd ~/.local/share/fcitx5/rime
python3 -m unittest discover -s tools/tests -v
```
