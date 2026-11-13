# 腳本與產出手冊

這份文件說明 `tools/` 下每支腳本、它的輸入、輸出，以及哪些檔案只在上游更新時才需要。
日常使用只要看 [README-essay-tw.md](README-essay-tw.md)；這裡是維護與重新產生資料時的參考。
檔案從哪裡來、hook 會改哪些檔，見 [SOURCES.md](SOURCES.md)。

## 1. 執行環境

| 用途 | 需求 |
|---|---|
| Rime 執行 | `librime`、`fcitx5-rime`（或 ibus-rime） |
| 產生 essay／dict | Python 3.11+，只用標準庫 |
| pacman hook | `runuser`、`logger`、`flock`、`curl`（抓上游 essay） |
| `extract_opencc_pairs.py` | Python `opencc` 套件（或系統 `opencc`） |
| `extract_evidence.py` | Python `readmdict` 套件 |
| `extract_moe_pairs.py`／`extract_abcn.py` | 原始 xlsx（Downloads） |
| Rime 八股文模型 | `zh-hant-t-essay-bgw.gram`、`bgc.gram`（來源：`lotem/rime-octagram-data` release） |

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
Exec = /usr/bin/runuser -u d0w0b -- /home/d0w0b/.local/share/fcitx5/rime/tools/update_essay.sh
```

- 只在 `rime-essay` 安裝／升級後執行。
- 以 `d0w0b` 身分寫入，避免 root 擁有的檔案。
- **優先抓上游** `https://raw.githubusercontent.com/rime/rime-essay/master/essay.txt`；
  失敗、逾時或格式不合理時退回 pacman 的 `/usr/share/rime-data/essay.txt`，
  不讓套件升級失敗。
- **不呼叫** `fcitx5-remote`、不重啟輸入法；只印出「請重新部署 Rime」。
- 需要：`update_essay.sh`、`generate_essay.py`、`essay_lib.py`、`essay_pairs.tsv`、
  `abcn.tsv`、`curl`、`flock`；退回模式另需 `/usr/share/rime-data/essay.txt`。
- 產出：根目錄 `essay.txt`、`tools/essay_report.txt`。

### `update_essay.sh`

```bash
bash tools/update_essay.sh [--source auto|upstream|system] [--dry-run]
# 預設 source=auto：先抓上游，失敗才用 pacman 版本
```

- `auto`：抓上游，失敗或不合法就退回 pacman 版本。
- `upstream`：抓不到就失敗，適合手動確認上游狀況。
- `system`：只用 pacman 版本，適合離線或比對。
- `--dry-run`：只顯示會用哪個來源，不寫檔。
- `RIME_ESSAY_URL` 可覆寫下載位置。
- 驗證：檔案 ≥ 1 MB、≥ 300,000 行、每行都是 `字詞<TAB>數值`。
- 先寫到暫存檔，成功後才 `mv` 覆蓋，避免留下半份 `essay.txt`。

### `91-rime-sources.hook`

`rime-cangjie`／`rime-luna-pinyin` 更新時，把系統 dict 同步回 repo 並重生四張表。

```ini
[Trigger]
Operation = Install
Operation = Upgrade
Type = Package
Target = rime-cangjie
Target = rime-luna-pinyin

[Action]
Description = Updating rime source dicts（更新倉頡／拼音來源）
When = PostTransaction
Exec = /usr/bin/runuser -u d0w0b -- /home/d0w0b/.local/share/fcitx5/rime/tools/update_sources.sh
```

- `cangjie5.dict.yaml`、`cangjie5.schema.yaml`：直接複製系統檔，逐字一致。
- `luna_pinyin.dict.yaml`：以系統檔合併（`tools/merge_source_dict.py`），
  再套用 `tools/dict_overrides.tsv` 的讀音權重。
- 接著重生 `flypy_quick5`、`lisp_quick5` 字表與詞組表。
- 不自動 commit；hook 只印出 `git diff --stat` 與提示。
- 手動預覽：`bash tools/update_sources.sh --dry-run`。

### `merge_source_dict.py`

```bash
python3 tools/merge_source_dict.py LOCAL UPSTREAM OUT [OVERRIDES]
```

- 檔頭與條目都取上游。
- 條目以上游順序為主；同一個（字, 碼）以上游為準。
- 只存在本地的非 PUA 條目附加在最後，所以更新不會刪掉自訂字。
- 只存在本地的 PUA 條目直接丟棄（上游已改用部首）。
- 有 `OVERRIDES` 時，依 `dict_overrides.tsv` 覆寫（字, 碼）的權重。
- 相同輸入重跑結果不變（冪等）。

### `dict_overrides.tsv`

字典層的本地差異，因為 `*.custom.yaml` 只能修補 schema／config，不能修補 `.dict.yaml`。

```
# 檔案	字	碼	權重
luna_pinyin.dict.yaml	暫	zhan	-
```

- 教育部《重編國語辭典》以 `ㄓㄢˋ`（zhan）為「暫」的讀音，`ㄗㄢˋ`（zan）為又音。
- `luna_pinyin` 的 `use_preset_vocabulary: true` 會把 `essay.txt` 的 `暫 1820` 套到
  兩個讀音；系統版把 zhan 設成 `0%`，移除後兩者都是 1820。
