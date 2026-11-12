# rime-essay-tw 設計文件

- 日期：2026-11-12
- 狀態：待核可
- 專案位置：`~/.local/share/fcitx5/rime`（既有 git `repo`（儲存庫））

## 1. 背景

- `rime-essay` 套件提供的 `/usr/share/rime-data/essay.txt`（442,799 條）以異體字為主：
  `爲` 211,329、`為` 684；`裏` 45,267、`裡` 11,636；`着` 94,513、`著` 4,115。
- 使用者目前用一份不再更新的 `essay.txt`（312,776 條）覆蓋它，導致 pacman 更新 `rime-essay` 後
  仍然使用舊資料。
- 現有 `flypy_quick5.dict.yaml` 是手動維護，且用百分比（`爲 1%`、`為 100%`）補償 essay 的偏差，
  兩層權重互相打架。
- lib rime 的實際權重是 `essay 權重 × dict 百分比`（`entry_collector.cc:CreateEntry`）；
  `%` 是「乘上 essay 值」，不是絕對值。

## 2. 目標

1. 以 `essay.txt` 為**唯一頻率來源**；`dict`（詞典）不再手調百分比。
2. 台灣字形（MOE 主形）優先，但**兩邊都保留**，候選順序差距約 **3 頁**（15 名）。
3. 破音字／讀音分化的異體關係**不自動對齊**，列人工清單。
4. `phrase`（詞）也要處理：字形詞與跨區用語分開對待。
5. pacman 更新 `rime-essay` 後自動重生，流程可重複執行、可回滾。

## 3. 非目標

- 不刪任何詞條、不做內容篩選。
- 不改寫既有 `key`（詞條鍵；不做字元轉換、不收斂簡體）。
- 不做詞彙替換（`軟件`→`軟體` 只調整權重，不取代）。
- 不改 `cangjie5.dict.yaml`、`luna_pinyin.dict.yaml` 等來源檔。

## 4. 名詞

| 名詞 | 定義 |
|---|---|
| `pair`（對照組） | `(preferred, variant, scope, type)`；`preferred` 為 MOE 主形 |
| `preferred`（主形／首選） | MOE 認定的正字，權重較高的一邊 |
| `variant`（異體／另一寫法） | 與主形同詞、但寫法不同的一邊 |
| `scope`（範圍） | `char`（單字）或 `phrase`（詞） |
| `ortho`（同詞異寫） | 同一個詞的不同字形，例：`爲/為`、`裏/裡`、`晒/曬` |
| `regional`（跨區同義） | 兩岸三地不同用語，例：`軟件/軟體`、`光盤/光碟` |
| `reading`（讀音分化） | 只在某些讀音／義項才是異體，例：`妳/嬭`、`洒/灑` |
| `gap`（名次差） | 兩者在全域權重排序中的名次差 |
| `tie block`（同值區） | 大量條目共用同一個權重的區段 |
| `overshoot`（超額差距） | 因同值區而超過 3 頁的差距 |
| `review`（待審清單） | 無法自動判定、留給人工決定的對照組 |

## 5. 曾考慮的做法

| | 做法 | 結果 |
|---|---|---|
| A | essay 單一來源，`dict`（詞典）權重全部跟 essay | **採用** |
| B | 保留 `dict` 百分比，essay 反推（`爲` ×100） | 會污染 cangjie/luna 等共用 essay 的 `schema`（輸入方案） |
| C | `hook`（pacman 鉤子）連 `dict` 百分比一起自動改 | 每次更新都動手調檔，風險最高 |

## 6. 資料來源

| 來源 | 用途 | 取得時機 |
|---|---|---|
| `/usr/share/rime-data/essay.txt` | 基礎頻率 | 每次 pacman 更新 |
| MOE `dict_revised_2015_20260929.xlsx` | 主形／異體對、注音、多音排序 | 離線抽取，結果 `commit`（提交） |
| OpenCC `TWVariantsPhrases` | 字形 `phrase`（詞）對 | 離線抽取 |
| OpenCC `TWPhrases` | 跨區 `phrase`（詞）對 | 離線抽取 |
| Unihan `kTraditionalVariant` ＋《通用規範漢字表》 | 覆蓋檢查（不當正字裁判） | 離線 |
| `luna_pinyin.dict.yaml`、`cangjie5.dict.yaml` | 產生 flypy `dict`（詞典） | 每次重生 |
| `essay_overrides.tsv` | 人工裁決（破音字、例外） | `commit`（提交） |

