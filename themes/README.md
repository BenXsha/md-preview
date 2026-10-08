# 主题 / Themes

md-preview 的主题就是**一个 CSS 文件**。渲染时会把主题文件以 `<link>` 原样引入，所以主题里引用自己目录下的
字体、图片都能正常加载；项目只在外围注入少量桥接与打印规则。

```console
$ md-preview --list-themes          # 自带主题 + 你添加的主题
$ md-preview --theme-dir            # 主题目录，把任意 .css 丢进去就成为一个主题
$ md-preview --install-theme <URL 或 .css 路径>
$ md-preview --theme default-dark FILE.md
```

## 自带主题（MIT，离线可用）

| 主题 | 说明 |
| --- | --- |
| `default` | 浅色；52 rem 正文宽度，类 GitHub 的代码块样式，中文字体栈 |
| `default-dark` | 深色；版式与 `default` 一致，PDF 里保留深色底 |

文件在 `src/md_preview/fallback.css`（= `default`）与 `src/md_preview/fallback-dark.css`（= `default-dark`），
安装时会在 `~/.config/md-preview/style.css` 放一份浅色版作为「主题缺失时的兜底样式」。你可以随意改这两个文件，
也可以复制一份改个名字放进主题目录。

## 可选主题集（需要显式拉取）

本仓库**不打包**第三方 CSS，也不替你分发。`--fetch-themes` 只会从上游仓库直接下载到你自己机器上，
并且只收录**许可明确**的来源：

| 主题集 | 上游 | 许可 |
| --- | --- | --- |
| `drake` | <https://github.com/liangjingkanji/DrakeTyporaTheme> | MIT, Copyright (c) 2023 劉強東 |
| `mdmdt` | <https://github.com/cayxc/Mdmdt> | Apache-2.0 |

```console
$ md-preview --fetch-themes drake mdmdt
```

上游仓库名里出现的编辑器名只是它的项目标识，与本项目没有隶属或背书关系；这里列出是为了满足
MIT/Apache-2.0 的署名要求。

其它主题请自行获取并确认许可，再用 `--install-theme` 安装：

```console
$ md-preview --install-theme ~/Downloads/some-theme.css
```

**该主题的许可由安装者自己确认。** 30 秒自查清单见 [`../docs/theme-licensing.md`](../docs/theme-licensing.md)。

## 主题要满足什么（DOM 契约）

这部分是兼容性接口，会保持稳定：

| 选择器 | 元素 |
| --- | --- |
| `#write` | 正文容器：`<div id="write" class="typora-export">` |
| `body.typora-export` | 页面根；判定为深色主题时会额外加 `md-dark` 类 |
| `pre.md-fences` | 代码块外壳：背景、边框、圆角、字体写这里 |
| `pre.md-fences > div.CodeMirror.cm-s-inner` | 代码块内层（有些主题的 `.cm-s-inner.CodeMirror { background: none }` 命中这里） |
| `.cm-keyword` `.cm-string` `.cm-comment` `.cm-def` `.cm-number` `.cm-variable` … | 语法 token 类名 |
| 普通元素 | `#write h1`、`p`、`table`、`blockquote`、`code`、`hr`、`img`、`ul/ol/li` |

> 关于 `typora-export` / `cm-s-typora-default` 这两个类名：它们是这套 CSS 约定里**既有的标识符**，
> 很多按该约定编写的主题用它做选择器，所以原样保留以维持兼容；它们只表示「遵循该 DOM 约定」，
> 与本项目、与任何编辑器都没有隶属关系。可以理解为协议里的一个字符串常量。

### 写一个主题的最小骨架

```css
/* my-theme.css — SPDX-License-Identifier: MIT */
@page { size: A4; margin: 18mm 16mm; }

body { background-color: var(--bg); color: var(--fg); }
#write { max-width: 48rem; margin: 0 auto; padding: 2rem 1.5rem; }

h1, h2 { border-bottom: 1px solid #ddd; }
.md-fences {
  background: #f6f8fa;
  border: 1px solid #ddd;
  border-radius: 6px;
  padding: .9em 1em;
  overflow-x: auto;
}
.cm-keyword { color: #a626a4; }
.cm-string  { color: #50a14f; }
```

三条实用经验：

1. **不要把 `cm-s-inner` / `CodeMirror` 加到 `<pre>` 上。** 有些主题带
   `.cm-s-inner.CodeMirror { background: none }`（特异性 0,2,0），会把 `.md-fences` 的底色抹掉。
   本项目把代码块做成两层嵌套，正是为了避开这个冲突。
2. **页面底色。** 有些主题把页面底色交给宿主应用，自己只定义 `--bg-color` 之类的变量。md-preview 检测到
   这种情况会补上 `body { background-color: var(--bg-color, …) }`，并把该主题按深色处理。
3. **非标准 at-rule 与宿主变量。** 部分主题带 `@include-when-export url(...)` 这类私有 at-rule，或者依赖
   宿主应用注入的变量 —— 浏览器会忽略取不到的东西，通常无需处理；如果主题靠私有变量取底色，按第 2 条加个
   默认值即可。

### 主题深浅是怎么判断的

`is_dark_theme()` 会解析主题里给 `html` / `body` / `#write` 设的页面背景色（支持 `var(--x)` 间接引用、
`html, body { }` 逗号选择器，跳过注释掉的声明与 `prefers-color-scheme: dark` 块，取变量的**首次**定义），
按亮度判断；解析不出来时才回退到按文件名猜（含 `dark`/`night`/`black`）。判定结果会影响：
内置代码高亮兜底配色的选用、代码块与行内代码的兜底底色、以及是否加 `md-dark` 类。

### 自己发布主题时

建议加一行 SPDX 头（`/* SPDX-License-Identifier: MIT */`）+ 一个 `LICENSE` 文件，并把字体/图片等子资源的
许可一并写明。这样别人用 `--install-theme` 装你的主题时，不需要猜许可。
