# 其它渠道的短稿（r/kde、HN、Linux.do / V2EX / 小众软件）

原则：先讲「Dolphin 中键其实是第二个 MIME 应用」这个冷知识，再说工具；动图放第一屏；不写功能清单。

---

## r/kde（英文）

**标题**：`Dolphin's middle-click opens the 2nd app for the MIME type — so I put a themed Markdown→PDF renderer there`

**正文**

> Two Okular wishes (#400529, #426682) have been asking for custom CSS in the Markdown backend since 2018/2020,
> and the backend still paints the page itself, so long `.md` documents stay black-on-white.
>
> While looking at that, I learned something I did not know after years of Plasma: middle-click in Dolphin opens
> **the second application registered for the MIME type** (Shift+middle-click = the third), and the order comes
> from `~/.config/mimeapps.list`. Three lines give you three slots:
>
> ```ini
> [Default Applications]
> text/markdown=org.kde.kate.desktop;      # double-click = editor
> [Added Associations]
> text/markdown=md-preview.desktop;md-preview-browser.desktop;okularApplication_md.desktop;
> ```
>
> I put a small per-user CLI in slot 1: it renders the `.md` with a full CSS engine (plain-CSS themes, light/dark,
> syntax colours, KaTeX, Mermaid) into a PDF and opens it in Okular — reading and annotating still happen in
> Okular, nothing is patched, no root, `uninstall.sh` restores everything. Mechanism write-up + code:
> <https://github.com/BenXsha/md-preview> · screenshots/GIF in the README.
>
> Honest limits: it is a workaround (a real fix belongs upstream in the Markdown backend), PDF output wants a
> Chromium-based browser present, and it is Linux/KDE-only by design.

**发布提示**：先回复 2–3 条评论再贴链接（r/kde 对「新账号 + 链接」的容忍度低）；被问到「为什么不直接修 Okular」
就贴 `docs/kde-dolphin-middle-click.md` 里关于 ABI 与 QTextDocument CSS 子集的那段。

---

## Show HN

**标题**：`Show HN: Middle-click preview for Markdown in KDE Dolphin (the slot nobody documents)`

**第一段**（必须直接给「这是什么」）

> Dolphin's middle-click opens the second application registered for a file's MIME type. Markdown preview in
> KDE is stuck on a backend that lets you choose a font and nothing else, so I wrote a small per-user tool that
> takes slot 1 for `text/markdown`: it renders the document with a CSS engine and opens the PDF in Okular.

**然后**：三行 `mimeapps.list` 示例 → 一句「这不是修复」→ 仓库链接 → 一行已知限制。

**HN 注意**：不要用营销词（beautiful / blazing / seamless）；准备好回答「和 pandoc/glow/mdcat/Marktext 有何不同」
（答：不同在于**触发点**——文件管理器里对文件按中键，不换默认应用）；标题不要带 emoji。

---

## Linux.do / V2EX / 小众软件（中文）

**标题候选**（V2EX「分享创造」/ Linux.do「开源」）：

- `Dolphin 的鼠标中键到底打开了谁？顺手做了个 .md 预览`
- `把 KDE 里按中键看 Markdown 这件事修好了（不 patch Okular）`

**正文**

> 起因：KDE 里 Okular 的 Markdown 后端只能改字体，纸面底色和文字颜色是写死的，长文就是一片黑字白底，
> 官方两个 wish（400529 / 426682）从 2018/2020 开到今天。
>
> 查源码发现一件很多人（包括我）不知道的事：**Dolphin 的鼠标中键 = 该 MIME 类型应用列表里的第 2 个应用**，
> Shift+中键 = 第 3 个，顺序由 `~/.config/mimeapps.list` 决定。所以根本不用写 Okular 插件，把想要的渲染器
> 排到第 2 位就行：
>
> ```ini
> [Default Applications]
> text/markdown=org.kde.kate.desktop;      # 双击 = 编辑器
> [Added Associations]
> text/markdown=md-preview.desktop;md-preview-browser.desktop;okularApplication_md.desktop;
> ```
>
> 我在第 1 位放了个小工具：把 .md 用完整 CSS 引擎渲染成带主题的 PDF 再交给 Okular（浅深色、代码高亮、
> 公式、Mermaid 都跟着主题走），不 patch 任何系统组件、不用 sudo、`uninstall.sh` 一键还原。
> 机制说明（含 Dolphin 源码与 mimeapps 排序规则）：<repo>/docs/kde-dolphin-middle-click.md
>
> 说明：这是绕法不是修复，真正的修复在 Okular 侧；PDF 需要系统里有 Chromium 系浏览器（没有就退回浏览器预览）。
> 顺带一提，那三行配置对**任何** MIME 类型都成立 —— 想给图片、PDF 配第二个应用也是同样写法。

**发布提示**：中文社区发帖时贴图比贴链接重要（截图/GIF）；被问「和 Typora/Obsidian 有啥区别」用上面的
「换的是文件管理器里那一下」来答。
