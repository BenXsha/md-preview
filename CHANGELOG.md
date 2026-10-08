# Changelog

遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，版本号用 [SemVer](https://semver.org/lang/zh-CN/)。

## [0.1.0] - 2025-10-08

首个可用版本。从「Dolphin 中键预览 Markdown 渲染太丑」这个问题出发，做成一个可独立发布的小工具。

### Added

- `md-preview` CLI：
  - 默认把 Markdown 渲染成**带主题样式的 PDF** 并用 Okular 打开；`--html` 走浏览器。
  - `--theme` / `--dark-theme` / `--pdf-theme`，配置文件 `~/.config/md-preview/config`。
  - `--list-themes` / `--theme-dir` / `--install-theme <URL|文件>` / `--fetch-themes [主题集]` / `--version`。
- Typora 主题支持（主题是纯 CSS，直接用）：
  - HTML 结构对齐 Typora DOM：`body.typora-export` → `div#write.typora-export` →
    `pre.md-fences` → `div.CodeMirror.cm-s-inner.cm-s-typora-default` → `code`。
  - Pygments token 同时挂 CodeMirror 类名（`cm-keyword` / `cm-string` / `cm-def` / `cm-comment` …），
    主题自有配色可命中；未定义时回退内置深浅两套 Pygments 配色。
  - 主题文件以 `<link>` 原样引用，主题自带的字体/图片相对路径可正常解析。
- 深浅色自动判定：解析主题给 `html|body|#write` 设的页面底色（跳过 `prefers-color-scheme: dark` 块、
  解析 `var(--x)`、忽略注释、取首次定义），自动切换兜底配色、代码块底色、页面底色（`md-dark` 类）。
- 打印修正：`@page A4` 页边距、打印时去掉主题栏宽/内边距、`print-color-adjust: exact` 保留底色、
  标题/代码块/表格避免跨页断开。
- 渲染缓存：签名 = 源文件 mtime + 脚本 + 主题文件 + 桥接版本，命中即秒开。
- 主题目录：`--fetch-themes` 支持 `typora`（官方默认 7 个，含字体资源）、`drake`（11 个 + JetBrains Mono）、
  `mdmdt`（浅/深 2 个）；另有 `drake/`、`github/` 等资源子目录结构。
- `contrib/install.sh` / `uninstall.sh`：用户级安装，并把 `~/.config/mimeapps.list` 排成
  「双击 = 编辑器 → 中键 = md-preview → Shift+中键 = 浏览器预览 → 其后 = 原 Okular」，原文件自动备份。
- 开发工具：`tools/theme-gallery.py`（全主题截图 + 拼版挑主题）、`tools/probe-styles.py`
  （CDP 读计算样式，验证主题真的命中 DOM）。
- 文档：README、`docs/kde-dolphin-middle-click.md`（Dolphin 中键选应用机制与踩坑）、`themes/README.md`（主题与许可）。
- 测试：`tests/`（颜色解析、深浅判定、token 映射、标题锚点、渲染输出、可选端到端 PDF）。

### Notes

- 2025 年的 KDE Gear 25.12.3 + Okular 25.12.3 上，Okular 的 Markdown 后端仍然只支持「默认字体 + SmartyPants」，
  上游 CSS 需求单 [400529](https://bugs.kde.org/show_bug.cgi?id=400529)（CONFIRMED）、
  [426682](https://bugs.kde.org/show_bug.cgi?id=426682)（UNCONFIRMED）都未实现，因此本项目选择
  「不写 Okular 插件、改用完整 CSS 引擎（Chromium）+ 主题生态」的路线。
