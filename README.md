# md-preview

用 **Typora 主题**把 Markdown 渲染成排版好看的 **PDF / HTML**，专为「中键一点就能看」设计。

在 KDE/Dolphin 里，鼠标中键点一个 `.md` 会打开「该类型应用列表里的第 2 个应用」。默认情况下那个位置是
Okular —— 但 Okular 的 Markdown 后端只能改字体和 SmartyPants（见文末「为什么不是改 Okular 插件」），
于是长文档读起来是白底黑字的一整块。md-preview 顶到这个位置上：中键 → 带主题样式的 PDF → Okular。
样式可以换成任何 Typora 主题（纯 CSS），也能随时自己写。

```console
$ md-preview --theme newsprint 设计文档.md      # 生成带样式的 PDF 并用 Okular 打开（带缓存）
$ md-preview --html --theme drake-jb 设计文档.md # 或者直接在浏览器里看
```

## 特性

- **Typora 主题直接用**：Typora 主题是纯 CSS，项目把 HTML 结构对齐到 Typora 的 DOM
  （`#write` / `pre.md-fences` / `div.CodeMirror.cm-s-inner` / `.cm-*` token 类），主题文件原样投放即可生效，
  字体、配色、代码块、表格、引用块都跟着主题走。
- **代码高亮跟着主题走**：Pygments 输出的 token 同时带上 `cm-keyword` / `cm-string` / `cm-def` …
  等 CodeMirror 类名，主题自带的配色能命中；主题没定义配色时退回内置的 Pygments 深浅两套配色。
- **深浅色自动判断**：读取主题给 `html/body/#write` 设的页面底色（会跳过 `prefers-color-scheme: dark` 块、
  解析 `var(--bg-color)`、忽略注释）算出亮度，自动决定用浅色还是深色的兜底配色与代码块底色。
- **Print 修正**：主题是按网页连续滚动写的，转 PDF 时会去掉它的栏宽/内边距、改用 `@page` 控制页边距，
  并强制 `print-color-adjust: exact`，这样深色主题和代码块底色在 PDF 里不会丢。
- **缓存**：按「源文件 mtime + 脚本 + 主题文件 + 配置」做签名，内容没变时再次预览是**秒开**。
- **无 sudo**：全部落在用户目录（`~/.local/bin`、`~/.config/md-preview`、`~/.cache/md-preview`）。

## 安装

### 方式一：源码 + 安装脚本（推荐，附带 Dolphin 中键集成）

```console
$ git clone https://github.com/BenXsha/md-preview.git && cd md-preview
$ ./contrib/install.sh          # 装脚本 + 主题 + desktop 项 + mimeapps 顺序，全部用户级
$ ./contrib/install.sh --help   # 看看它到底会改哪些文件
```

`contrib/install.sh` 做的事：

1. `src/md_preview/cli.py` → `~/.local/bin/md-preview`（单文件，无包依赖，随拷随用）；
2. `src/md_preview/fallback.css` → `~/.config/md-preview/style.css`（只在文件不存在时写入，不覆盖你的修改）；
3. `--fetch-themes` 拉取主题（可选，也可以跳过稍后自己拉）；
4. 两个 desktop 项 → `~/.local/share/applications/`；
5. 在 `~/.config/mimeapps.list` 里把 Markdown 的处理器顺序排成
   **双击/回车 = 编辑器 → 中键 = md-preview → Shift+中键 = 浏览器预览 → 再后面 = 原来的 Okular**（先备份原文件）。

卸载：`./contrib/uninstall.sh`（会还原 `mimeapps.list` 备份）。

### 方式二：pipx / pip

```console
$ pipx install .                 # 或者 pip install --user .
$ md-preview --version
```

### 方式三：只要一个文件

```console
$ curl -O <raw-url>/src/md_preview/cli.py && install -Dm755 cli.py ~/.local/bin/md-preview
```

`cli.py` 是自包含的（只用标准库 + `markdown-it-py` + `Pygments`），拷到 `~/.local/bin` 就能用。

### 依赖

