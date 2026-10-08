# 主题目录

md-preview 的主题就是一段 CSS。**本仓库不重新分发第三方主题**，只提供获取脚本，主题版权归各自作者。

```console
$ md-preview --fetch-themes            # 全部主题集
$ md-preview --fetch-themes typora     # 只拉某一个
$ md-preview --list-themes
$ md-preview --theme-dir               # 打印主题目录（默认 ~/.config/md-preview/themes/）
$ md-preview --install-theme ~/Downloads/my-theme.css
$ md-preview --theme my-theme FILE.md
```

## 内置目录

| 主题集 | 主题 | 上游 | 许可 |
| --- | --- | --- | --- |
| `typora` | `github` `gothic` `newsprint` `night` `pixyll` `whitey` `whitey-deep` | [typora/typora-default-themes](https://github.com/typora/typora-default-themes) | 上游仓库未声明开源许可（这些是 Typora 自带的默认主题），**仅供本地个人使用** |
| `drake` | `drake-ayu` `drake-black` `drake-dark` `drake-google` `drake-jb` `drake-juejin` `drake-light` `drake-material` `drake-purple` `drake-vue` `drake-white` … | [liangjingkanji/DrakeTyporaTheme](https://github.com/liangjingkanji/DrakeTyporaTheme) | MIT, Copyright (c) 2023 劉強東 |
| `mdmdt` | `mdmdt-light` `mdmdt-dark` | [cayxc/Mdmdt](https://github.com/cayxc/Mdmdt) | Apache-2.0 |

`--fetch-themes` 会连同主题的资源子目录（如 `github/*.woff2`、`gothic/*.woff`、`drake/font.css`）一起下载，
这样主题里的 `@font-face` / `@import` 相对路径才有效。

其他主题：Typora 官方画廊 <https://theme.typora.io/>，或 GitHub 搜 `typora theme`。
下载到的 `.css`（若带 `fonts/` 子目录请一并放到同名目录里）丢进 `md-preview --theme-dir` 的路径即可。

## 主题要满足什么

HTML 结构与 Typora 一致，因此 Typora 主题基本可以直接用：

| 选择器 | 元素 |
| --- | --- |
| `#write` | `<div id="write" class="typora-export">`，正文容器 |
| `body.typora-export` | 页面根；判定为深色主题时会额外加 `md-dark` |
| `pre.md-fences` | 代码块外壳（放背景、边框、圆角、字体） |
| `pre.md-fences > div.CodeMirror.cm-s-inner` | 代码块内层（主题的 `.cm-s-inner.CodeMirror { background: none }` 命中这里） |
| `.cm-keyword` `.cm-string` `.cm-comment` `.cm-def` `.cm-number` `.cm-variable` … | 语法 token 配色 |
| 普通元素 | `#write h1` / `p` / `table` / `blockquote` / `code` / `hr` / `img` |

内置的 `src/md_preview/fallback.css` 是一个最小可用的兜底主题，可以当模板抄。

## 坑与注意事项

- **不要**把 `cm-s-inner` 或 `CodeMirror` 加到 `<pre>` 上：很多主题里有
  `.cm-s-inner.CodeMirror { background: none }`（特异性 0,2,0），会盖掉 `.md-fences`（0,1,0）的底色。
- 主题里的页面底色常常只写在 `--bg-color` 变量里（Typora 的界面会用它涂背景，CSS 里并不给
  `body` 设 `background`）。这种主题单拿出来会变成「白底浅字」，md-preview 会补上
  `body { background-color: var(--bg-color, …) }`，并把主题判为深色。
- 主题可以按网页连续滚动来设计；md-preview 转 PDF 时会去掉 `#write` 的栏宽和内边距，
  改用 `@page` 控制页边距，避免在 A4 上挤成一条窄栏。
- 主题里的 `@include-when-export url(...)` 是 Typora 私有 at-rule，浏览器会忽略，无需处理。
- 主题若引用 Google Fonts 等在线字体，离线时会退回系统字体（中文通常落到 Noto Sans CJK）。
