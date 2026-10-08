# 第三方许可 / Third-party licenses

本项目（md-preview）自身代码以 [MIT](LICENSE) 发布。

**仓库里不包含任何第三方主题的 CSS。** 用户显式执行 `--fetch-themes` 时，程序直接从各自上游仓库下载到
用户自己的配置目录；仓库自带的两个主题是本项目原创的 MIT 资源。

The project code is MIT licensed. **No third-party theme CSS is bundled**: themes are downloaded on demand from
their upstream repositories into the user's own config directory. The two bundled themes are original MIT assets.

## 自带资源 / Bundled assets

| 文件 | 许可 |
| --- | --- |
| `src/md_preview/fallback.css`（主题 `default`） | MIT，本项目原创 |
| `src/md_preview/fallback-dark.css`（主题 `default-dark`） | MIT，本项目原创 |

## 可选主题集 / Optional fetchable theme sets

只有在用户显式执行 `md-preview --fetch-themes …` 时才会联网下载，且只收录许可明确的来源。

| 主题集 | 上游 / Upstream | 许可 / License |
| --- | --- | --- |
| `drake` | <https://github.com/liangjingkanji/DrakeTyporaTheme> | MIT, Copyright (c) 2023 劉強東（随附 JetBrains Mono 字体，SIL OFL 1.1） |
| `mdmdt` | <https://github.com/cayxc/Mdmdt> | Apache-2.0 |

上游仓库名中的编辑器字样只是项目标识，用于准确署名与定位源码；本项目与任何编辑器厂商无隶属或背书关系。

其它来源的主题：使用者自行获取并确认许可，用 `md-preview --install-theme` 安装，
许可由安装者负责。自查方法见 [docs/theme-licensing.md](docs/theme-licensing.md)。

## 运行时依赖 / Runtime dependencies

| 依赖 | 许可 |
| --- | --- |
| [markdown-it-py](https://github.com/executablebooks/markdown-it-py) | MIT |
| [linkify-it-py](https://github.com/tsutsu3/linkify-it-py)（`markdown-it-py[linkify]` 会带上；缺失时自动关闭自动链接功能） | MIT |
| [Pygments](https://pygments.org/) | BSD-2-Clause |
| [KaTeX](https://katex.org/)（可选，`md-preview --fetch-assets katex`；Debian/Ubuntu 也有 `libjs-katex` + `fonts-katex`） | MIT, Copyright (c) 2013-2020 Khan Academy and other contributors |
| [Mermaid](https://mermaid.js.org/)（可选，`md-preview --fetch-assets mermaid`） | MIT, Copyright (c) 2014-2024 Knut Sveidqvist |
| Chromium 系浏览器（Edge / Chrome / Chromium / Brave，仅作为无头 PDF 引擎调用） | 各自许可 |
| Okular（可选，用于查看生成的 PDF） | GPL-2.0-or-later |
| Pillow（可选，仅 `tools/theme-gallery.py`） | HPND |
| websockets（可选，仅 `tools/probe-styles.py`） | BSD-3-Clause |

## 参考 / References

- KDE Dolphin 源码（`src/dolphinviewcontainer.cpp` → `slotfileMiddleClickActivated`）与 kservice 的
  `KMimeAssociations`：中键槽位的选择机制，见
  [docs/kde-dolphin-middle-click.md](docs/kde-dolphin-middle-click.md)。
- Okular 的 Markdown 后端（`okularGenerator_md`）与上游需求单
  [400529](https://bugs.kde.org/show_bug.cgi?id=400529)、
  [426682](https://bugs.kde.org/show_bug.cgi?id=426682)：说明本项目为什么不做 Okular 后端插件，
  只在文档里引用事实，不含任何上游代码。
