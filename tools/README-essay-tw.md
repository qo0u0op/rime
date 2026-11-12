# rime-essay-tw

從 pacman 維護的 `/usr/share/rime-data/essay.txt` 重生一份「台灣字形優先、保留異體與跨區用語」的
`essay.txt`，並用同一套資料產生 flypy／lisp 的字表與詞組表。

Rime 只讀根目錄的資料檔；腳本、對照表、QA 與文件都放在 `tools/`。
每支腳本的參數與產出見 **[SCRIPTS.md](SCRIPTS.md)**。

## 根目錄（Rime 會讀）

| 檔案 | 用途 |
|---|---|
| `essay.txt` | 重生後的頻率表（hook 產生） |
| `flypy_quick5.dict.yaml` | flypy 字表 |
| `flypy_quick5_phrases.dict.yaml` | flypy 詞組表 |
| `flypy_quick5.schema.yaml` | flypy schema |
| `lisp_quick5.dict.yaml` | lisp 字表 |
| `lisp_quick5_phrases.dict.yaml` | lisp 詞組表 |
| `lisp_quick5.schema.yaml` | lisp schema |

### 自製闊碼雙拼（lisp）

`lisp.schema.yaml` 與 `lisp_quick5.schema.yaml` 是自製的**闊碼雙拼**
（Colemak-DH 大牛雙拼）＋倉頡速成；字表 `lisp_quick5.dict.yaml`、詞組表
`lisp_quick5_phrases.dict.yaml` 由 `tools/generate_lisp_quick5.py` 與
`tools/generate_lisp_quick5_phrases.py` 產生。`default.custom.yaml` 的
`schema_list` 目前是 `lisp_quick5` 與 `flypy_quick5`。

lisp 詞組表也會套用字對（例如 `着實`→`著實`），所以 `aoei` 可以打到 `著實`。

詞組表是在**字表的 dict 標頭**用 `import_tables` 載入，不是寫在 schema 的 `translator`：

```yaml
---
name: flypy_quick5
...
import_tables:
  - flypy_quick5_phrases
```

## tools/（不參與 Rime 執行）

| 檔案 | 用途 |
|---|---|
| `generate_essay.py` | 重生 `essay.txt` 與 `essay_report.txt` |
| `essay_lib.py` | 共用資料模型與排序／權重邏輯 |
| `generate_flypy_quick5.py`、`generate_flypy_quick5_phrases.py` | 產生 flypy 字表／詞組表 |
| `generate_lisp_quick5.py`、`generate_lisp_quick5_phrases.py` | 產生 lisp 字表／詞組表 |
| `essay_pairs.tsv` | 已核可的對照表（hook 需要） |
| `abcn.tsv` | ABCN 字類（hook 需要，決定罕用上限） |
| `reading_weights.tsv` | 破音字的讀音權重（重生 dict 時使用） |
| `essay_pairs_review.tsv` | 待人工確認的對照表 |
| `extract_*.py`、`xlsx_rows.py` | 從外部字典重新抽取對照（開發用） |
| `list_variants_not_in_abcn.py`、`moe_check.py` | 產生 QA 清單 |
| `package_rime.sh` | 只打包 Rime 需要的檔案（CI 使用） |
| `91-rime-essay-tw.hook` | pacman hook 本體 |
| `tests/`、`docs/` | 測試與設計文件 |

## 排序規則

**單字**（`char/ortho`）：

| 層級 | 權重 |
|---|---|
| 常用字（ABCN A/B/N，且不是異體/罕用） | 保留原權重；只有原本 0 的抬到 1 |
| 異體字 | 0.2–0.9 窄帶，依原權重與來源排序 |
| C 罕用／CJK 增補 | ≤0.1 |

例：`wei` 是 **為 > 未 > 位 > 味 > 衛 > 偽 > 慰（原 971）> 爲/僞（<0.9）> 罕用字**。

**詞**：

| 類型 | 規則 |
|---|---|
| `phrase/ortho`（同詞異寫） | 異體寫法設 0；主形保留權重（詞的碼重疊少，仍可從尾端找到） |
| `phrase/regional`（跨區同義） | 本地用語優先，差距 20 頁 |
| `reading`（讀音分化） | 兩邊不動；只在 0 權重時給下限 |

可調：`--variant-cap`（0.9）、`--rare-cap`（0.1）、`--phrase-gap-pages`（20）。

## MOE 檢查清單

`tools/moe_check.tsv` 由 `tools/moe_check.py` 從 `essay_pairs.tsv` 產生（約 1,434 列，
破音字會有多個讀音列）。每列包含 `preferred`、`variant`、讀音，以及 lisp／flypy 的輸入碼。

```bash
grep '^為' tools/moe_check.tsv
grep '^三' tools/moe_check.tsv
```

照 `lisp_input`（或 `flypy_input`）輸入，主形應排在異體之前：

| 主形／異體 | lisp | flypy |
|---|---|---|
| 為／爲 | `ww` | `ww` |
| 裡／裏 | `li` | `li` |
| 著／着 | `ae` | `ve` |
| 吃／喫 | `ii` | `ii` |
| 麵／麪 | `mk` | `mm` |
| 群／羣 | `qd` | `qy` |
| 眾／衆 | `ah` | `vs` |
| 三／弎 | `ss` | `sj` |

