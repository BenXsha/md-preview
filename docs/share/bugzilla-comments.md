# Bugzilla 评论草稿（okular#400529 / #426682）

**发帖前注意**

- KDE Bugzilla（Bugzilla 5.x）支持 Markdown，`{code}` 亦可；如果预览里代码块没生效，把围栏换成 `{code}`。
- 只发**一条**、信息为主：现状 + 绕法 + 真正修复需要什么。不要写「请加上这个功能」——wish 已经开着了。
- 两条不要同一天发；第二条交叉引用第一条（`See also bug 400529`）。
- 明确声明：绕法是第三方项目、与 KDE 无隶属关系；顺带说明它不是修复。
- 先在两个 bug 里搜一下有没有人已经贴过类似内容，避免重复。

---

## 给 #400529（Ship multiple CSS files for markdown backend，CONFIRMED，2018 起）

> Adding a data point for anyone landing here: the Markdown backend still paints the paper itself and takes the
> ink colour from the palette, so there is no in-app way to get a dark or otherwise styled page.
>
> A workaround that requires no Okular change, for people who only need to *look* at a document: Dolphin's
> middle-click opens **the second application registered for the MIME type**
> (`DolphinViewContainer::slotfileMiddleClickActivated`, `indexOfAppToOpenFileWith = 1`), so it is possible to put
> a renderer of your choice in that slot and keep the editor on double-click and Okular one slot further back:
>
> ```ini
> # ~/.config/mimeapps.list
> [Added Associations]
> text/markdown=md-preview.desktop;md-preview-browser.desktop;okularApplication_md.desktop;
> ```
>
> I wrote up the mechanism with the Dolphin source, the KDE sycoca scoring rules and the `mimeapps.list` ordering
> (useful for any MIME type, not just Markdown):
> https://github.com/BenXsha/md-preview/blob/main/docs/kde-dolphin-middle-click.md
>
> The renderer I put in that slot is a small per-user CLI from the same repo (MIT, no patches, no root) that
> renders the `.md` to a themed PDF with a full CSS engine and hands it to Okular — reading, zooming and
> annotating still happen in Okular. It only covers the middle-click gesture and it is a third-party project,
> not affiliated with KDE: a workaround, not a fix for this report.

---

## 给 #426682（CSS support in the Markdown backend，UNCONFIRMED，2020 起）

> Same gap as bug 400529 (See also there for a longer write-up): the Markdown backend colours the page and the
> text itself, so a user stylesheet has nothing to override.
>
> For the record, what a real fix looks like from the outside: (1) stop hard-coding the paper/ink colours and let
> a user stylesheet participate, and (2) accept that `QTextDocument` only understands a CSS subset — so it would
> help to document which properties are honoured, rather than promising "CSS support" generally.
>
> Until then, the middle-click workaround in bug 400529 is what I use day to day (slot 1 of `text/markdown` in
> `~/.config/mimeapps.list` → a themed renderer, Okular stays in the list). Mechanism notes:
> https://github.com/BenXsha/md-preview/blob/main/docs/kde-dolphin-middle-click.md

---

## 记录

| bug | 评论日期 | 结果 / 后续 |
|---|---|---|
| 400529 | — | |
| 426682 | — | |
