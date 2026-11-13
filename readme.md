# About

小鶴雙拼的音碼＋倉頡第五版速成的形碼的 Rime 繁體中文輸入方案。
兩個輸入法都是輸入 2 碼出字，打字上的節奏感很一致，但都有個共同的缺點，很常出現需要選字的情況。
兩者一起使用可以大幅降低需要選字的情況，前兩碼為雙拼後兩碼為速成，同時也讓用戶不至於忘記中文字長怎樣。

原版的小鶴音形是發明新的形碼來拆解簡體中文字，對繁體字用戶來說有幾個問題：

1. 額外的拆字規則學習成本跟難度，規則夠不夠完善，教學文件夠不夠充分等。
2. 簡體轉繁體非一對一，很多是一對多。
3. 打字上不直覺，在腦中要先建立簡繁的對應關係。

因此，在設計此方案時，形碼的輸入法選擇上，便是從那些已經長時間存在，教學資源遍地都是的輸入法裡開始挑選。
最終採用速成是因為規則夠簡單，倉頡的字根數量相較於嘸蝦米、行列來說很少，加上優秀跨平台特性，
幾乎各平台有倉頡便會有速成，熟悉此輸入法後，即使只用其中一種應該都不會有太大問題。

## 方案檔案

| 檔案                       | 說明                                                                 |
| -------------------------- | -------------------------------------------------------------------- |
| `flypy_luna.schema.yaml`   | 小鶴雙拼基礎設定（轉譯成 Luna 拼音）                                 |
| `flypy_self.schema.yaml`   | 轉換後字碼表，不經過轉譯                                             |
| `flypy_quick5.schema.yaml` | 小鶴雙拼＋速成（flypy 主方案）                                       |
| `lisp.schema.yaml`         | 自製闊碼雙拼（符合 Colemak-DH 鍵位的雙拼方案，改自大牛雙拼）基礎設定 |
| `lisp_quick5.schema.yaml`  | 闊碼雙拼＋速成（lisp 主方案）                                        |

`default.custom.yaml` 的 `schema_list` 預設是 `lisp_quick5` 與 `flypy_quick5`。
`latex.schema.yaml` 提供 LaTeX 輸入，`cangjie5.dict.yaml` 提供倉頡反查。

# 預設配置

## 按鍵輸入提示

- flypy：小鶴雙拼的鍵位和倉頡字根。
- lisp：闊碼雙拼的鍵位和倉頡字根。

# 其它功能

## 繁體異體字與字頻

Rime 的字頻來自 `essay.txt`。上游 `rime-essay` 以異體字為主（`爲`、`裏`、`着`、`衆`），
而且 pacman 更新後會覆蓋；本 repo 不直接改上游，而是用 `tools/generate_essay.py`
從上游重生一份 `essay.txt`：

- 常用字（ABCN A/B/N）保留原權重；只有原本是 0 的抬到 1。
- 單字異體放進 0.2–0.9 的窄帶（例如 `爲`、`僞`、`着`）；C 罕用／CJK 增補上限 0.1。
- 詞的異體寫法直接設 0；跨區詞保留 20 頁差距。
- 讀音分化（`妳/嬭`、`洒/灑`、`台/臺`）兩邊不動。

所以 `wei` 會是 **為 > 未 > 位 > 味 > 衛 > 偽 > 慰 > 爲/僞 > 罕用字**；
異體仍然查得到，但不會蓋過常用字。

完整規則、對照表與可調參數見 [tools/README-essay-tw.md](tools/README-essay-tw.md)，
每支腳本的用法見 [tools/SCRIPTS.md](tools/SCRIPTS.md)。

### 為什麼不用 `t2tw`

`t2tw` 會把異體轉成標準字，再被 `uniquifier` 當成重複候選刪掉（例：`爲` 轉成 `為` 後與 `為` 重複），
異體等於被拋棄。現在仍然不使用 `t2tw`；改用 essay 權重分層，讓異體保留、排在後面。
簡體模式（`t2s`）保留，`着` 在簡體模式不會被誤轉成 `著`。