| 依赖 | 说明 |
| --- | --- |
| Python ≥ 3.10 | |
| `markdown-it-py` ≥ 3.0 | Markdown → HTML（GFM 表格 / 删除线 / linkify / 原始 HTML） |
| `Pygments` ≥ 2.14 | 代码高亮 |
| Chromium 系浏览器 | PDF 引擎，用 `--headless=new --print-to-pdf`。自动探测 Edge / Chrome / Chromium / Brave |
| Okular | 只看 PDF 时的阅读器（可换成 `zathura` 等，改脚本里的 `VIEWER_PDF`）；没有就退回浏览器 |
| Pillow（可选） | 只有 `tools/theme-gallery.py` 需要 |

## 主题

```console
$ md-preview --fetch-themes            # 拉取全部（官方默认 7 个 + Drake 11 个 + Mdmdt 2 个，含字体）
$ md-preview --fetch-themes typora     # 只拉某一个主题集
$ md-preview --list-themes
$ md-preview --theme-dir               # 把任意 .css 丢进这个目录就能用
$ md-preview --install-theme <URL 或 .css 路径>
```

已内置目录（下载到 `~/.config/md-preview/themes/`，本仓库**不重新分发**这些 CSS）：

| 主题集 | 来源 | 许可 |
| --- | --- | --- |
| `typora` 官方默认：`github` `gothic` `newsprint` `night` `pixyll` `whitey` `whitey-deep` | [typora/typora-default-themes](https://github.com/typora/typora-default-themes) | 上游未声明开源许可，仅供本地个人使用 |
| `drake` 系列 11 个：`drake-jb` `drake-dark` `drake-light` `drake-google` `drake-vue` … | [liangjingkanji/DrakeTyporaTheme](https://github.com/liangjingkanji/DrakeTyporaTheme) | MIT |
| `mdmdt`：`mdmdt-light` `mdmdt-dark` | [cayxc/Mdmdt](https://github.com/cayxc/Mdmdt) | Apache-2.0 |

挑主题用截图更快：

```console
$ python3 tools/theme-gallery.py            # 给每个主题截图，并拼成一张 _contact-sheet.png
```

输出在 `~/.cache/md-preview/gallery/`（另附每张单图）。实测 14 个主题的渲染结果两两不同：
深色 4 个（`night` 亮度 60 / `drake-dark` 44 / `mdmdt-dark` 35 / `whitey-deep` 40），浅色 10 个。

想看别人的主题：Typora 官方画廊 <https://theme.typora.io/> 里的主题基本都是单个 `.css`（少数带 `fonts/`
子目录），下载后 `md-preview --install-theme <文件>` 即可。

### 写自己的主题

主题就是一段 CSS，关键选择器（与 Typora 一致）：

| 选择器 | 对应元素 |
| --- | --- |
| `#write` | 正文容器（`<div id="write" class="typora-export">`） |
| `body.typora-export` | 页面根；深色主题会被加上 `md-dark` 类 |
| `pre.md-fences` | 代码块外壳（背景/边框/圆角放这里） |
| `pre.md-fences > div.CodeMirror.cm-s-inner` | 代码块内层（主题里的 `.cm-s-inner.CodeMirror { background: none }` 就是命中它） |
| `.cm-keyword` `.cm-string` `.cm-comment` `.cm-def` `.cm-number` … | 语法 token |
| `#write h1` / `table` / `blockquote` / `code` … | 普通元素 |

> 小坑：不要把 `cm-s-inner` / `CodeMirror` 直接放到 `<pre>` 上 —— 很多主题里有
> `.cm-s-inner.CodeMirror { background: none }`，特异性比 `.md-fences` 高，会把代码块底色抹掉。
> 项目里就是照 Typora 的真实结构分成两层来避免这个问题的。

## 配置

`~/.config/md-preview/config`：

```ini
theme      = github      # 默认主题（--list-themes 看全部）
dark_theme = night       # 浏览器预览时，系统切到深色模式则换成这个（留空 = 不换）
pdf_theme  =             # PDF 模式专用主题（留空 = 用 theme）。想让 Okular 里也是深色就填 night
```

命令行可以临时覆盖：`--theme` / `--dark-theme` / `--pdf-theme`。
`--html` 走浏览器（连续滚动、页内查找、深色跟随系统），默认走 PDF（交给 Okular，能批注/加书签）。

## Dolphin 中键集成（原理）

Dolphin 源码 `src/dolphinviewcontainer.cpp` → `DolphinViewContainer::slotfileMiddleClickActivated`：

```cpp
KService::List services = KApplicationTrader::queryByMimeType(item.mimetype());
int indexOfAppToOpenFileWith = 1;                                // 中键 = 列表第 2 个
if (modifiers & Qt::ShiftModifier) indexOfAppToOpenFileWith = 2;  // Shift+中键 = 第 3 个
```

顺序由 `kservice` 的 `KMimeAssociations` 决定：`~/.config/mimeapps.list` 的 `Default Applications`
（权重最高，列表内递减）> `Added Associations` > desktop 文件的 `InitialPreference`。所以只要排好
`mimeapps.list`，就能精确指定「双击谁、中键谁、Shift+中键谁」。本项目安装后是这个顺序：

```ini
[Default Applications]
text/markdown=org.kde.kate.desktop;

[Added Associations]
text/markdown=md-preview.desktop;md-preview-browser.desktop;okularApplication_md.desktop;
```

改完记得 `kbuildsycoca6 --noincremental` 刷新（安装脚本会自动做）。
细节与踩坑记录见 [`docs/kde-dolphin-middle-click.md`](docs/kde-dolphin-middle-click.md)。

## 工作原理

```
.md ──markdown-it-py──▶ HTML(+Pygments token 类名) ──┬─▶ 主题 CSS 注入 ─▶ 浏览器
                                                     └─▶ Chromium --headless --print-to-pdf ─▶ Okular
```

- HTML 里同时注入：桥接 CSS（低特异性兜底）→ 主题 `<link>`（原样引用主题文件，主题自带的字体/图片相对
  路径靠这个才解析得对）→ 打印 CSS（`@page` + 去栏宽 + `print-color-adjust: exact`）。
- 相对图片/链接用 `<base href="file://<md 所在目录>/">` 解析；标题自动加 `id`，文档内 `#锚点` 可跳转。
- 缓存目录 `~/.cache/md-preview/<路径哈希>/`，里面放生成的 HTML、PDF、缓存签名和浏览器 profile。

## 已验证

在 Ubuntu 26.04 / KDE Gear 25.12.3 / Edge + Firefox 上实测（`tools/probe-styles.py` 用 CDP 读真实计算样式）：

| 检查 | 方法 | 结果 |
| --- | --- | --- |
| 主题 CSS 真的命中 DOM | CDP 读 `getComputedStyle` | `github`：`#write` 860px、`pre` 底色 `#f8f8f8`；`drake-jb`：1200px、`pre` `#2b2b2b`；`night`：body `rgb(54,59,64)`、`pre` `#333` |
| token 配色来自主题而非兜底 | 同上 | 各主题 token 颜色互不相同（`github`/`newsprint` 未定义配色 → 走内置 Pygments 兜底） |
| 结构对齐 Typora | 查询 `pre.md-fences > .CodeMirror.cm-s-inner > code` | 全部主题为真 |
| 深色主题不会变成「白底浅字」 | 同上 | `drake-dark` body `rgb(43,43,43)`、`mdmdt-dark` body `rgb(27,27,31)` |
| PDF 保留底色 | `pdftoppm` + PIL 统计页面亮度 | `night` 110、`drake-dark` 97（深色底保留）；`newsprint` 240（米色纸保留）、`github` 247 |
| 打印不被主题栏宽限制 | 量墨迹横向占比 | 各主题均 85%（页边距 7–8%，与 `@page 16mm` 一致） |
| 中文可复制可搜索 | `pdftotext` | 抽取到正文中文 |
| 速度 | `time` | 19.9 KB / 12 页文档：HTML 0.22s，PDF 冷启 2.8s，缓存命中 0.000s |

## 已知限制

- **数学公式**：没有 KaTeX/MathJax 渲染，`$…$` 原样显示。
- **任务列表**：`- [x]` 不会渲染成勾选框（需要额外的 markdown-it 插件）。
- **批注**：Okular 的批注落在缓存 PDF 上；源文件改动后 PDF 会重生成，Okular 按路径保存的批注可能错位。
  需要长期批注的文档建议用 `--html` 阅读。
- **跨文件链接**：PDF 里点不动；HTML 里会打开浏览器而非继续预览。
- **需要 Chromium 系浏览器**当 PDF 引擎；没有就自动退回浏览器预览 HTML。
- 渲染在**沙箱之外**：markdown 里的原始 HTML 会进浏览器（本地自己的文档没问题，别拿它渲染不可信来源）。

## 目录结构

```
md-preview/
├── src/md_preview/
│   ├── cli.py              # 全部实现（自包含单文件，可直接拷到 ~/.local/bin）
│   └── fallback.css        # 无主题时的兜底样式
├── bin/md-preview          # 源码仓库直接运行的启动器
├── contrib/                # install.sh / uninstall.sh / merge-mimeapps.py / *.desktop.in
├── docs/kde-dolphin-middle-click.md
├── tools/                  # theme-gallery.py（主题截图拼版）、probe-styles.py（CDP 校验）
├── tests/                  # pytest：纯函数 / 渲染结构 / mimeapps 合并 / 端到端 PDF（27 项）
├── themes/README.md        # 主题来源、许可、自己写主题的要点
├── Makefile                # make help / test / install / gallery / probe
├── pyproject.toml          # pipx install . 安装，console script = md-preview
└── CHANGELOG.md · LICENSE · README.md
```

## 开发

```console
$ make help                                  # 常用任务一览（test / install / gallery / probe）
$ python3 -m pytest -q                       # 全部测试（端到端需要 Edge/Chrome）
$ python3 -m pytest -q -k "not end_to_end"   # 只跑不需要浏览器的部分
$ ./bin/md-preview --theme night tests/sample.md
$ python3 tools/theme-gallery.py             # 主题对比图
```

测试依赖 `pytest`：`pipx install pytest`，或在一个 venv 里 `pip install pytest`（项目依赖只有
`markdown-it-py` 和 `Pygments`，用 `python3 -m venv --system-site-packages` 可以直接复用系统的）。

## 为什么不是改 Okular 插件

Okular 的 Markdown 后端（`okularGenerator_md`，基于 discount）只暴露两个设置：**默认字体** 和
**Enable SmartyPants formatting** —— 源码 `generators/markdown/generator_md.cpp` 里 `addPages()` 就加了
一个复选框，配置骨架 `textdocumentsettings.cpp` 里只有 `addItemFont("Font", …)`；渲染时
`image.fill(Qt::white)`、`context.palette.setColor(QPalette::Text, Qt::black)` 是写死的，
页面尺寸 980×1307、页边距 45 也写死。上游关于 CSS 的需求单
[Bug 400529](https://bugs.kde.org/show_bug.cgi?id=400529)（CONFIRMED）与
[Bug 426682](https://bugs.kde.org/show_bug.cgi?id=426682)（UNCONFIRMED）都还开着，没人实现。

要真的在 Okular 里支持样式，只能自己写一个 generator 插件（第三方有先例：`okular-backend-mupdf`），
代价是依赖 `okular-dev`、每次 Okular 升级重编，而且仍然受 Qt 富文本 CSS 子集限制。
既然要「看一眼、读得舒服」，把渲染交给完整 CSS 引擎（Chromium）+ 主题生态更划算。

## 相关与致谢

- [Typora](https://typora.io/) 及其主题生态（主题即 CSS，这个项目直接复用）
- [markdown-it-py](https://github.com/executablebooks/markdown-it-py)、[Pygments](https://pygments.org/)
- KDE Dolphin / Okular / kservice（`KApplicationTrader` 的选应用逻辑）

## English summary

`md-preview` renders Markdown into a **styled PDF or HTML** using **Typora themes** (plain CSS), designed for
KDE Dolphin's middle-click preview slot (which opens the *second* application registered for a MIME type —
`DolphinViewContainer::slotfileMiddleClickActivated`). It rewrites the HTML DOM to match Typora's
(`#write`, `pre.md-fences`, `div.CodeMirror.cm-s-inner`) and adds CodeMirror token classes next to the Pygments
ones, so unmodified Typora themes apply. PDF output goes through headless Chromium with print CSS fixed up
(column width removed, `print-color-adjust: exact`), then opens in Okular. MIT licensed; third-party themes are
fetched on demand, never redistributed.

## License

MIT —— 见 [LICENSE](LICENSE)；第三方主题与依赖的许可见 [THIRD-PARTY.md](THIRD-PARTY.md)。