- 權重寫 `-` 代表移除該欄，讓條目回到 essay 預設權重；也可以寫 `0%`、`100%`。


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
- 小鶴雙拼代碼 + 倉頡速成碼；權重預設複製 luna 的百分比，再用
  `tools/reading_weights.tsv` 覆寫特定讀音。
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
- 來源：<https://language.moe.gov.tw/001/Upload/Files/site_content/M0001/respub/index.html>
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
- 來源：<https://github.com/BYVoid/OpenCC>
- 需要 Python `opencc`。
- 輸出：`essay_pairs_opencc.tsv`（auto）與 `essay_pairs_opencc_review.tsv`（一對多）。
- 單字只取 `t2tw` 的 ortho 分支；多字詞只取 `t2tw` 不變、`s2twp` 有變的 regional 分支。
- 目標不存在於 essay/luna 的 regional 對會跳過。

### `extract_abcn.py`

- 輸入：《臺灣TW-ABCN正字甲乙丙表》xlsx（Downloads）。
- 來源：<https://github.com/TraditionalChinese/TW-ABCN>
- 輸出：`tools/abcn.tsv`（`char / A|B|C|N / 字號`）。
- 只讀 ABCN 工作表；`C` 類與 CJK 增補區會被 `generate_essay.py` 壓到 `rare_cap`。

### `extract_evidence.py`

- 輸入：《電腦漢字字典》mdx（OneDrive/Documents）。
- 來源：<https://fgwang.blogspot.com/2014/11/blog-post.html>
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

weight 可寫絕對值（`20000`）或百分比（`100%`）。目前固定 `100%` 的是
`參 san` 與 `零壹貳肆伍陸柒捌玖拾佰仟` 的正式讀音：luna 只給 `參 san` 0.01%，
`陸 liu` 6.25%、`拾 shi` 99.90% 也偏低；拉到 100% 後打 `san`／`liu`／`shi`
仍會排在前面。

## 7. 外部字典與可移除檔案

以下**不在執行期使用**，只在重新抽取對照資料時需要：

- 教育部《重編國語辭典》xlsx → 只給 `extract_moe_pairs.py`
  <https://language.moe.gov.tw/001/Upload/Files/site_content/M0001/respub/index.html>
- 《臺灣TW-ABCN正字甲乙丙表》xlsx → 只給 `extract_abcn.py`
  <https://github.com/TraditionalChinese/TW-ABCN>
- 《電腦漢字字典》mdx → 只給 `extract_evidence.py`
  <https://fgwang.blogspot.com/2014/11/blog-post.html>
- `zh-*.gram` → Rime 執行期的八股文模型，來自
  <https://github.com/lotem/rime-octagram-data>；**不隨套件打包**，由使用者依需求下載。

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
| `tools/update_sources.sh`、`tools/merge_source_dict.py` | **不可** | sources hook 需要 |
| `tools/update_essay.sh` | **不可** | essay hook 需要 |
| `tools/dict_overrides.tsv` | **不可** | sources hook 需要（字典權重覆寫） |
| `cangjie5.dict.yaml`、`cangjie5.schema.yaml` | **不可** | 系統檔複本；sources hook 會覆蓋 |
| `luna_pinyin.dict.yaml` | **不可** | 系統檔合併＋overrides；sources hook 更新 |
| 根目錄 `essay.txt`、四張 dict | 不可 | Rime 需要 |

hook 更新 essay 時只會覆寫 `essay.txt` 與 `essay_report.txt`；不會動
`essay_pairs.tsv`、`abcn.tsv`、`reading_weights.tsv` 或兩張 dict。
sources hook 會複製 `cangjie5.dict.yaml`／`cangjie5.schema.yaml`、合併
`luna_pinyin.dict.yaml`，並重生四張表。

### `package_rime.sh`

只把 Rime 真正需要的檔案複製到一個輸出目錄（CI 的 artifact）。

```bash
bash tools/package_rime.sh [OUT_DIR] [all|flypy|lisp] [desktop|mobile]
# 預設 OUT_DIR=dist/rime-config、VARIANT=all、PLATFORM=desktop
```

- `all`：全部 schema。
- `flypy`：只含 flypy 群組；`default.custom.yaml` 只留 `flypy_quick5`。
- `lisp`：只含 lisp 群組；`default.custom.yaml` 只留 `lisp_quick5`。
- `desktop`：保留 latex；不加 `trime.custom.yaml`／`hamster.app.yaml`。
- `mobile`：套用 `tools/mobile/*.custom.yaml`，移除 latex 與 `extended_charset`／`ascii_punct`，
  加入 `trime.custom.yaml`、`hamster.app.yaml`、`cangjie5.schema.yaml`，不打包 `latex.*`。
- **不打包 `.gram`**；八股文模型由使用者依需求從
  <https://github.com/lotem/rime-octagram-data> 下載（hant 或 hant+hans）。

手機 overlay 檔案：

- `tools/mobile/flypy_quick5.custom.yaml`
- `tools/mobile/lisp_quick5.custom.yaml`

兩者都會把 `schema/dependencies` 收斂成 `cangjie5`（flypy），並在 `switches` 只留下
`t2s`、`full_shape`、`ascii_mode`、`cangjie_comment`。

打包內容：

- `essay.txt`
- `grammar.yaml`
- `*.schema.yaml`
- `*.dict.yaml`
- `*.custom.yaml`
- `rime.lua`
- `lua/`
- `LICENSE`
- `*.gram`（至少要有 `zh-hant-t-essay-bgw.gram`、`zh-hant-t-essay-bgc.gram`）

不會包含 `tools/`、`tests/`、`docs/`、`build/`、`*.userdb`、`sync/`、
`installation.yaml`、`user.yaml`。

CI 在 `.github/workflows/package.yml`：
先跑測試，再產生四個包：desktop 的 `all`／`flypy`／`lisp` 與 mobile 的 `all`。
`.gram` 不打包，模型由使用者自行下載。

## 8. 測試

```bash
cd ~/.local/share/fcitx5/rime
python3 -m unittest discover -s tools/tests -v
```
