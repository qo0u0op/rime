# Mobile overlay

`tools/package_rime.sh ... mobile` copies these files over the desktop
`*.custom.yaml` in the mobile package:

- `flypy_quick5.custom.yaml`
- `lisp_quick5.custom.yaml`

They differ from the desktop customs in:

- 不載入 latex translator／segmentor／recognizer
- 不把 `\` 加進 `speller/alphabet`
- `schema/dependencies` 只留 `cangjie5`（flypy，移除 latex）
- `switches` 只留 `t2s`、`full_shape`、`ascii_mode`、`cangjie_comment`
  （移除 `extended_charset`、`ascii_punct`）

桌面版仍然使用根目錄的 `flypy_quick5.custom.yaml`／`lisp_quick5.custom.yaml`，
所以 latex 與 `cangjie_comment` 不受影響。
