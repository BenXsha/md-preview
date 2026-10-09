# discuss.kde.org 帖子草稿

**版块**：Tips & Tricks（或 Brainstorm）。**标题**候选：

1. `What Dolphin's middle-click actually does — and a workaround for Okular's unstyled Markdown rendering`
2. `The second MIME slot: turning Dolphin's middle-click into a themed Markdown preview`

推荐 1：先给机制，工具作为附带。

**发帖前**：贴一张/一段动图（`python3 tools/middle-click-demo.py` 生成的是「预览滚动」那部分；
「中键那一下」用 Spectacle/kooha 录屏更可信）。不要把工具链接放在第一行。

---

## 正文

Middle-clicking a file in Dolphin is one of those behaviours that everybody uses and nobody can explain, so
I dug into the source a while ago and wrote it up. Short version: **middle-click opens the second application
registered for that MIME type**, and Shift+middle-click opens the third.

The order comes from `KApplicationTrader::queryByMimeType()`, i.e. from the service list sycoca builds out of
`~/.config/mimeapps.list` plus each desktop file's `InitialPreference` — `[Default Applications]` entries score
higher than `[Added Associations]` entries, and within one list the first line wins. So three lines in
`mimeapps.list` pin down three slots:

```ini
[Default Applications]
text/markdown=org.kde.kate.desktop;      # slot 0 — double-click / Enter

[Added Associations]
text/markdown=md-preview.desktop;md-preview-browser.desktop;okularApplication_md.desktop;
#             slot 1 (middle)     slot 2 (Shift+middle)      slot 3 — the original viewer
```

The relevant bit of Dolphin (`src/dolphinviewcontainer.cpp`):

```cpp
int indexOfAppToOpenFileWith = 1;                                   // middle click → 2nd
if (modifiers & Qt::ShiftModifier) {
    indexOfAppToOpenFileWith = 2;                                   // Shift+middle → 3rd
}
// …and if the list is too short, nothing happens at all
```

Full write-up, including what happens for executable text files and how to inspect your current order
(`ktraderclient6 --mimetype text/markdown`, `xdg-mime query default`):
<https://github.com/BenXsha/md-preview/blob/main/docs/kde-dolphin-middle-click.md>

**Why it matters to me:** Markdown is the one format where reading in Okular is genuinely painful — the
Markdown backend lets you pick a font and nothing else, and the page colour is painted by the backend itself,
so a long document is a wall of black on white with no dark mode (that is bug 400529 / 426682 upstream).
Rather than patch Okular, I used the middle-click slot: a tiny per-user CLI renders the `.md` to a themed PDF
with a real CSS engine and hands it to Okular, so the middle click is the "pretty" path while double-click
stays the editor and Okular stays in the list for everything else.

- <https://github.com/BenXsha/md-preview> (MIT, per-user, no root, no patches; uninstaller included)

It is a workaround, not a fix — a proper fix belongs in Okular's Markdown backend (custom/user CSS, and not
hard-coding the paper and ink colours). I am posting it here mainly because the slot mechanism is useful on its
own: the same three lines give you a second or third application for *any* MIME type (a different image viewer,
a hex dump, a PDF cropper …).

If you maintain one of the affected bits — the Markdown backend, or the middle-click slot semantics — I would
love to know whether the `mimeapps.list` ordering is the behaviour you intend to keep; if it is, it may be
worth a paragraph in the KDE user docs.