## 7. 產物

```
~/.local/share/fcitx5/rime/
├── generate_essay.py              # 依 pairs.tsv 重生 essay.txt
├── generate_flypy_quick5.py       # 字表
├── generate_flypy_quick5_phrases.py
├── essay_pairs.tsv                # 已審核的對照表
├── essay_pairs_review.tsv         # 待人工確認
├── essay_overrides.tsv            # 人工例外
├── tools/extract_moe_pairs.py     # 離線：MOE xlsx → pair 候選
├── tools/extract_opencc_pairs.py  # 離線：TWVariants/TWPhrases → pair 候選
├── essay_report.txt               # 每次重生的統計與警告
├── essay.txt                      # 產物（git `tracked`，已納入版本控制）
├── flypy_quick5.dict.yaml         # 產物
└── flypy_quick5_phrases.dict.yaml # 產物

/usr/local/bin/rime-essay-tw       # root wrapper（pacman hook 呼叫）
/etc/pacman.d/hooks/91-rime-essay-tw.hook
```

## 8. essay 演算法

### 8.1 前置

1. 讀上游 essay，key 重複時取 `max`。
2. 讀 `essay_pairs.tsv`；格式：

```
preferred<TAB>variant<TAB>scope<TAB>type<TAB>source<TAB>note
```

3. 以**原始**權重建立 `value -> rank`（權重到名次）索引（由大到小）。

### 8.2 對齊規則

| type（類型） | preferred（主形） | variant（異體） |
|---|---|---|
| `ortho`（同詞異寫） | `max(w_p, w_v)` | 名次 `rank(preferred) + 15` 的權重，且嚴格小於 preferred |
| `regional`（跨區同義） | `max(w_p, w_v)` | 名次 `rank(preferred) + 30`（6 頁） |
| `reading`（讀音分化） | **保持原值** | **保持原值**；只有原值為 0 時給 `floor`（下限值，`rank + 30`） |

- `page_size = 5`（取自 `build/default.yaml`），3 頁 = 15 名。
- 名次取全域排序；任何一個 code 的候選只會更少，所以實際差距 **≤ 3 頁**。
- **同值區（tie block）**：低頻區有大量同值（權重 0 有 66k 條、權重 1 有 5.3k 條）。
  當 preferred 落在這種區塊，`rank + 15` 仍會取到同一個值；此時 variant 取「嚴格小於 preferred
  的最大值」，差距可能超過 3 頁，寫入 `essay_report.txt` 的 `overshoot` 清單，不視為失敗。
- 高頻／中頻（權重 ≥ 100，約 37 萬條）可精確做到 3 頁。
- 為避免低頻區同值把順序壓死，對齊後的 variant 可用一位小數（librime 以 `std::stod` 解析）。
- 任一邊不存在時，用對方的權重建立缺的一邊（`reading` 類型除外）。
- 兩邊都是 0 時，`preferred` 給 `floor`（下限）10。

### 8.3 讀音判定（自動）

MOE xlsx 的 `異體字` 欄位是旗標（值為 `異體字`），真正的關係寫在 `釋義`：
`「X」的異體字`。抽取時：

1. 取所有 `異體字` 旗標非空、且 `釋義` 可解析出 `「X」的異體字` 的列，
   產生 `Pair(preferred=X, variant=字詞名)`。
2. 檢查同一個 `字詞名` 是否有 **非旗標列、且有注音**（`多音排序`／`注音一式`）。

| 情況 | 判定 |
|---|---|
| 只有旗標列（純異體，如 `爲`、`裏`、`曬`、`麪`、`牀`） | `ortho`（同詞異寫），自動 |
| 另有獨立讀音的列（如 `妳` 有 ㄋㄧˇ、`洒` 有 ㄘㄨㄟˇ/ㄒㄧˇ/ㄙㄚˇ、`台` 有 ㄊㄞ/ㄧˊ） | `review`（待審），預設 `reading`（讀音分化），只給 floor |

