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
| `generate_lisp_quick5.py`、`generate_lisp_quick5_phrases.py` | 既有的 lisp 產生器（原樣移入） |
| `extract_moe_pairs.py`、`xlsx_rows.py` | 從 MOE xlsx 抽對照組 |
| `extract_opencc_pairs.py` | 從 OpenCC 抽對照組 |
| `essay_pairs.tsv` | 已核可的對照表 |
| `essay_pairs_review.tsv` | 待人工確認的對照表 |
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

- `ortho`（同詞異寫）：主形與異體都保留，全域名次差目標 15 名（約 3 頁）。
- `regional`（跨區同義）：主形與另一區用語都保留，目標 30 名（約 6 頁）。
- `reading`（讀音分化）：兩邊權重都不動，只在 0 權重時給下限；用來處理 `妳/嬭`、`洒/灑`、`台/臺`。

## 看報告

`tools/essay_report.txt` 會列出：

- `added entries`：相對上游新增的條目數。
- `pairs applied`：套用成功的對照組。
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