數字大寫：`參` 的 `san` 讀音由 `reading_weights.tsv` 設成 `100%`；`參` 的 MOE 異體是
`参`，`叁` 由《電腦漢字字典》的民國教育部證據補進對照。`ss`／`sj` 的順序是
**三 > 參 > 弎 > 参 > 叁**。

## 外部字典不在執行期

以下只用來**重新抽取**對照資料，Rime 與 hook 都不會讀：

- 教育部《重編國語辭典》xlsx → `extract_moe_pairs.py`
  <https://language.moe.gov.tw/001/Upload/Files/site_content/M0001/respub/index.html>
- 《臺灣TW-ABCN正字甲乙丙表》xlsx → `extract_abcn.py`
  <https://github.com/TraditionalChinese/TW-ABCN>
- 《電腦漢字字典》mdx → `extract_evidence.py`
  <https://fgwang.blogspot.com/2014/11/blog-post.html>

`essay_pairs.tsv`、`abcn.tsv`、`evidence.tsv` 產生並 commit 後，原始 xlsx／mdx 就可以移除。
`opencc`、`readmdict` 也只在抽取時需要。

## 八股文語言模型（octagram）

`grammar.yaml` 定義 `zh-hant-t-essay-bgw`／`bgc`（以及 hans 版）；
`lisp_quick5.custom.yaml`、`flypy_quick5.custom.yaml` 以 `__include: grammar:/hant` 載入。
模型來自 [lotem/rime-octagram-data](https://github.com/lotem/rime-octagram-data)，
是 release asset，且被 `.gitignore` 忽略。

Rime 使用者目錄需要：

- `zh-hant-t-essay-bgw.gram`
- `zh-hant-t-essay-bgc.gram`

（簡體模式另外需要 `zh-hans-*`。）CI 會下載 compact 版並改名成上面兩個檔名；
本機若已有 `.gram`，`package_rime.sh` 會直接帶入。

## CI 打包

`.github/workflows/package.yml` 在 push／PR／手動觸發時：

1. 跑 `tools/tests`。
2. 從 `rime-octagram-data` 的 release（`OCTAGRAM_TAG`）下載 compact 模型，
   改名成 Rime 預期的 `zh-*.gram`。
3. 執行 `tools/package_rime.sh`，只打包 Rime 需要的產物：
   `essay.txt`、`grammar.yaml`、`*.schema.yaml`、`*.dict.yaml`、`*.custom.yaml`、
   `rime.lua`、`lua/`、`LICENSE`、`.gram`。
4. 上傳 artifact `rime-config`。

不會打包 `tools/`、`tests/`、`docs/`、`build/`、`*.userdb`、`sync/`、
`installation.yaml`、`user.yaml`。

本機預覽：

```bash
bash tools/package_rime.sh dist/rime-config .
```

## pacman hook

```bash
sudo cp tools/91-rime-essay-tw.hook /etc/pacman.d/hooks/
```

hook 在 `rime-essay` 安裝或升級後，以 `d0w0b` 身分執行 `tools/generate_essay.py`，
只重生 `essay.txt` 並印出「請重新部署 Rime」。
**不會**呼叫 `fcitx5-remote`、不會重啟輸入法。

移除：

```bash
sudo rm /etc/pacman.d/hooks/91-rime-essay-tw.hook
```

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
python3 tools/generate_lisp_quick5.py
python3 tools/generate_lisp_quick5_phrases.py
```

接著手動重新部署 Rime（重新啟動 fcitx5，或使用選單的「部署」）。

## 可移除／可重生

| 檔案 | 說明 |
|---|---|
| `build/` | Rime 會重建 |
| `tools/essay_report.txt` | 每次重生覆蓋 |
| `tools/evidence*.tsv`、`variants_not_in_abcn.tsv`、`moe_check.tsv` | QA 快照，可刪 |
| `tools/extract_*.py`、`xlsx_rows.py` | 不再重新抽取時可刪 |
| `tools/tests/`、`tools/docs/` | 開發用 |
| `tools/essay_pairs.tsv`、`tools/abcn.tsv` | **hook 需要，不可刪** |
| `tools/generate_essay.py`、`tools/essay_lib.py` | **hook 需要，不可刪** |
| 根目錄 `essay.txt`、四張 dict | Rime 需要 |

完整說明見 [SCRIPTS.md](SCRIPTS.md#7-外部字典與可移除檔案)。

## 回滾

```bash
git checkout -- essay.txt flypy_quick5.dict.yaml flypy_quick5_phrases.dict.yaml \
  lisp_quick5.dict.yaml lisp_quick5_phrases.dict.yaml
```

## 新增或調整對照組

1. 要自動套用的，加一行到 `tools/essay_pairs.tsv`。
2. 有疑慮的（破音字、假朋友），先放 `tools/essay_pairs_review.tsv`，確認後再搬。
3. 重跑 `generate_essay.py` 與四支 dict 產生器。
4. 跑 `python3 -m unittest discover -s tools/tests -v`。

## 已知限制

- 常用字的**冷門讀音**仍受 luna 百分比影響（例如 `三` 的 `sa` 讀音是 0%）；權重帶保證的是
  該字的主要讀音。
- `essay.txt` 是 git tracked；hook 重生後會讓 repo 顯示 modified，需自行 commit。
- `.gram` 語言模型不會隨 essay 重生。
- 只處理字形與已存在詞形的權重，不新增未經核可的詞彙。
- MOE 的使用者造字區（PUA 與 `&xxxx._104_0.gif` 佔位字）已在抽取時排除。
