# rime-essay-tw

從 pacman 維護的 `/usr/share/rime-data/essay.txt` 重生一份「台灣字形優先、但保留異體與跨區用語」的
`essay.txt`，並用同一套資料產生 flypy 的字表與詞組表。

## 檔案

| 檔案 | 用途 |
|---|---|
| `essay_pairs.tsv` | 已核可的對照表（`preferred / variant / scope / type / source / note`） |
| `essay_pairs_review.tsv` | 待人工確認的對照表（預設不套用） |
| `generate_essay.py` | 重生 `essay.txt` 與 `essay_report.txt` |
| `generate_flypy_quick5.py` | 產生 `flypy_quick5.dict.yaml`（字表） |
| `generate_flypy_quick5_phrases.py` | 產生 `flypy_quick5_phrases.dict.yaml`（詞組） |
| `rime-essay-tw` | 包裝器；pacman hook 呼叫它，只印提示不重新部署 |
| `install-hook.sh` | 安裝／移除 pacman hook（需要 root） |

## 手動重生

```bash
cd ~/.local/share/fcitx5/rime
python3 generate_essay.py \
    --essay /usr/share/rime-data/essay.txt \
    --pairs essay_pairs.tsv \
    --out essay.txt \
    --report essay_report.txt
python3 generate_flypy_quick5.py
python3 generate_flypy_quick5_phrases.py
```

接著手動重新部署 Rime（重新啟動 fcitx5，或使用選單的「部署」）。

## 對照表的類型

- `ortho`（同詞異寫）：主形與異體都保留，全域名次差目標 15 名（約 3 頁）。
- `regional`（跨區同義）：主形與另一區用語都保留，目標 30 名（約 6 頁）。
- `reading`（讀音分化）：兩邊權重都不動，只在 0 權重時給下限；用來處理 `妳/嬭`、`洒/灑`、`台/臺`。

## 看報告

`essay_report.txt` 會列出：

- `pairs applied`：套用成功的對照組。
- `overshoot`：因低頻同值區（tie block）無法精確切出 3 頁而超過目標的對照組。
  這是**全域名次**的差距；實際候選清單是同一個 code 的子集，通常會更近。
- `skipped`：兩邊都不存在於上游，直接跳過。

## pacman hook

安裝（root）：

```bash
sudo ./install-hook.sh
```

移除：

```bash
sudo ./install-hook.sh --uninstall
```

hook 只在 `rime-essay` 安裝或升級後執行 `/usr/local/bin/rime-essay-tw`；
它會以各使用者身分重生 `essay.txt`，然後印出「請重新部署 Rime」。
**不會**呼叫 `fcitx5-remote`、不會重啟輸入法。

## 回滾

`essay.txt` 與兩張 dict 都在 git 內：

```bash
git checkout -- essay.txt flypy_quick5.dict.yaml flypy_quick5_phrases.dict.yaml
```

第一次手動重生前建議先備份 `essay.txt`。

## 新增或調整對照組

1. 需要自動對齊的，加一行到 `essay_pairs.tsv`。
2. 有疑慮的（破音字、假朋友），先放 `essay_pairs_review.tsv`，確認後再搬。
3. 重跑 `generate_essay.py` 與兩支 dict 腳本。
4. 執行 `python3 -m unittest discover -s tests -v`。

## 已知限制

- 低頻區有大量同值（權重 0、1 各有數千到數萬條），全域名次差無法精確做到 3 頁；
  報告會列在 `overshoot`。
- `essay.txt` 是 git tracked；hook 重生後會讓 repo 顯示 modified，需自行 commit。
- `.gram` 語言模型不會隨 essay 重生。
- 只處理字形與已存在詞形的權重，不新增未經核可的詞彙。