以 20260929 版實測：1,481 個旗標列、1,476 個唯一字；**1,421 個純異體**、**60 個有獨立讀音**。

`essay_pairs_review.tsv` 由人工看過後，把要對齊的搬進 `essay_pairs.tsv` 並改 type。

`essay_overrides.tsv` 永遠優先於自動判定，用來處理 MOE 未收錄的對（如 `着/著`）。

**pair 表的種子（第一次執行前）**：由 `tools/extract_moe_pairs.py`（MOE 20260929 xlsx）與
`tools/extract_opencc_pairs.py`（`TWVariants` 41 條字對、`TWPhrases` 818 條）產生
`essay_pairs_review.tsv`；其中 OpenCC 的 41 條字對與 MOE 的純異體對自動寫入
`essay_pairs.tsv`（標記 `source=auto`），其餘留 review。這確保第一版就涵蓋
`爲/裏/着/衆/麪/喫/牀/峯/羣`，不會出現「重生後反而翻轉」的問題。

### 8.4 phrase

實測本機 OpenCC 字典：`TWVariantsPhrases` 只有 **12 條**、`TWVariants`（字級）41 條、
`TWPhrases`（跨區）818 條。因此「phrase 只靠現成詞表」不可行，`裏面/裡面`、`爲了/為了`、
`喫飯/吃飯` 都不在詞表裡。

1. **字形 phrase（有條件的字元套用）**：
   對 `luna_pinyin` 片語與上游 essay 的多字詞，套用 **`essay_pairs.tsv` 已核可的 `ortho` 字對**，
   產生另一種寫法（例：`裏面`→`裡面`、`爲了`→`為了`、`喫飯`→`吃飯`）。
   - 只套已核可的字對，不套整個 OpenCC，避免 `一傢伙→一傢夥`。
   - 這也保留現有 `flypy_quick5.dict.yaml` 裡 859 個台灣詞形（s2tw 可重現 836 個）。
   - 兩邊都保留；essay 對齊 3 頁。
2. **跨區 `phrase`（詞）**：`TWPhrases` 818 條，只有 **一對一（1:1）、非 `identity`（前後相同）、
   且兩邊都在 essay 或 luna 存在**的條目自動套用（`regional`（跨區同義），6 頁）；
   一對多（43 條）與 identity（27 條）全部進 `review`（待審清單）。
3. **不做無條件的字元級轉換**；任何套用都必須來自已核可的 pair。
4. 一對多、假朋友（`質量/品質`、`支持/支援`）一律進 review，預設不動。

### 8.5 輸出

- 依 key 的 Unicode 碼位排序（與上游一致）。
- 同 key 只留一筆，取 `max`。
- 原子寫入：`essay.txt.tmp` → `rename`。
- 同時輸出 `essay_report.txt`：pair 數、新增數、差距超標清單、仍為 0 權重的字。

## 9. dict 生成

### 9.1 `generate_flypy_quick5.py`

照 `generate_lisp_quick5.py` 的模式：

- 來源：`luna_pinyin.dict.yaml`（單字）＋ `cangjie5.dict.yaml`。
- 小鶴雙拼代碼：使用 `flypy_luna.schema.yaml` 的 `algebra`（拼寫轉換規則），硬編碼在腳本內。
- 倉頡速成碼：`cangjie_quick()`（取首尾碼，沿用 lisp 版）。
- 輸出：`字<TAB>dp/cj`（`dp`＝雙拼碼、`cj`＝倉頡速成碼）；**權重欄位直接複製 luna 的百分比**（保留 `妳 nai 0% / ni 100%`
  這類讀音分化），沒有百分比就留空，由 essay 提供。
- 排序：`(字, code)`。

### 9.2 `generate_flypy_quick5_phrases.py`

- 來源：`luna_pinyin.dict.yaml` 的 `#以下爲詞組` 段。
- 每位字取所有 dp/cj 組合，用 `product`（笛卡兒積）展開。
- 輸出：`詞<TAB>dp/cj dp/cj ...`，無權重欄位。
- 額外：對每一條片語，套用 `essay_pairs.tsv` 的 `ortho` 字對，產生另一種寫法
  （`裏面`→`裡面`），再用同一組字碼規則輸出；兩邊都保留，由 essay 對齊權重。
  沒有對應字的片語不產生額外條目。

