# rime-essay-tw

從 pacman 維護的 `/usr/share/rime-data/essay.txt` 重生一份「台灣字形優先、但保留異體與跨區用語」的
`essay.txt`，並用同一套資料產生 flypy 的字表與詞組表。

Rime 只會讀根目錄的資料檔；所有腳本、對照表、報告、測試與文件都放在 `tools/`。

## 根目錄（Rime 會讀）

| 檔案 | 用途 |
|---|---|
| `essay.txt` | 重生後的頻率表 |
| `flypy_quick5.dict.yaml` | flypy 字表 |
| `flypy_quick5_phrases.dict.yaml` | flypy 詞組表 |
| `flypy_quick5.schema.yaml` | 已加上 `import_tables: flypy_quick5_phrases` |

## tools/（不參與 Rime 執行）

| 檔案 | 用途 |
|---|---|
| `generate_essay.py` | 重生 `essay.txt` 與 `essay_report.txt` |
| `essay_lib.py` | pair 模型、名次表、對齊演算法 |
| `generate_flypy_quick5.py` | 產生 `flypy_quick5.dict.yaml` |
| `generate_flypy_quick5_phrases.py` | 產生 `flypy_quick5_phrases.dict.yaml` |
| `generate_lisp_quick5.py`、`generate_lisp_quick5_phrases.py` | 既有的 lisp 產生器；詞組也會套用字對產生另一種寫法（例：`着實`→`著實`） |
| `extract_moe_pairs.py`、`xlsx_rows.py` | 從 MOE xlsx 抽對照組 |
| `extract_opencc_pairs.py` | 從 OpenCC 抽對照組 |
| `essay_pairs.tsv` | 已核可的對照表 |
| `essay_pairs_review.tsv` | 待人工確認的對照表 |
| `reading_weights.tsv` | 破音字的讀音權重覆寫（例：`參 san 20000`、`弎 san 100`） |
| `abcn.tsv` / `extract_abcn.py` | 《臺灣TW-ABCN正字甲乙丙表》的字類（A/B/C/N） |
| `extract_evidence.py` / `evidence.tsv` | 《電腦漢字字典》的異體字來源證據 |
| `moe_check.py` / `moe_check.tsv` | 產生 MOE 對照的輸入檢查清單 |
| `essay_report.txt` | 重生報告 |
| `91-rime-essay-tw.hook` | pacman hook 本體 |
| `tests/` | `unittest` 測試 |
| `docs/` | 設計文件與實作計畫 |

## 手動重生

```bash
cd ~/.local/share/fcitx5/rime
python3 tools/generate_essay.py \
    --essay /usr/share/rime-data/essay.txt \
    --pairs tools/essay_pairs.tsv \
    --out essay.txt \
    --report tools/essay_report.txt
python3 tools/generate_flypy_quick5.py
python3 tools/generate_flypy_quick5_phrases.py
```

接著手動重新部署 Rime（重新啟動 fcitx5，或使用選單的「部署」）。

## 對照表的類型

- `char` + `ortho`（單字同詞異寫）：三層嚴格排序
  **常用字（地板上 1001）> 異體（1000）> 罕用/CJK 增補（≤100）**。
  常用字的原始權重若低於地板，會被抬到 1001；這是為了保證它一定贏過異體。
  例：`wei` 的順序是 **為 > 未 > 位 > 味 > 衛 > 偽 > 慰（1001）> 爲/僞（1000）> 罕用字**。
- `phrase` + `ortho`（詞的同詞異寫）：異體寫法直接設 **0**，主形保留權重。
  詞的碼重疊比單字少，所以從候選尾端仍找得到，不會佔首頁。
- `phrase` + `regional`（跨區同義）：本地用語優先，目標 20 頁（`--phrase-gap-pages`）。
- `reading`（讀音分化）：兩邊權重都不動，只在 0 權重時給下限；用來處理 `妳/嬭`、`洒/灑`、`台/臺`。

可用 `--variant-cap`、`--rare-cap`、`--phrase-gap-pages` 調整。

## MOE 檢查清單

`tools/moe_check.tsv` 由 `tools/moe_check.py` 從 `essay_pairs.tsv` 產生（1,426 列，破音字會有多個讀音列），
每列包含 `preferred`、`variant`、讀音，以及 lisp／flypy 的輸入碼。

用法：`grep '^為' tools/moe_check.tsv`，照 `lisp_input`（或 `flypy_input`）輸入，
主形應該排在異體之前。

| 主形／異體 | 讀音 | lisp 輸入 | flypy 輸入 |
|---|---|---|---|
| 為／爲 | wei | `ww` | `ww` |
| 裡／裏 | li | `li` | `li` |
| 著／着 | zhe | `ae` | `ve` |
| 吃／喫 | chi | `ii` | `ii` |
| 麵／麪 | mian | `mk` | `mm` |
| 床／牀 | chuang | `ix` | `il` |
| 峰／峯 | feng | `fn` | `fg` |
| 群／羣 | qun | `qd` | `qy` |
| 眾／衆 | zhong | `ah` | `vs` |
| 啟／啓 | qi | `qi` | `qi` |
| 三／弎 | san | `ss` | `sj` |

數字的大寫：`參` 的 `san` 讀音原本在 luna 只有 0.01%，現在由 `reading_weights.tsv`
設成 `100%`，直接使用它的常用字權重（1,726）；`弎` 走異體帶（1,000）；`叁` 不在
ABCN 也不是對照組，維持 0。所以 `ss`／`sj` 的順序是 **三 > 參 > 弎 > 叁**。