## 自製闊碼雙拼（lisp）

`lisp.schema.yaml` 與 `lisp_quick5.schema.yaml` 是自製的闊碼雙拼
（Colemak-DH 大牛雙拼）＋倉頡速成；字表與詞組表由
`tools/generate_lisp_quick5.py`、`tools/generate_lisp_quick5_phrases.py` 產生。
詞組表也會套用字對（例如 `着實`→`著實`），所以 `aoei` 可以打到 `著實`。

## 倉頡反查

在 lisp/flypy 下輸入 `` `c `` 進入倉頡反查，接著輸入倉頡碼：

- `` `c ``：只顯示 `` `c〔倉頡〕 `` 提示，沒有候選。
- `` `ca ``：`a` 對應的候選（日、曰、昌…）。
- `cangjie_comment` 開關切換「字根／字母」：字根模式顯示 `中中`、`卜口`，字母模式顯示 `ll`、`yr`。

## 八股文語言模型（octagram）

`grammar.yaml` 定義 `zh-hant-t-essay-bgw`／`bgc`（以及 hans 版）；
`lisp_quick5.custom.yaml`、`flypy_quick5.custom.yaml` 以 `__include: grammar:/hant` 載入。
模型來自 [lotem/rime-octagram-data](https://github.com/lotem/rime-octagram-data)，
是 release asset，且被 `.gitignore` 忽略。

模型**不隨套件打包**，請依需求自行下載：

- 只要繁體：`hant` 分支／release 的 `zh-hant-t-essay-bgw.gram`、`zh-hant-t-essay-bgc.gram`。
- 也要簡體：再加 `zh-hans-t-essay-bgw.gram`、`zh-hans-t-essay-bgc.gram`。

放到 Rime 使用者目錄即可。下載位置：
<https://github.com/lotem/rime-octagram-data>

## 建置與維護

重生 essay 與字典：

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

接著重新部署 Rime（重新啟動 fcitx5，或使用選單的「部署」）。

`rime-essay` 更新時，pacman hook `tools/91-rime-essay-tw.hook` 會呼叫
`tools/update_essay.sh` 重生 `essay.txt`：

- **優先抓上游** [rime/rime-essay](https://github.com/rime/rime-essay) 的 `essay.txt`。
- 下載失敗或格式不合理時，**退回 pacman 的** `/usr/share/rime-data/essay.txt`，
  不會讓套件升級失敗。
- 只印出提示、不會呼叫 `fcitx5-remote`。

pacman `extra` 的 `rime-essay` 目前停在 2025-02，落後上游（2026-11），所以預設抓上游。
手動執行：

```bash
bash tools/update_essay.sh --dry-run            # 看會用哪個來源
bash tools/update_essay.sh                      # 抓上游並重生
bash tools/update_essay.sh --source system      # 強制用 pacman 版本
bash tools/update_essay.sh --source upstream    # 抓不到就失敗，不退回
```

差別只在頻率來源；`essay_pairs.tsv`、`reading_weights.tsv` 與三層權重規則不變。
`essay.txt` 是 tracked 產物，重生後需自行 commit。

`rime-cangjie`／`rime-luna-pinyin` 更新時，`tools/91-rime-sources.hook` 會同步來源並重生
四張表：

- `cangjie5.dict.yaml`、`cangjie5.schema.yaml`：**直接複製系統檔**，逐字一致，不保留本地差異。
- `luna_pinyin.dict.yaml`：以系統檔合併，再套用 `tools/dict_overrides.tsv`
  （目前只移除系統版的 `暫 zhan 0%`）。
- 之後重生 `flypy_quick5`、`lisp_quick5` 字表與詞組表。

不自動 commit。手動預覽與套用：

```bash
bash tools/update_sources.sh --dry-run
bash tools/update_sources.sh
```

安裝兩個 hook：

```bash
sudo cp tools/91-rime-essay-tw.hook tools/91-rime-sources.hook /etc/pacman.d/hooks/
```

CI（`.github/workflows/package.yml`）會跑測試並打包四個 artifact（不含 `.gram`）：

- `rime-config-desktop-all`
- `rime-config-desktop-flypy`
- `rime-config-desktop-lisp`
- `rime-config-mobile-all`

桌面版保留 latex、`cangjie_comment` switch；手機版套用 `tools/mobile/` overlay，
移除 latex 與 `extended_charset`／`ascii_punct`，加入 `trime.custom.yaml`、
`hamster.app.yaml`、`cangjie5.schema.yaml`，不打包 `latex.*`。手機只產 `all`，不再分 flypy／lisp。

手機差異只存在 `tools/mobile/` 與手機 UI 檔，不再需要 `hamster` 分支。

## 部署方式：桌面用 repo、手機用 release

建議 **hybrid**：

| 環境 | 來源 | 更新方式 |
|---|---|---|
| 桌面（`~/.local/share/fcitx5/rime`） | git repo + pacman hook | `git pull` 後重新部署；來源套件更新由 hook 重生 |
| 手機（Trime／Hamster） | `rime-config-mobile-all` release | 下載解壓覆蓋使用者目錄 |

桌面不建議改用 release 覆蓋，因為 repo 內有些**無法從上游還原**的本地狀態：

- `cangjie5.dict.yaml` 現在是系統檔的逐字複本，沒有本地差異。
- `essay.txt` 是重生產物，不是上游原始檔
- `luna_pinyin.dict.yaml` 對 `暫 zhan` 的權重調整（`tools/dict_overrides.tsv`）
- 自己的 `*.custom.yaml`、`tools/`、pacman hook 都依賴 repo 路徑

release 解壓會直接蓋掉這些差異，而且 hook 的 `Exec` 綁定 repo 路徑。
手機端沒有這些 hook 與本地修改，`mobile-all` 一次覆蓋即可。

同時：桌面維持 repo，release 只服務手機與乾淨安裝。

檔案來源、hook 與系統檔的完整對照，見 [tools/SOURCES.md](tools/SOURCES.md)。

## 個人 fork 的 PR

這個 repo 是 `qo0u0op/rime`，fork 自上游 `JeffChien/rime-flypyquick5`。
在 GitHub 開 PR 時，**base repository 要選 `qo0u0op/rime`（base: `main`）**；
不要使用預設的 upstream，否則會把個人設定送到原作者。

```bash
git push -u origin feat/rime-essay-tw
gh pr create --repo qo0u0op/rime --base main --head feat/rime-essay-tw
```

或在網頁使用：

```
https://github.com/qo0u0op/rime/compare/main...feat/rime-essay-tw?expand=1
```

### 已知邊界

- 常用字的冷門讀音仍受 luna 百分比影響（例如 `三` 的 `sa` 讀音是 0%）；權重帶保證的是該字的主要讀音。
- 只有字表裡真的有的異體字才打得出來；其他台灣用字差異（`祇/衹`、`註/注`、`盡/儘`）與詞彙差異
  （`軟件/軟體`、`光盤/光碟`）不在自動處理範圍。
- 簡體模式（`t2s`）下異體字會被簡化：`爲→为`、`纔→才`、`裏→里`、`衆→众`，這是預期行為。
- 簡體字的倉頡碼本來就不準（例如 `发`），不在此處理範圍。
- 不再套 OpenCC 的相容漢字正規化：`cangjie5.dict` 有 15 個相容區字元（U+F92C、U+FA0E…），
  `extended_charset` 關閉時會被 `cjk_minifier` 濾掉；開「增廣」後反查才會出現。
- `.gram` 是 release asset，不進 git；`essay.txt` 與四張 dict 是 tracked 的產物，
  hook 重生後需自行 commit。

# 學習資源

[雙拼練習](https://api.ihint.me/shuang/) 也是個不錯的練習網頁。
