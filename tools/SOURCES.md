# 檔案來源與 hook 關係

這份文件說明 repo 內的檔案從哪裡來、哪個 hook 會改它，以及和
`/usr/share/rime-data`（pacman 套件）的對應關係。

## 1. 目錄樹（依來源標記）

```
~/.local/share/fcitx5/rime/
├── essay.txt                          [生成] 上游 essay + tools/essay_pairs.tsv
├── cangjie5.dict.yaml                 [系統] /usr/share/rime-data 逐字複本
├── cangjie5.schema.yaml               [系統] 逐字複本
├── luna_pinyin.dict.yaml              [合併] 系統檔 + tools/dict_overrides.tsv
├── flypy_quick5.dict.yaml             [生成] luna + cangjie5 + pairs
├── flypy_quick5_phrases.dict.yaml     [生成]
├── lisp_quick5.dict.yaml              [生成]
├── lisp_quick5_phrases.dict.yaml      [生成]
├── flypy_luna.schema.yaml             [本地]
├── flypy_quick5.schema.yaml           [本地]
├── flypy_quick5.custom.yaml           [本地] 桌面客製（latex、cangjie_comment）
├── flypy_self.schema.yaml             [本地]
├── flypy_self.dict.yaml               [本地]
├── lisp.schema.yaml                   [本地]
├── lisp_quick5.schema.yaml            [本地]
├── lisp_quick5.custom.yaml            [本地]
├── default.custom.yaml                [本地] schema_list、switcher
├── grammar.yaml                       [本地] 八股文模型定義（不含 .gram）
├── rime.lua                           [本地]
├── lua/                               [本地]
├── latex.schema.yaml                  [本地] 桌面用
├── latex.dict.yaml                    [本地] 桌面用
├── trime.custom.yaml                  [本地] 手機 UI；桌面 Rime 忽略
├── hamster.app.yaml                   [本地] 手機 UI；桌面 Rime 忽略
├── zh-*.gram                          [下載] gitignore；不隨套件打包
├── build/                             [執行期] Rime 部署產物
├── dist/                              [執行期] package_rime.sh 輸出
├── *.userdb                           [執行期] 使用者學習紀錄
├── sync/                              [執行期] Rime 同步
└── tools/
    ├── 91-rime-essay-tw.hook          hook 1（需複製到 /etc/pacman.d/hooks）
    ├── 91-rime-sources.hook           hook 2（需複製到 /etc/pacman.d/hooks）
    ├── update_essay.sh                hook 1 的入口
    ├── update_sources.sh              hook 2 的入口
    ├── generate_essay.py              essay 產生器
    ├── essay_lib.py                   essay 共用邏輯
    ├── generate_flypy_quick5.py       flypy 字表
    ├── generate_flypy_quick5_phrases.py
    ├── generate_lisp_quick5.py        lisp 字表
    ├── generate_lisp_quick5_phrases.py
    ├── merge_source_dict.py           luna 合併
    ├── dict_overrides.tsv             luna 的本地權重差異
    ├── essay_pairs.tsv                已核可的字對
    ├── abcn.tsv                       ABCN 字類
    ├── reading_weights.tsv            破音字權重
    ├── mobile/*.custom.yaml           手機打包 overlay
    ├── package_rime.sh                CI／本機打包
    └── tests/                         單元測試
```

## 2. 三種來源關係

| 系統檔 | repo 檔 | 關係 |
|---|---|---|
| `/usr/share/rime-data/cangjie5.dict.yaml` | `cangjie5.dict.yaml` | **逐字複本**，沒有本地差異 |
| `/usr/share/rime-data/cangjie5.schema.yaml` | `cangjie5.schema.yaml` | **逐字複本** |
| `/usr/share/rime-data/luna_pinyin.dict.yaml` | `luna_pinyin.dict.yaml` | **合併＋覆寫**；唯一差異是 `dict_overrides.tsv` |
| `/usr/share/rime-data/essay.txt` | `essay.txt` | 只用來**重生**；預設抓上游，pacman 版當備援 |
| （無） | `flypy_*`、`lisp_*` 四張 dict | 由 luna＋cangjie5＋pairs **生成** |

`cangjie5.schema.yaml` 與系統相同，保留在 repo 是為了手機打包。
`cangjie5.dict.yaml` 保留在 repo 是為了：

- `generate_flypy_quick5.py`、`generate_lisp_quick5.py` 需要它當輸入。
- CI 的 `mobile-all` 需要把它放進手機包（Android 不一定有 `rime-cangjie`）。

檢查目前差異：

```bash
diff -q cangjie5.dict.yaml /usr/share/rime-data/cangjie5.dict.yaml
diff -u luna_pinyin.dict.yaml /usr/share/rime-data/luna_pinyin.dict.yaml
```

正常結果：cangjie 無輸出（一致）；luna 只有 `暫 zhan` 的權重差異。

## 3. Hook 對照

| Hook | Trigger | 入口 | 讀取 | 產出 | 網路 |
|---|---|---|---|---|---|
| `91-rime-essay-tw.hook` | `rime-essay` Install／Upgrade | `update_essay.sh` | 上游 `essay.txt`（失敗時 pacman 版）、`essay_pairs.tsv`、`abcn.tsv` | `essay.txt`、`tools/essay_report.txt` | 有，失敗自動退回 |
| `91-rime-sources.hook` | `rime-cangjie`、`rime-luna-pinyin` Install／Upgrade | `update_sources.sh` | 系統的三個 dict／schema、`dict_overrides.tsv`、`reading_weights.tsv`、pairs | `cangjie5.dict.yaml`、`cangjie5.schema.yaml`、`luna_pinyin.dict.yaml`、四張 flypy／lisp dict | 無 |

兩個 hook 都：

- 以 `d0w0b` 身分執行（`runuser`），避免 root 擁有檔案。
- **不**呼叫 `fcitx5-remote`、不重啟輸入法。
- **不**自動 commit；只留下 `git diff` 讓人工檢視。

hook 檔本身只是 repo 內的樣板，**修改後要重新複製**：

```bash
sudo cp tools/91-rime-essay-tw.hook tools/91-rime-sources.hook /etc/pacman.d/hooks/
```

## 4. Hook 不會碰的檔案

- 所有 `*.schema.yaml`（除 `cangjie5.schema.yaml`，它是系統複本）
- 所有 `*.custom.yaml`（桌面與 `tools/mobile/` 都算）
- `grammar.yaml`、`rime.lua`、`lua/`
- `latex.schema.yaml`、`latex.dict.yaml`
- `trime.custom.yaml`、`hamster.app.yaml`
- `tools/essay_pairs.tsv`、`abcn.tsv`、`reading_weights.tsv`（hook 只讀）
- `zh-*.gram`（由使用者自行下載）

## 5. 更新流程

```bash
# 1. 看 hook 會做什麼
bash tools/update_essay.sh --dry-run
bash tools/update_sources.sh --dry-run

# 2. 手動套用（pacman 升級時 hook 會自動跑）
bash tools/update_essay.sh
bash tools/update_sources.sh

# 3. 檢查、commit、重新部署 Rime
git diff
git add -A && git commit -m "chore: sync sources"
```

只想用 pacman 的 essay：

```bash
bash tools/update_essay.sh --source system
```

只想改 luna 的讀音權重：編輯 `tools/dict_overrides.tsv`，再跑 `update_sources.sh`。