想快速看幾個代表輸入：

| 輸入（lisp／flypy） | 預期順序 |
|---|---|
| `ss`／`sj` | 三 > 參 > 弎／叁 |
| `ww`／`ww` | 為 > 爲 |
| `li`／`li` | 裡 > 裏 |
| `ae`／`ve` | 著 > 着 |
| `ii`／`ii` | 吃 > 喫 |
| `mk`／`mm` | 麵 > 麪 |

## ABCN 罕用字

`extract_abcn.py` 從《臺灣TW-ABCN正字甲乙丙表》取出 A/B/C/N 四類。只有 **C 罕用字**
的異體會被額外後移（預設 10 頁，`--rare-gap-pages`）。目前 56 個 C 類異體，
例如 `怜`、`眀`；`爲`、`裏`、`着` 不在 ABCN 表內，維持原本的 3 頁。

## ABCN 表外的異體

ABCN 只收「正字」，異體多半不在表內。排除 `爲`、`裏`、`着`、`衆` 後，目前有
**1,194 個**異體不在 ABCN：

| 上游權重 | 數量 |
|---|---:|
| ≥1000 | 14 |
| 100–999 | 691 |
| 1–99 | 42 |
| 0 | 447 |

完整清單在 `tools/variants_not_in_abcn.tsv`（含 preferred、權重、民國教育部證據、來源）。
其中 1,019 個有民國教育部證據，175 個沒有。

**不要用「不在 ABCN」當成後移條件**：那會把 `爲`、`裏`、`着`、`衆` 這類常用異體一起推走。
現在所有單字異體都會進入固定帶（預設 1000）；其中被列在 **C 罕用字** 或 CJK 增補區的
再壓到 100 以下。常用字（A/B/N）不受影響。

## 電腦漢字字典的證據

`extract_evidence.py` 會讀《電腦漢字字典》mdx，對每個字對抓「異體字」段與來源標籤
（民國教育部、漢語大字典、戸籍統一文字、簡化字…），輸出：

- `evidence.tsv`：`preferred / variant / moe(yes/no) / sources / note`
- `evidence_missing.tsv`：字典裡有民國教育部標籤、但不在 `essay_pairs.tsv` 的候選對

目前 1,330 個字對中，1,119 個有民國教育部證據；277 個候選對已篩選 170 個
（兩邊都在 essay）放進 `essay_pairs_review.tsv`，沒有自動套用。

需要 `readmdict`（或 `PYTHONPATH=/path/to/readmdict` 執行）。

## 破音字的讀音權重

`reading_weights.tsv` 的格式：

```
# char<TAB>pinyin<TAB>weight
參	san	100%
```

weight 可以寫絕對值（`20000`）或百分比（`100%`）。兩支字表產生器都會套用；
適合處理「同一個字在不同讀音要有不同權重」的情況。

## 看報告

`tools/essay_report.txt` 會列出：

- `added entries`：相對上游新增的條目數。
- `pairs applied`：套用成功的對照組。
- `char variants banded`：被放進異體帶的單字數。
- `phrase variants zeroed`：被設為 0 的詞形數。
- `conflicts`：同一個字同時是某組的主形、又是另一組的異體；這些組會跳過，避免方向反轉。
- `overshoot`：因同值區（tie block）無法精確切出 3 頁而超過目標的對照組。
  這是**全域名次**的差距；實際候選清單是同一個 code 的子集，通常會更近。
- `skipped`：兩邊都不存在於上游，直接跳過。
- `core characters still at weight 0`：核心字若仍為 0，會列在這裡。

同值區不只出現在 0/1；中頻（例如權重 500 附近）也可能有數百筆同值。
在「只調整既有權重、不重寫整份排序」的前提下，`overshoot` 是最佳解，不是錯誤。

## pacman hook

把 `tools/91-rime-essay-tw.hook` 複製到 `/etc/pacman.d/hooks/` 即可：

```bash
sudo cp tools/91-rime-essay-tw.hook /etc/pacman.d/hooks/
```

hook 在 `rime-essay` 安裝或升級後，以 `d0w0b` 身分執行 `tools/generate_essay.py`，
只重生 `essay.txt` 並印出訊息與「請重新部署 Rime」。
**不會**呼叫 `fcitx5-remote`、不會重啟輸入法。

移除：

```bash
sudo rm /etc/pacman.d/hooks/91-rime-essay-tw.hook
```

## 回滾

`essay.txt` 與兩張 dict 都在 git 內：

```bash
git checkout -- essay.txt flypy_quick5.dict.yaml flypy_quick5_phrases.dict.yaml
```

## 新增或調整對照組

1. 需要自動對齊的，加一行到 `tools/essay_pairs.tsv`。
2. 有疑慮的（破音字、假朋友），先放 `tools/essay_pairs_review.tsv`，確認後再搬。
3. 重跑 `tools/generate_essay.py` 與兩支 dict 腳本。
4. 執行 `python3 -m unittest discover -s tools/tests -v`。

## 已知限制

- 低頻與中頻都有大量同值，全域名次差無法精確做到 3 頁；報告會列在 `overshoot`。
- `essay.txt` 是 git tracked；hook 重生後會讓 repo 顯示 modified，需自行 commit。
- `.gram` 語言模型不會隨 essay 重生。
- 只處理字形與已存在詞形的權重，不新增未經核可的詞彙。
- MOE 的使用者造字區（PUA 與 `&xxxx._104_0.gif` 佔位字）已在抽取時排除。
