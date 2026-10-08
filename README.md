# md-preview

[![tests](https://github.com/BenXsha/md-preview/actions/workflows/test.yml/badge.svg)](https://github.com/BenXsha/md-preview/actions/workflows/test.yml)
[![license: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

**One middle-click in Dolphin, and a `.md` opens as a properly typeset document** — styled with a plain-CSS
theme, rendered to PDF for Okular (or to HTML for your browser), cached so the next click is instant.

> 中文文档：[README.zh-CN.md](README.zh-CN.md)

## Why

In KDE, middle-clicking a file in Dolphin opens **the second application registered for that MIME type**
(`DolphinViewContainer::slotfileMiddleClickActivated`). For `.md` that slot normally lands on Okular — whose
Markdown backend only lets you pick a **font** and toggle smart punctuation, with the paper/ink colours
hard-coded (`image.fill(Qt::white)`, `QPalette::Text` → black). Long documents are a wall of black text,
and there is no way to style them (upstream wishes [400529](https://bugs.kde.org/show_bug.cgi?id=400529),
[426682](https://bugs.kde.org/show_bug.cgi?id=426682) are still open).

`md-preview` does not patch Okular. It takes the middle-click slot instead and hands the rendering to a full
CSS engine, so your previews get real typography, real dark mode, and a theme of your choosing — while Okular
keeps doing what it is good at (reading, zooming, annotating).

## Features

- **KDE-first workflow** — fills the Dolphin middle-click slot; `Shift+middle-click` for a browser preview;
  an optional Dolphin *service menu* entry for right-click → preview. Installation is per-user, no sudo.
- **Instant on repeat** — output is cached per (source mtime + theme + script); re-opening an unchanged
  document is instant, only edits trigger a re-render.
- **Plain-CSS themes** — the generated HTML follows the common Markdown-theme DOM contract
  (`#write`, `pre.md-fences`, `div.CodeMirror.cm-s-inner`, `.cm-*` token classes), so themes written for that
  contract drop in unmodified. Two MIT themes are bundled (`default`, `default-dark`) — works offline.
- **Syntax colours follow the theme** — Pygments tokens carry CodeMirror class names too, so a theme's own
  token palette applies; if it defines none, built-in light/dark palettes are used.
- **Automatic light/dark handling** — the theme's page background (including `var(--bg-color)` indirection and
  comma-separated selectors, ignoring commented-out and dark `prefers-color-scheme` blocks) decides whether a
  dark fallback is needed; themes that delegate the page colour to a host app get one injected.
- **Print fixes for a web-first stylesheet** — A4 `@page` margins, theme column width removed for print, and
  `print-color-adjust: exact` so dark backgrounds and code blocks survive into the PDF.
- **Linux-friendly** — Python + `markdown-it-py` + `Pygments`; PDF via headless Chromium (Edge/Chrome/Chromium/
  Brave, auto-detected); falls back to a browser preview if no Chromium is available.

## Install

### From the repository (recommended — sets up the KDE integration)

```console
$ git clone https://github.com/BenXsha/md-preview.git && cd md-preview
$ ./contrib/install.sh --help      # see exactly which files it touches
$ ./contrib/install.sh             # install script + bundled themes + .desktop + slot order
```

It is fully per-user (`~/.local/bin`, `~/.config/md-preview`, `~/.cache/md-preview`, `~/.local/share/applications`,
`~/.local/share/kio/servicemenus`) and it backs up `~/.config/mimeapps.list` before reordering the Markdown
MIME slots. `./contrib/uninstall.sh` restores everything.

### With pipx

```console
$ pipx install .          # or: pip install --user .
$ md-preview --version
```

### Single file

`src/md_preview/cli.py` is self-contained (stdlib + `markdown-it-py` + `Pygments`):

```console
$ install -Dm755 src/md_preview/cli.py ~/.local/bin/md-preview
```

### Requirements

| Requirement | Why |
| --- | --- |
| Python ≥ 3.10 | runtime |
| `markdown-it-py`, `Pygments` | Markdown → HTML, syntax highlighting |
| a Chromium-based browser | PDF engine (`--headless=new --print-to-pdf`); Edge/Chrome/Chromium/Brave are auto-detected |
| Okular (or any PDF viewer) | reading the generated PDF; without one the browser is used |
| Pillow, websockets (optional) | only for `tools/theme-gallery.py` and `tools/probe-styles.py` |

## Using it in KDE

After `contrib/install.sh`, the Markdown MIME slots are ordered like this:

| Slot | Opened by | Application |
| --- | --- | --- |
| 0 | double-click / Enter | your editor (e.g. Kate) — unchanged |
| 1 | **middle-click** | **md-preview** → themed PDF → Okular |
| 2 | `Shift` + middle-click | md-preview `--html` → browser |
| 3+ | context menu → Open With | the previous previewer (Okular) is still there |

```console
$ md-preview notes.md                # themed PDF, opens in Okular (cached)
$ md-preview --html notes.md         # themed HTML, opens in your browser
$ md-preview --theme default-dark notes.md
$ md-preview --list-themes
```

Right-clicking a `.md` in Dolphin also offers **Markdown Preview (PDF / Browser)** from the service menu.

Why slot 1 and not the editor slot? Because that is exactly the gesture you already use for "just show me
this file", and it leaves double-click for editing. Details, ordering rules and gotchas:
[`docs/kde-dolphin-middle-click.md`](docs/kde-dolphin-middle-click.md).

## Themes

A theme is a single CSS file. Bundled (MIT, always available, no network):

| Theme | Look |
| --- | --- |
| `default` | light, 52 rem column, GitHub-ish code blocks, CJK-friendly font stack |
| `default-dark` | dark counterpart, same metrics; keeps its dark background in the PDF |

Optional, license-clear sources you can fetch explicitly (`md-preview --fetch-themes drake mdmdt`):
[MIT](https://github.com/liangjingkanji/DrakeTyporaTheme) and
[Apache-2.0](https://github.com/cayxc/Mdmdt) community CSS sets. Anything else you install yourself with
`md-preview --install-theme <file|url>` — **you are responsible for that theme's license**; see
[`docs/theme-licensing.md`](docs/theme-licensing.md) for a 30-second audit checklist.

```console
$ md-preview --list-themes
$ md-preview --theme-dir            # drop any .css in here, it becomes a theme
$ md-preview --install-theme ~/Downloads/my-theme.css
```

Comparing themes is easier with screenshots:

```console
$ python3 tools/theme-gallery.py     # one PNG per theme + a contact sheet
```

### Writing your own theme

The generated DOM (kept deliberately stable, it is the compatibility surface):

| Selector | Element |
| --- | --- |
| `#write` | content container (`<div id="write" class="typora-export">`) |
| `body.typora-export` | page root; dark themes additionally get `md-dark` |
| `pre.md-fences` | code block shell — put background/border/radius here |
| `pre.md-fences > div.CodeMirror.cm-s-inner` | code block inner layer |
| `.cm-keyword` `.cm-string` `.cm-comment` `.cm-def` `.cm-number` … | syntax tokens |
| plain elements | `#write h1`, `p`, `table`, `blockquote`, `code`, `hr`, `img` |

Two notes from hard-won experience:

- Do **not** put `cm-s-inner`/`CodeMirror` on the `<pre>` itself: themes that ship
  `.cm-s-inner.CodeMirror { background: none }` (specificity 0,2,0) would wipe the `.md-fences` background.
  That is why the code block is two nested elements.
- Some themes leave the page colour to the host application and only define `--bg-color`; md-preview injects
  `body { background-color: var(--bg-color, …) }` in that case and treats the theme as dark.

## Configuration

`~/.config/md-preview/config`:

```ini
theme      = default        # --list-themes for everything available
dark_theme = default-dark   # used for --html when the system prefers dark (leave empty to disable)
pdf_theme  =                # theme used for PDF only (empty = same as theme)
```

`--theme` / `--dark-theme` / `--pdf-theme` override it per invocation.
`--html` opens the browser (continuous scrolling, in-page search, adapts to the system dark mode); the default
path produces a PDF for Okular (annotations, bookmarks, single-page/continuous modes).

## How it works

```
.md ──markdown-it-py──▶ HTML (+ Pygments & CodeMirror token classes) ──┬─▶ + theme CSS ─▶ browser
                                                                       └─▶ headless Chromium --print-to-pdf ─▶ Okular
```

- The HTML links the theme file as-is (`<link>`), so a theme's own relative fonts/images resolve correctly;
  project CSS is injected around it: a low-specificity bridge first, print rules last.
- Relative images/links resolve via `<base href="file://<dir of the .md>/">`; headings get `id`s so in-document
  `#anchors` work.
- Cache: `~/.cache/md-preview/<hash>/` holds the generated HTML, the PDF, a signature stamp and the headless
  browser profile.

## Verified

Measured on Ubuntu 26.04 / KDE Gear 25.12.3 (Edge + Firefox), using `tools/probe-styles.py` (real
`getComputedStyle` through the DevTools protocol) and `pdftoppm`/PIL on the PDF output:

| Check | Result |
| --- | --- |
| Theme CSS actually matches the DOM | bundled `default`: `#write` 52 rem, `pre.md-fences` light background; `default-dark`: `body` background `rgb(27,31,39)` |
| Token colours come from the theme, not the fallback | distinct per theme; themes without token palettes fall back to built-in Pygments light/dark |
| Code block structure | `pre.md-fences > .CodeMirror.cm-s-inner > code` present for every theme |
| Dark themes stay dark in the PDF | `print-color-adjust: exact` keeps the dark page (page luminance ≈ 100–115 vs ≈ 240 for light themes) |
| Print ignores web column widths | ink spans 85 % of the A4 page width, 7–8 % side margins (matches `@page 16mm`) |
| Chinese text stays selectable | extracted with `pdftotext` |
| Speed | 20 KB / 12-page document: HTML 0.22 s, PDF cold 2.8 s, cached 0.000 s |

## Known limitations

- No math rendering (KaTeX/MathJax); `$…$` is shown literally.
- Task lists (`- [x]`) are not turned into checkboxes (needs an extra markdown-it plugin).
- Okular annotations attach to the cached PDF; when the source changes the PDF is regenerated and
  Okular's per-path annotation file may drift. Use `--html` for documents you annotate long-term.
- Links between `.md` files do not work in the PDF, and open in the browser rather than continuing the preview.
- Raw HTML in the Markdown reaches the browser/PDF engine — fine for your own documents, not for untrusted input.

## Repository layout

```
src/md_preview/cli.py     the whole implementation (self-contained single file)
src/md_preview/*.css      bundled MIT themes (default / default-dark)
bin/md-preview            launcher for running straight from a clone
contrib/                  install.sh, uninstall.sh, merge-mimeapps.py, MIME slot ordering, .desktop & service menu templates
docs/                     Dolphin middle-click internals, theme licensing
themes/README.md          theme contract and sources
tools/                    theme screenshot sheet, DevTools-protocol style probe
tests/                    pytest suite (unit + DOM structure + MIME merge + optional end-to-end PDF)
.github/workflows/        CI
```

## Development

```console
$ make help                                  # test / install / gallery / probe
$ python3 -m pytest -q                       # full suite (the e2e PDF test needs a Chromium browser)
$ python3 -m pytest -q -k "not end_to_end"
$ ./bin/md-preview --theme default-dark tests/sample.md
```

Tests need `pytest` (`pipx install pytest`, or a venv — `python3 -m venv --system-site-packages` can reuse the
system's `markdown-it-py`/`Pygments`).

## Why not an Okular generator plugin

An in-tree backend would be the "native" answer, but: Okular's Markdown backend exposes exactly one checkbox
and one font setting, its rendering is hard-coded to white paper/black text, and a third-party generator links
against `libOkular6Core` with no ABI promise — it has to be rebuilt for every Okular release, and it is still
limited to the Qt rich-text CSS subset. Handing rendering to a full CSS engine keeps the styling options broad
and the maintenance cost near zero. (For reference, third-party generators do exist, e.g.
[okular-backend-mupdf](https://github.com/lanconnected/okular-backend-mupdf).)

## Credits

- KDE Dolphin / Okular / kservice — the middle-click slot logic lives in `KApplicationTrader` + `KMimeAssociations`.
- [markdown-it-py](https://github.com/executablebooks/markdown-it-py) and [Pygments](https://pygments.org/).
- Theme authors whose work can be fetched on demand — see [THIRD-PARTY.md](THIRD-PARTY.md).

## License

MIT — see [LICENSE](LICENSE). Third-party themes and dependencies:
[THIRD-PARTY.md](THIRD-PARTY.md) · theme license audit guide: [docs/theme-licensing.md](docs/theme-licensing.md).
