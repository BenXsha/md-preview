# 第三方许可与致谢 / Third-party licenses

本项目自身代码是 [MIT](LICENSE)。**仓库里不包含任何第三方主题的 CSS**，主题由
`md-preview --fetch-themes` 在用户机器上按需下载，版权归各自作者所有。

The project code is MIT licensed. **No third-party theme CSS is bundled in this repository** —
themes are downloaded on demand into the user's own config directory by `md-preview --fetch-themes`.

## 可一键拉取的主题 / Fetchable themes

| 主题集 | 上游 / Upstream | 许可 / License |
| --- | --- | --- |
| `typora`（`github` `gothic` `newsprint` `night` `pixyll` `whitey` `whitey-deep`） | <https://github.com/typora/typora-default-themes> | 上游仓库未声明开源许可（这些是 Typora 自带的默认主题），仅供本地个人使用 / No license declared upstream; personal local use only |
| `drake`（11 个配色） | <https://github.com/liangjingkanji/DrakeTyporaTheme> | MIT, Copyright (c) 2023 劉強東 |
| `mdmdt`（`mdmdt-light` `mdmdt-dark`） | <https://github.com/cayxc/Mdmdt> | Apache-2.0 |

其他主题可从 [Typora 主题画廊](https://theme.typora.io/) 或 GitHub 自取，用
`md-preview --install-theme <URL 或 .css>` 安装；其许可由各自作者决定，本项目不做任何再分发。

## 运行时依赖 / Runtime dependencies

| 依赖 | 许可 |
| --- | --- |
| [markdown-it-py](https://github.com/executablebooks/markdown-it-py) | MIT |
| [Pygments](https://pygments.org/) | BSD-2-Clause |
| Chromium 系浏览器（Edge / Chrome / Chromium / Brave，仅作为 headless PDF 引擎调用） | 各自的许可 |
| Okular（可选，用于查看生成的 PDF） | GPL-2.0-or-later |
| Pillow（可选，只有 `tools/theme-gallery.py` 用） | HPND |
| websockets（可选，只有 `tools/probe-styles.py` 用） | BSD-3-Clause |

## 参考 / References

- KDE Dolphin 源码（`src/dolphinviewcontainer.cpp` → `slotfileMiddleClickActivated`）与
  kservice 的 `KMimeAssociations`：中键选应用的机制，见
  [docs/kde-dolphin-middle-click.md](docs/kde-dolphin-middle-click.md)。
- Okular 的 Markdown 后端（`okularGenerator_md`）与上游需求单
  [400529](https://bugs.kde.org/show_bug.cgi?id=400529)、
  [426682](https://bugs.kde.org/show_bug.cgi?id=426682)：为什么本项目不改 Okular 插件。