### 9.3 schema

`flypy_quick5.schema.yaml` 的 `translator` 增加：

```yaml
  import_tables:
    - flypy_quick5_phrases
```

## 10. pacman hook（鉤子）

`/etc/pacman.d/hooks/91-rime-essay-tw.hook`：

```ini
[Trigger]
Operation = Install
Operation = Upgrade
Type = Package
Target = rime-essay

[Action]
Description = Regenerating Taiwan-first rime essay（重生台灣優先的 essay）...
When = PostTransaction
Exec = /usr/local/bin/rime-essay-tw
```

`/usr/local/bin/rime-essay-tw`：

1. `flock` 防止重入。
2. 掃描 `/home/*/.local/share/fcitx5/rime`（以及 `~/.config/ibus/rime`）。
3. 以該使用者身分執行 `generate_essay.py`（`runuser -u`，避免 root 擁有產物）。
4. **只印出提示，不執行 `fcitx5-remote`**：

   ```
   [rime-essay-tw] 已更新 /home/d0w0b/.../essay.txt（442,799 → 448,201 條）
   [rime-essay-tw] 請重新部署 Rime（重新啟動 fcitx5，或使用選單的「部署」）
   ```

   同一段訊息同時寫入 stdout 與 `logger -t rime-essay-tw`，方便在 pacman 輸出與 journal 看到。
5. 不自動重啟或重新部署任何輸入法。

dict 的產生（flypy）不放在 hook：它依賴 `luna`／`cangjie` 本地檔，由使用者手動或 git hook 觸發。

## 11. 驗證

- `essay.txt` 筆數 ≥ 上游筆數（只增不減）。
- **最終產出**的全域名次差：`ortho` ≤ 15、`regional` ≤ 30；低頻同值造成的 `overshoot`
  只記錄、不視為失敗。
- 採用 **2 次迭代**（第一次用原始 `ranking`（名次表）算目標，第二次用產出 `ranking` 修正），
  避免批次移動造成的名次漂移。
- 同一輸入連跑兩次，輸出 `hash`（雜湊值）相同（`idempotent`，冪等）。
- `essay_report.txt` 沒有「仍為 0 權重」的核心字（爲/裏/着/衆/麵/喫/床/峰/群）。
- 手動部署後（重新啟動 fcitx5 或使用選單的 Deploy（部署）），測試 `為/爲`、`裡/裏`、`著/着` 的候選順序；
  另測 `ww`（2 碼）與 `wwif`（全碼）在 `code_order_filter`（碼長排序過濾）下的差異。
- `.gram`（語言模型）不隨 essay 重生，報告中註明；需要時另行重建。

## 12. 回滾

- 第一次執行前備份 `essay.txt` → `essay.txt.bak`。
- 產物都在 git 內，`git checkout -- essay.txt` 即可還原。
- hook 可用 `pacman` 的 `--noscriptlet`? 不需要；直接停用 hook 檔即可。

## 13. 風險

| 風險 | 對策 |
|---|---|
| 3 頁是全域近似，個別 code 可能更近 | 可接受（只會更近） |
| MOE 版本更新導致 pair 變動 | 抽取器輸出 diff，`essay_pairs.tsv` 人工核可 |
| essay 使用小數 | librime 支援；報告中標示 |
| `essay.txt` 是 git tracked（已納入版本控制），hook 會弄髒 `repo`（儲存庫） | 接受；必要時改成 `skip-worktree` |
| 低頻同值太多 | 取「嚴格小於」的值；超出 3 頁記入 `overshoot` |

## 14. 本次先以預設值實作

1. `regional` 預設 6 頁。
2. flypy 產物 commit 進 git（與現有 dict 一致）。
3. lisp 兩支腳本暫不改，只重生；日後再對齊。
4. MOE／OpenCC 抽取器在本次範圍內（產生 pair 種子與 review 清單）。
5. `reading` 的兩邊都保持原值，不取 max。
