# Changelog

遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，版本号用 [SemVer](https://semver.org/lang/zh-CN/)。

## [0.3.0] - 2025-10-08

内容能力补齐：**数学公式**（KaTeX）与 **Mermaid 图表** 可以在 HTML 与 PDF 里正常渲染了；
代码高亮本来就有（Pygments），这次一并做了端到端验证。

### Added

- **公式**：`$…$` / `$$…$$` 由自定义 markdown-it 规则转成占位元素（避免 Markdown 先把 `$x_i$` 吃成斜体），
  再由浏览器里的 KaTeX 渲染；`$5`、`$100` 这类货币不会被误判；代码块里的 `$` 不受影响。
- **图表**：` ```mermaid ` 代码块变成 `.mermaid` 容器交给 mermaid 渲染；没有资源时降级为代码块显示。
  深浅主题会自动切 mermaid 的 `default` / `dark` 主题。
- **资源获取**：`md-preview --fetch-assets [katex|mermaid|all]`，把 KaTeX（含字体，取自 npm tarball）
  与 Mermaid 下载到 `~/.config/md-preview/assets/`；查找顺序为
  `assets_dir` 配置 → `~/.config/md-preview/assets/<kind>` → 系统目录（如 `/usr/share/javascript/katex`）。
  仓库依旧不打包这些文件（都是 MIT，署名见 THIRD-PARTY.md）。
- 新配置项：`math` / `mermaid`（auto|off）、`assets_dir`、`js_budget`；新开关 `--no-math`、`--no-mermaid`、
  `--assets-dir`。
- PDF 侧：需要 JS 的页面会传 `--virtual-time-budget`（默认 10s，`js_budget` 可调），确保快照前
  KaTeX/Mermaid 已经渲染完；缓存签名把资源目录与开关一起算进去。
- 测试：新增公式规则、mermaid 降级、资源解析、开关语义、`js_budget` 解析的单元测试，
  以及「公式 + 图表端到端 PDF（校验 KaTeX 字体已内嵌）」的集成测试。
- 单文件安装（只拷 `cli.py`）时 `contrib/install.sh` 会把自带主题也放一份到
  `~/.config/md-preview/themes/default.css` / `default-dark.css`（已存在则不覆盖，等于给你一份可改的副本）；
  `theme_path()` 在包里找不到自带主题时会继续到用户主题目录找，因此不会再出现
  「主题 'default' 不存在」的误导性提示。

### Verified

在本机（Edge + 系统 libjs-katex + 下载的 mermaid 11.17.2）实测：

| 检查 | 结果 |
| --- | --- |
| KaTeX 真的渲染 | CDP 读到 6 个 `.katex`（含 1 个 display 块），盒模型 104×22 / 709×44 |
| 公式进了 PDF | PDF 文本层含 `x2 + y2 = z2`，`pdffonts` 显示内嵌 `KaTeX_Main-Regular` / `KaTeX_Math-Italic` / `KaTeX_Size1-Regular` |
| Mermaid 真的渲染 | CDP 读到 2 个 `svg`（250×334 流程图 / 450×287 时序图），节点标签为 开始/判断/结束/重试、用户/服务/请求预览/返回 PDF |
| 图表进了 PDF | 文本层含全部节点标签；第 2 页位图采样到 9238 个节点底色像素 + 418 个描边像素 |
| 代码高亮 | 同一文档里 63 个着色 span，8 种颜色（关键字/字符串/注释/数字等） |
| 边界 | `$5`、`$100` 原样保留；代码块内的 `$x$` 不被当公式 |
| 速度 | 含公式与 2 张图的文档：HTML 生成 0.x s，PDF（2 页）2.1 s |

## [0.2.1] - 2025-10-08

发布后修掉 CI 暴露出来的问题；功能内容与 0.2.0 相同。

### Fixed

- 干净环境下渲染会因 `ModuleNotFoundError: Linkify enabled but not installed.` 崩溃（CI 三个 Python 版本全红的原因）：
  现在声明 `markdown-it-py[linkify]` 依赖，并在缺少可选的 `linkify-it-py` 时自动关闭裸 URL 自动链接，
  而不是报错；新增对应回归测试。
- CI/容器/以 root 运行时 Chromium 的沙箱起不来，无头浏览器直接 SIGABRT
  （`zygote_linux.cc: write: Broken pipe`），端到端 PDF 生成失败：现在这种环境自动补 `--no-sandbox`
  （普通桌面用户不动，沙箱保持开启），并加了单元测试。
- 无头浏览器未能生成 PDF 时，把它的 stderr 末行打到 stderr，便于定位；CI 失败时会把 pytest 日志
  推到 `ci-logs` 分支，方便在无法访问 Actions 页面/日志 API 的环境里排查。

## [0.2.0] - 2025-10-08

主题体系与文档的**中立化 + 许可合规**整理，并补上 KDE 侧的体验细节。

### Changed

- **术语中立化**：文档、注释、desktop 项与包元数据里不再引用任何具体编辑器品牌；统一表述为
  「纯 CSS 主题」+「DOM 约定（`#write` / `pre.md-fences` / `div.CodeMirror.cm-s-inner` / `.cm-*`）」。
  兼容性所需的既有类名字符串（`typora-export`、`cm-s-typora-default`）原样保留，并在
  `themes/README.md` 里说明其含义（协议里的字符串常量，无隶属关系）。
- **主题目录只收录许可明确的来源**：移除未声明许可的主题集；`--fetch-themes` 现在只包含 MIT 与
  Apache-2.0 两套社区主题（`drake`、`mdmdt`），安装脚本默认**不联网**（用自带主题即可）。
- 自带主题改为 `default`（浅色）与 `default-dark`（深色），均为本项目原创 MIT 资源；深色版在 PDF 里
  保留深色底。`~/.config/md-preview/style.css` 仍作为主题缺失时的兜底样式。
- 文档拆成中英两份：[README.md](README.md)（English）与 [README.zh-CN.md](README.zh-CN.md)，重点讲
  如何提升 KDE 下的 Markdown 预览体验；`docs/theme-licensing.md` 新增主题许可自查清单。

### Added

- Dolphin 右键「服务菜单」项：安装后可直接选 *Markdown 预览（PDF / 浏览器）*。
- GitHub Actions CI（3.10 / 3.12 / 3.13 跑 pytest）。
- `README` 徽章、`THIRD-PARTY.md` 重写、`CHANGELOG` 本条目。


## [0.1.0] - 2025-10-08

首个可用版本。出发点：Dolphin 中键预览 Markdown 时的渲染不好看，而阅读器的 Markdown 后端只允许改字体。

### Added

- `md-preview` CLI：
  - 默认把 Markdown 渲染成**带主题样式的 PDF** 并用 Okular 打开；`--html` 走浏览器。
  - `--theme` / `--dark-theme` / `--pdf-theme`，配置文件 `~/.config/md-preview/config`。
  - `--list-themes` / `--theme-dir` / `--install-theme <URL|文件>` / `--fetch-themes` / `--version`。
- 纯 CSS 主题支持：
  - HTML 结构遵循文档化的主题 DOM 约定（`body.typora-export` → `div#write` → `pre.md-fences` →
    `div.CodeMirror.cm-s-inner` → `code`），主题文件以 `<link>` 原样引用。
  - Pygments token 同时挂 CodeMirror 类名（`cm-keyword` / `cm-string` / `cm-def` / `cm-comment` …），
    主题自有配色可命中；未定义时回退内置深浅两套配色。
- 深浅色自动判定：解析主题给 `html|body|#write` 设的页面底色（跳过 `prefers-color-scheme: dark` 块、
  解析 `var(--x)` 间接引用、忽略注释、取首次定义；支持逗号选择器），自动切换兜底配色、代码块底色、
  页面底色（`md-dark` 类）。
- 打印修正：`@page A4` 页边距、打印时去掉主题栏宽/内边距、`print-color-adjust: exact` 保留底色、
  标题与代码块/表格避免跨页断开。
- 渲染缓存：签名 = 源文件 mtime + 脚本 + 主题文件 + 桥接版本，命中即秒开。
- `contrib/install.sh` / `uninstall.sh`：用户级安装，并把 `~/.config/mimeapps.list` 排成
  「双击 = 编辑器 → 中键 = md-preview → Shift+中键 = 浏览器预览 → 其后 = 原预览器」，原文件自动备份。
- 开发工具：`tools/theme-gallery.py`（主题截图对比）、`tools/probe-styles.py`（DevTools 协议读计算样式，
  验证主题真的命中 DOM）。
- 文档：双语文档、`docs/kde-dolphin-middle-click.md`（中键槽位机制与坑）、`themes/README.md`（主题契约）。
- 测试：`tests/`（颜色解析、深浅判定、token 映射、标题锚点、渲染结构、mimeapps 合并、可选端到端 PDF）。
