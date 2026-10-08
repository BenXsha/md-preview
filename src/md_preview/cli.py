#!/usr/bin/env python3
"""md-preview —— 把 Markdown 渲染成带样式的 PDF / HTML，专为「中键看一眼」设计。

最适合的场景是 KDE(Dolphin) 的鼠标中键预览：中键点一个 .md，直接得到排版漂亮的预览
（默认渲染成 PDF 交给 Okular，或 --html 用浏览器打开）。

样式来自**纯 CSS 主题**：项目生成的 HTML 遵循通用的 Markdown 主题 DOM 约定
（`#write` / `pre.md-fences` / `div.CodeMirror.cm-s-inner` / `.cm-*` token 类），
任何按这套约定书写的 CSS 都能直接用。自带两个 MIT 许可的主题（`default` / `default-dark`），
开箱即用、不需要联网；需要更多风格时可安装自己信任的主题文件。

内容能力：代码高亮（Pygments）、数学公式（KaTeX）、Mermaid 图表。后两者需要前端资源，
仓库不打包、也不会自动联网：用 `md-preview --fetch-assets` 下载到用户目录即可，
系统若已装 KaTeX（如 Debian/Ubuntu 的 libjs-katex）会自动使用。

用法:
  md-preview FILE.md                渲染成带主题样式的 PDF，用 Okular 打开（默认，带缓存）
  md-preview --html FILE.md         渲染成 HTML，用默认浏览器打开
  md-preview --theme default-dark FILE.md
  md-preview --list-themes          列出可用主题（自带 + 已安装）
  md-preview --fetch-themes         可选：拉取带明确开源许可的社区主题集（见 THIRD-PARTY.md）
  md-preview --fetch-assets         可选：下载公式/图表用的 KaTeX、Mermaid（都是 MIT）
  md-preview --no-math --no-mermaid 关闭公式 / 图表渲染
  md-preview --front-matter card     YAML 头部的显示方式：card / raw / off
  md-preview --install-theme <URL 或 .css 路径>
  md-preview --theme-dir            打印主题目录（把任意 .css 丢进去即可生效）
  md-preview --version

配置: ~/.config/md-preview/config
    theme      = default       # 默认主题（default / default-dark 为自带主题）
    dark_theme = default-dark  # 浏览器预览时系统为深色模式则换成这个（可留空）
    pdf_theme  =               # PDF 模式专用主题（留空 = 用 theme）
    math       = auto          # auto / off：公式渲染开关
    mermaid    = auto          # auto / off：图表渲染开关
    assets_dir =               # 自定义 KaTeX/Mermaid 所在目录（留空 = 用默认查找顺序）
    js_budget  = 10000         # 无头浏览器给 JS 渲染留的虚拟时间预算（毫秒）
    front_matter = card        # YAML 头部：card（信息卡）/ raw（原文）/ off（不显示）

主题目录: ~/.config/md-preview/themes/   资源目录: ~/.config/md-preview/assets/
缓存目录: ~/.cache/md-preview/<hash>/
许可说明: 主题与前端资源由使用者添加；本项目只收录许可明确的来源，详见 THIRD-PARTY.md
"""

from __future__ import annotations

import html as html_mod
import hashlib
import json
import io
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tarfile
import unicodedata
import urllib.request

HOME = pathlib.Path.home()
CONF = pathlib.Path(os.environ.get("XDG_CONFIG_HOME", HOME / ".config")) / "md-preview"
CACHE = pathlib.Path(os.environ.get("XDG_CACHE_HOME", HOME / ".cache")) / "md-preview"
THEMES = CONF / "themes"
CONFIG_FILE = CONF / "config"
PKG_DIR = pathlib.Path(__file__).resolve().parent
PACKAGE_FALLBACK = PKG_DIR / "fallback.css"  # 自带浅色主题（MIT，随项目分发）
PACKAGE_FALLBACK_DARK = PKG_DIR / "fallback-dark.css"  # 自带深色主题（MIT）
# 自带主题：不依赖任何第三方，装完即可用
BUNDLED_THEMES: dict[str, pathlib.Path] = {
    "default": PACKAGE_FALLBACK,
    "default-dark": PACKAGE_FALLBACK_DARK,
}
__version__ = "0.4.0"

CHROMIUM_CANDIDATES = [
    "/usr/bin/microsoft-edge-stable",
    "/usr/bin/microsoft-edge",
    "/usr/bin/google-chrome-stable",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
    "/usr/bin/brave-browser",
]
VIEWER_PDF = "okular"

# 主题缺失时的兜底主题（自带样式，见 style.css）
FALLBACK_THEME = CONFIG_FILE.parent / "style.css"

BRIDGE_VERSION = 3  # 桥接层变了就作废缓存

# ---------------------------------------------------------------- 桥接 CSS（主题之前）
# 只放「主题不管的」和「主题缺失时的兜底」。选择器刻意保持低特异性，方便主题覆盖。
BASE_CSS = """\
*, *::before, *::after { box-sizing: border-box; }
body { margin: 0; }
#write {
  max-width: 52rem;
  margin: 0 auto;
  padding: 2rem 1.5rem 3rem;
  font-family: "Noto Sans CJK SC", "Source Han Sans SC", "Microsoft YaHei",
               "PingFang SC", "Segoe UI", system-ui, sans-serif;
  line-height: 1.75;
}
#write img, #write video, #write svg { max-width: 100%; height: auto; }
#write table { border-collapse: collapse; margin: 1em 0; }
#write hr { border: none; border-top: 1px solid currentColor; opacity: .25; margin: 1.6em 0; }

/* 代码块：有些主题把 padding/font 放在 .CodeMirror-lines 上，我们没有那层元素，这里补上 */
:root { --mp-fence-bg: #f6f8fa; --mp-inline-bg: #f6f8fa; --mp-frontmatter-bg: #f8f9fb; }
body.md-dark { --mp-fence-bg: #22272e; --mp-inline-bg: #2d333b; --mp-frontmatter-bg: #20252e; }

.md-fences {
  padding: .9em 1em;
  overflow-x: auto;
  border-radius: 6px;
  line-height: 1.55;
  background-color: var(--mp-fence-bg);
}
.md-fences code {
  background: none;
  border: 0;
  padding: 0;
  font-size: 1em;
  font-family: "JetBrains Mono", "Cascadia Code", "DejaVu Sans Mono",
               "Noto Sans Mono CJK SC", monospace;
}
/* 行内代码兜底（主题自带 code 规则会覆盖它） */
code {
  background-color: var(--mp-inline-bg);
  padding: .1em .3em;
  border-radius: 4px;
  font-family: "JetBrains Mono", "Cascadia Code", "DejaVu Sans Mono",
               "Noto Sans Mono CJK SC", monospace;
}

/* ---- 数学公式与图表（资源缺失时降级为代码块显示） ---- */
.math-inline { white-space: nowrap; }
.math-block { margin: 1em 0; text-align: center; overflow-x: auto; overflow-y: hidden; break-inside: avoid; page-break-inside: avoid; }
.math-block .katex-display { margin: .4em 0; }
.katex { font-size: 1.06em; }
pre.mermaid-source { white-space: pre-wrap; font-size: .9em; }
.mermaid { margin: 1em 0; text-align: center; break-inside: avoid; page-break-inside: avoid; }
.mermaid svg { max-width: 100%; height: auto; }

/* ---- YAML 头部（front matter）信息卡 ---- */
.front-matter {
  margin: 0 0 1.6em;
  padding: .85em 1.1em;
  border: 1px solid rgba(127, 127, 127, .35);
  border: 1px solid color-mix(in srgb, currentColor 20%, transparent);
  border-left-width: 3px;
  border-left-color: color-mix(in srgb, currentColor 45%, transparent);
  border-radius: 8px;
  background-color: var(--mp-frontmatter-bg);
  font-size: .95em;
  line-height: 1.6;
  break-inside: avoid;
  page-break-inside: avoid;
}
.front-matter .fm-title { display: flex; flex-wrap: wrap; align-items: baseline; gap: .5em; margin-bottom: .35em; }
.front-matter .fm-name { font-size: 1.22em; font-weight: 600; font-family: "JetBrains Mono", "Cascadia Code", "Noto Sans Mono CJK SC", monospace; }
.front-matter .fm-chip {
  font-size: .78em;
  padding: .05em .55em;
  border: 1px solid color-mix(in srgb, currentColor 25%, transparent);
  border-radius: 999px;
  opacity: .8;
  font-family: "JetBrains Mono", "Cascadia Code", "Noto Sans Mono CJK SC", monospace;
}
.front-matter dl { margin: 0; }
.front-matter dt {
  margin-top: .55em;
  font-size: .78em;
  letter-spacing: .05em;
  text-transform: uppercase;
  opacity: .6;
}
.front-matter dd { margin: .1em 0 0; }
.front-matter .fm-chips { display: flex; flex-wrap: wrap; gap: .35em; margin: .1em 0 0; padding: 0; list-style: none; }
.front-matter .fm-chips li {
  font-size: .85em;
  padding: .05em .5em;
  border-radius: 4px;
  background-color: var(--mp-inline-bg);
  font-family: "JetBrains Mono", "Cascadia Code", "Noto Sans Mono CJK SC", monospace;
}
.front-matter .fm-raw { margin: 0; background: none; border: 0; padding: 0; }
.front-matter .fm-hint { margin: .4em 0 0; font-size: .8em; opacity: .7; }
"""

# ---------------------------------------------------------------- 打印 CSS（主题之后）
PRINT_CSS = """\
@page { size: A4; margin: 18mm 16mm 16mm 16mm; }
@media print {
  /* 让深色主题/代码块底色在 PDF 里保留（Chrome 默认不打印背景色） */
  html, * { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  /* 主题是按「网页连续滚动」设计的：打印时去掉宽度/内边距限制，交给 @page 控制 */
  #write {
    max-width: none !important;
    margin: 0 !important;
    padding: 0 !important;
  }
  h1, h2, h3, h4, h5, h6 { break-after: avoid-page; page-break-after: avoid; }
  pre, table, blockquote, figure, img { break-inside: avoid-page; page-break-inside: avoid; }
  a { text-decoration: none; }
}
"""

TEMPLATE = """<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<base href="{base}">
<title>{title}</title>
<style>
{bridge}
{page_bg}
/* pygments 兜底配色（主题自带 .cm-* 配色时会覆盖它） */
{pyg_light}
@media screen and (prefers-color-scheme: dark) {{
{pyg_dark}
}}
</style>
{theme_links}
{asset_links}
<style>
{print_css}
</style>
</head>
<body class="typora-export{body_class}">
<div id="write" class="typora-export">
{body}
</div>
</body>
</html>
"""

# Pygments token -> CodeMirror 类名（遵循这套 DOM 约定的主题按这些类名配色）
TOKEN_MAP = {
    "k": "cm-keyword", "kc": "cm-keyword", "kd": "cm-keyword", "kn": "cm-keyword",
    "kp": "cm-keyword", "kr": "cm-keyword", "kt": "cm-keyword",
    "n": "cm-variable", "na": "cm-attribute", "nb": "cm-builtin", "bp": "cm-builtin",
    "nc": "cm-variable-3", "no": "cm-atom", "nd": "cm-meta", "ni": "cm-property",
    "ne": "cm-atom", "nf": "cm-def", "fm": "cm-def", "nl": "cm-qualifier",
    "nn": "cm-variable-3", "nt": "cm-tag", "nv": "cm-variable-2",
    "vc": "cm-variable-2", "vg": "cm-variable-2", "vi": "cm-variable-2", "vm": "cm-variable-2",
    "o": "cm-operator", "ow": "cm-operator",
    "s": "cm-string", "s1": "cm-string", "s2": "cm-string", "sb": "cm-string",
    "sc": "cm-string", "sd": "cm-string", "se": "cm-string", "sh": "cm-string",
    "si": "cm-string", "sx": "cm-string", "sa": "cm-string", "dl": "cm-string",
    "sr": "cm-string-2", "ss": "cm-string-2",
    "m": "cm-number", "mb": "cm-number", "mf": "cm-number", "mh": "cm-number",
    "mi": "cm-number", "mo": "cm-number", "il": "cm-number",
    "c": "cm-comment", "c1": "cm-comment", "cm": "cm-comment", "cs": "cm-comment",
    "cp": "cm-comment", "cpf": "cm-comment", "ch": "cm-comment",
    "gd": "cm-negative", "gi": "cm-positive", "gh": "cm-header",
    "ge": "cm-em", "gs": "cm-strong", "err": "cm-error",
}

_SPAN_CLASS = re.compile(r'<span class="([^"]+)">')
_SLUG_BAD = re.compile(r"[^\w\u4e00-\u9fff\u3040-\u30ff-]+", re.UNICODE)
_HEADING = re.compile(r"<h([1-6])>(.*?)</h\1>", re.S)


# ---------------------------------------------------------------- 配置
def read_config() -> dict[str, str]:
    cfg: dict[str, str] = {}
    if CONFIG_FILE.exists():
        for line in CONFIG_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            cfg[key.strip()] = value.strip()
    return cfg


def theme_path(name: str) -> pathlib.Path | None:
    """把主题名解析成 css 路径：自带主题 → 用户主题目录 → 绝对路径 / 显式 .css。"""
    if not name:
        return None
    bundled = BUNDLED_THEMES.get(name)
    if bundled is not None and bundled.is_file():
        return bundled
    # 单文件安装（只拷了 cli.py）时包里没有自带主题，会继续在用户主题目录里找
    # （install.sh 会把 default / default-dark 也放一份到那里）
    p = pathlib.Path(name).expanduser()
    if p.is_absolute() or p.suffix == ".css":
        return p if p.is_file() else None
    for cand in (THEMES / f"{name}.css", THEMES / name):
        if cand.is_file():
            return cand
    return None


def list_themes() -> list[str]:
    """自带主题 + 用户主题目录里的 *.css（不含主题自带的资源子目录）。"""
    user = {p.stem for p in THEMES.glob("*.css")}
    return sorted(set(BUNDLED_THEMES) | user)


# ---------------------------------------------------------------- Markdown -> HTML
def _map_tokens(fragment: str) -> str:
    def repl(m: re.Match) -> str:
        toks = m.group(1).split()
        extra = [TOKEN_MAP[t] for t in toks if TOKEN_MAP.get(t)]
        merged = toks + [e for e in extra if e not in toks]
        return f'<span class="{" ".join(merged)}">' if merged else "<span>"

    return _SPAN_CLASS.sub(repl, fragment)


def _slug(text: str) -> str:
    text = unicodedata.normalize("NFKC", re.sub(r"<[^>]+>", "", text)).strip().lower()
    return _SLUG_BAD.sub("-", text).strip("-") or "section"


def _add_heading_ids(html: str) -> str:
    def repl(m: re.Match) -> str:
        level, inner = m.group(1), m.group(2)
        return f'<h{level} id="{_slug(inner)}">{inner}</h{level}>'

    return _HEADING.sub(repl, html)


# 页面级规则：选择器里出现 html / body / #write（支持 `html,\nbody { }` 这种逗号列表）。
# 用非贪婪匹配所有 { } 块（@ 被排除，所以 at-rule 前奏不会进来），再按选择器过滤。
_BG_BLOCK = re.compile(r"([^{}@]*?)\s*\{([^}]*)\}", re.S)
_PAGE_SELECTOR = re.compile(r"(?:^|,|\s)(?:html|body|#write)(?=\s*(?:[,{]|$))", re.M)
_BG_DECL = re.compile(r"background(?:-color)?\s*:\s*([^;}!]+)")
_VAR_DECL = re.compile(r"(--[\w-]+)\s*:\s*([^;]+)")
_DARK_MEDIA = re.compile(r"@media[^{]*prefers-color-scheme\s*:\s*dark[^{]*\{", re.I)


def _dark_media_spans(text: str) -> list[tuple[int, int]]:
    """找出 @media (prefers-color-scheme: dark) 块的范围，判断主题底色时要跳过它们。"""
    spans: list[tuple[int, int]] = []
    for m in _DARK_MEDIA.finditer(text):
        depth, i = 1, m.end()
        while i < len(text) and depth:
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
            i += 1
        spans.append((m.start(), i))
    return spans


def _color_luminance(color: str, variables: dict[str, str]) -> float | None:
    """把一个 CSS 颜色算成 0..1 的亮度；解析不了就返回 None。"""
    c = color.strip().lower()
    ref = re.match(r"var\(\s*(--[\w-]+)", c)
    if ref:
        value = variables.get(ref.group(1))
        return None if value is None else _color_luminance(value, variables)
    c = re.sub(r"\s*!\s*important\s*$", "", c).strip()  # 别用 split()：rgb(1, 2, 3) 里有空格
    m = re.match(r"#([0-9a-f]{3}|[0-9a-f]{6})\b", c)
    if m:
        h = m.group(1)
        if len(h) == 3:
            h = "".join(ch * 2 for ch in h)
        r, g, b = (int(h[i : i + 2], 16) for i in (0, 2, 4))
    else:
        m = re.match(r"rgba?\(\s*([\d.]+)[\s,]+([\d.]+)[\s,]+([\d.]+)", c)
        if m:
            r, g, b = (float(m.group(i)) for i in (1, 2, 3))
        elif c == "white":
            r = g = b = 255.0
        elif c == "black":
            r = g = b = 0.0
        else:
            return None
    return (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255


_COMMENT = re.compile(r"/\*.*?\*/", re.S)


def _strip_comments(text: str) -> str:
    return _COMMENT.sub("", text)


def _first_page_bg(css_path: pathlib.Path | None) -> str | None:
    """取主题给 html/body/#write 设的页面背景色原始值（没有则 None）。"""
    if css_path is None:
        return None
    try:
        text = _strip_comments(css_path.read_text(encoding="utf-8", errors="replace"))
    except OSError:
        return None
    dark_spans = _dark_media_spans(text)
    for m in _BG_BLOCK.finditer(text):
        if any(a <= m.start() < b for a, b in dark_spans):
            continue
        if not _PAGE_SELECTOR.search(m.group(1)):
            continue
        for value in _BG_DECL.findall(m.group(2)):
            value = value.strip()
            if value.lower() in ("transparent", "none", "inherit", "currentcolor", "unset"):
                continue
            return value
    return None


def theme_variables(css_path: pathlib.Path | None) -> dict[str, str]:
    if css_path is None:
        return {}
    try:
        text = _strip_comments(css_path.read_text(encoding="utf-8", errors="replace"))
    except OSError:
        return {}
    variables: dict[str, str] = {}
    for key, value in _VAR_DECL.findall(text):
        variables.setdefault(key, value.strip())  # 取第一次定义（后面的常常是暗色变体）
    return variables


def is_dark_theme(css_path: pathlib.Path | None) -> bool:
    """猜主题深浅：优先看主题自设的页面背景亮度，其次按主题名猜。"""
    if css_path is None:
        return False
    bg = _first_page_bg(css_path)
    if bg is not None:
        lum = _color_luminance(bg, theme_variables(css_path))
        if lum is not None:
            return lum < 0.5
    return bool(re.search(r"dark|night|black", css_path.stem, re.I))


def make_markdown(math: bool = False, mermaid: bool = False):
    from markdown_it import MarkdownIt
    from pygments import highlight
    from pygments.formatters import HtmlFormatter
    from pygments.lexers import get_lexer_by_name
    from pygments.util import ClassNotFound

    def pyg(code: str, lang: str, _attrs: str = "") -> str:
        lang = (lang or "").strip()
        if lang.lower() == "mermaid":
            source = html_mod.escape(code)
            if mermaid:
                # mermaid 库自己扫描 .mermaid 元素并把内容换成 SVG
                return f'<pre class="mermaid">{source}</pre>'
            # 没有 mermaid 资源时降级成代码块，至少能看清源码
            return f'<pre class="md-fences mermaid-source"><code class="language-mermaid">{source}</code></pre>'
        try:
            lexer = get_lexer_by_name(lang) if lang else get_lexer_by_name("text")
        except ClassNotFound:
            lexer = get_lexer_by_name("text")
        inner = _map_tokens(highlight(code, lexer, HtmlFormatter(nowrap=True)))
        lang_attr = f' lang="{html_mod.escape(lang)}"' if lang else ""
        lang_cls = html_mod.escape(lang) if lang else "text"
        # 兼容类名：主题 CSS 通过它们命中代码块（#write > pre.md-fences /
        # .cm-s-inner / .cm-s-typora-default 是这套 DOM 约定的既有标识符，保留以保持兼容）
        # 结构与约定一致：#write > pre.md-fences > div.CodeMirror.cm-s-inner > code。
        # 注意不能把 cm-s-inner/CodeMirror 直接放在 pre 上：主题里的
        # `.cm-s-inner.CodeMirror { background: none }`（特异性更高）会盖掉
        # `.md-fences` 的背景色，代码块就没底色了。
        return (
            f'<pre class="md-fences"{lang_attr}>'
            f'<div class="CodeMirror cm-s-inner cm-s-typora-default">'
            f'<code class="language-{lang_cls}">{inner}</code>'
            f'</div></pre>'
        )

    try:
        import linkify_it  # noqa: F401  # 可选依赖：装了才开启自动链接
        linkify = True
    except ImportError:
        linkify = False

    md = MarkdownIt("gfm-like", {"linkify": linkify, "highlight": pyg, "html": True}).enable("table")
    if math:
        _install_math_rules(md)
    return md, HtmlFormatter


# ------------------------------------------------ 可选前端资源（KaTeX 公式 / Mermaid 图表）
# 与主题同样的策略：仓库不打包这些 JS/CSS，只在需要时下载到用户目录；两者都是 MIT。
ASSET_SETS: dict[str, dict[str, object]] = {
    "katex": {
        "npm": "katex",
        "version": "0.16.11",
        "extract": ["dist/katex.min.js", "dist/katex.min.css", "dist/fonts/*.woff2"],
        "main": "katex.min.js",
        "license": "KaTeX — MIT, Copyright (c) 2013-2020 Khan Academy and other contributors",
    },
    "mermaid": {
        "url_base": "https://cdn.jsdelivr.net/npm/mermaid@11.17.2/dist/",
        "cdn_files": ["mermaid.min.js"],
        "main": "mermaid.min.js",
        "license": "Mermaid — MIT, Copyright (c) 2014-2024 Knut Sveidqvist",
    },
}

# 已经装到系统里的可以直接用（Debian/Ubuntu 的 libjs-katex 等）
SYSTEM_ASSET_DIRS: dict[str, list[str]] = {
    "katex": ["/usr/share/javascript/katex", "/usr/share/nodejs/katex/dist"],
    "mermaid": ["/usr/share/javascript/mermaid", "/usr/share/nodejs/mermaid/dist"],
}
ASSETS_DIR = CONF / "assets"


def resolve_assets(kind: str, cfg: dict[str, str]) -> pathlib.Path | None:
    """找某种前端资源的目录（katex / mermaid），找不到返回 None。

    顺序：配置里的 assets_dir → ~/.config/md-preview/assets/<kind> → 系统目录。
    """
    spec = ASSET_SETS.get(kind)
    if spec is None:
        return None
    main = str(spec["main"])
    candidates: list[pathlib.Path] = []
    custom = cfg.get("assets_dir", "").strip()
    if custom:
        base = pathlib.Path(custom).expanduser()
        candidates += [base / kind, base]
    candidates.append(ASSETS_DIR / kind)
    candidates += [pathlib.Path(p) for p in SYSTEM_ASSET_DIRS.get(kind, [])]
    for cand in candidates:
        if (cand / main).is_file():
            return cand
    return None


def _download_bytes(url: str, timeout: int = 120) -> bytes:
    return _http_get(url, timeout=timeout)


def _extract_from_npm_tarball(spec: dict[str, object], dest: pathlib.Path) -> None:
    """从 npm tarball 里只取需要的文件（KaTeX 的字体是 CSS 相对引用的，得一起拿）。"""
    name, version = str(spec["npm"]), str(spec["version"])
    data = _download_bytes(f"https://registry.npmjs.org/{name}/-/{name}-{version}.tgz")
    patterns = [str(p) for p in spec["extract"]]  # type: ignore[union-attr]
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
        for member in tar.getmembers():
            if not member.isfile():
                continue
            rel = member.name.split("/", 1)[-1] if "/" in member.name else member.name  # 去掉 package/
            if not any(pathlib.PurePosixPath(rel).match(p) for p in patterns):
                continue
            out = dest / rel.split("dist/", 1)[-1]  # dist/fonts/x.woff2 → fonts/x.woff2
            out.parent.mkdir(parents=True, exist_ok=True)
            handle = tar.extractfile(member)
            if handle is not None:
                out.write_bytes(handle.read())


def fetch_assets(names: list[str], cfg: dict[str, str] | None = None) -> bool:
    """把公式/图表用的前端资源下载到用户目录（都是 MIT，见 THIRD-PARTY.md）。"""
    cfg = cfg or {}
    custom = cfg.get("assets_dir", "").strip()
    base = pathlib.Path(custom).expanduser() if custom else ASSETS_DIR
    targets = names or list(ASSET_SETS)
    ok = True
    for name in targets:
        spec = ASSET_SETS.get(name)
        if spec is None:
            print(f"未知资源 {name!r}，可选: {', '.join(ASSET_SETS)}", file=sys.stderr)
            ok = False
            continue
        dest = base / name
        dest.mkdir(parents=True, exist_ok=True)
        print(f"[{name}] {spec['license']}")
        try:
            if spec.get("npm"):
                _extract_from_npm_tarball(spec, dest)
            else:
                for rel in spec["cdn_files"]:  # type: ignore[union-attr]
                    dest.joinpath(pathlib.Path(str(rel)).name).write_bytes(
                        _download_bytes(str(spec["url_base"]) + str(rel))
                    )
        except Exception as exc:  # 网络/解包问题都只提示
            print(f"  下载失败: {exc}", file=sys.stderr)
            ok = False
            continue
        for f in sorted(dest.rglob("*")):
            if f.is_file():
                print(f"  ✓ {f.relative_to(dest)}")
    return ok


def _install_math_rules(md) -> None:
    """把 $…$ / $$…$$ 变成占位元素，交给浏览器里的 KaTeX 渲染。

    这样做而不是直接留着 $ 让 KaTeX 扫描页面，是为了避免 Markdown 先把 `$x_i$` 吃成斜体。
    """

    def math_inline(state, silent: bool) -> bool:
        src, start = state.src, state.pos
        if src[start] != "$" or (start + 1 < state.posMax and src[start + 1] == "$"):
            return False
        if start + 1 >= state.posMax or src[start + 1].isspace():
            return False
        pos = start + 1
        while pos < state.posMax:
            ch = src[pos]
            if ch == "\\":
                pos += 2
                continue
            if ch == "\n":
                return False
            if ch == "$":
                break
            pos += 1
        else:
            return False
        if pos >= state.posMax or pos == start + 1 or src[pos - 1].isspace():
            return False
        if pos + 1 < state.posMax and src[pos + 1].isdigit():
            return False  # $5、$100 这类货币不当公式
        if not silent:
            token = state.push("math_inline", "span", 0)
            token.content = src[start + 1 : pos]
        state.pos = pos + 1
        return True

    def math_block(state, start_line: int, end_line: int, silent: bool) -> bool:
        begin = state.bMarks[start_line] + state.tShift[start_line]
        line = state.src[begin : state.eMarks[start_line]].strip()
        if not line.startswith("$$"):
            return False
        if silent:
            return True
        body: list[str] = []
        first = line[2:]
        next_line = start_line + 1
        if first.endswith("$$") and len(first) > 2:  # $$…$$ 写在一行
            body.append(first[:-2])
        else:
            if first:
                body.append(first)
            while next_line < end_line:
                nbegin = state.bMarks[next_line] + state.tShift[next_line]
                nline = state.src[nbegin : state.eMarks[next_line]]
                if nline.strip().endswith("$$"):
                    body.append(nline.strip()[:-2])
                    next_line += 1
                    break
                body.append(nline)
                next_line += 1
        token = state.push("math_block", "div", 0)
        token.content = "\n".join(body).strip()
        token.map = [start_line, next_line]
        state.line = next_line
        return True

    def render_inline(_self, tokens, idx, _options, _env) -> str:
        return f'<span class="math-inline" data-tex="{html_mod.escape(tokens[idx].content, quote=True)}"></span>'

    def render_block(_self, tokens, idx, _options, _env) -> str:
        tex = html_mod.escape(tokens[idx].content, quote=True)
        return f'<div class="math-block" data-tex="{tex}" data-display="1"></div>'

    md.inline.ruler.before("escape", "math_inline", math_inline)
    md.block.ruler.before("fence", "math_block", math_block)
    md.add_render_rule("math_inline", render_inline)
    md.add_render_rule("math_block", render_block)


def _asset_links(katex_dir: pathlib.Path | None, mermaid_dir: pathlib.Path | None, is_dark: bool) -> str:
    """生成资源引用与渲染脚本；只有文档真的用到公式/图表时才注入。"""
    parts: list[str] = []
    if katex_dir is not None:
        css_uri = (katex_dir / "katex.min.css").as_uri()
        js_uri = (katex_dir / "katex.min.js").as_uri()
        parts.append('<link rel="stylesheet" href="%s">' % css_uri)
        parts.append('<script defer src="%s"></script>' % js_uri)
        parts.append(
            """<script>
document.addEventListener('DOMContentLoaded', function () {
  document.querySelectorAll('[data-tex]').forEach(function (el) {
    if (!window.katex || !el.dataset.tex) return;
    try {
      katex.render(el.dataset.tex, el, {displayMode: el.dataset.display === '1', throwOnError: false, output: 'htmlAndMathml'});
    } catch (err) { console.error('katex:', err); }
  });
});
</script>"""
        )
    if mermaid_dir is not None:
        theme = "dark" if is_dark else "default"
        mermaid_uri = (mermaid_dir / "mermaid.min.js").as_uri()
        parts.append('<script defer src="%s"></script>' % mermaid_uri)
        parts.append(
            f"""<script>
document.addEventListener('DOMContentLoaded', function () {{
  if (!window.mermaid) return;
  mermaid.initialize({{startOnLoad: false, theme: {json.dumps(theme)}}});
  mermaid.run({{nodes: document.querySelectorAll('.mermaid')}}).catch(function (err) {{ console.error('mermaid:', err); }});
}});
</script>"""
        )
    return "\n".join(parts)
# ---------------------------------------------------------------- YAML 头部（front matter）
# 像 SKILL.md / 博客文章这种带 YAML 头部的文档，头部会被渲染成一张信息卡而不是一堆正文。
FRONT_MATTER_MODES = ("card", "raw", "off")
_TITLE_KEYS = ("name", "title")
_CHIP_KEYS = ("version", "license", "author", "authors", "created", "updated", "date", "status", "model")
_FM_KEY = re.compile(r"^[ \t]*[A-Za-z_][\w.-]*[ \t]*:", re.M)


def _yaml_module():
    """有 PyYAML 就用它（更准），没有就退回内置的简单解析器。"""
    try:
        import yaml  # noqa: PLC0415
    except ImportError:
        return None
    return yaml


def split_front_matter(text: str) -> tuple[str | None, str]:
    """拆出文档开头的 YAML 头部，返回 (yaml 源码, 正文)；没有头部时返回 (None, 原文)。

    只有 `---` 成对出现、且中间确实像 `key: value` 时才认作头部，
    免得把「以分隔线开头的普通文档」也吃掉。
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, text
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            head = lines[1:index]
            if not _FM_KEY.search("\n".join(head)):
                return None, text  # 中间没有 key:，当普通内容处理
            return "\n".join(head), "\n".join(lines[index + 1 :])
    return None, text


def _plain_scalar(value: str) -> object:
    text = value.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "'\"":
        return text[1:-1]
    if text.lower() in ("true", "false"):
        return text.lower() == "true"
    if re.fullmatch(r"-?\d+", text):
        return int(text)
    if re.fullmatch(r"-?\d+\.\d+", text):
        return float(text)
    return text


def _parse_simple_yaml(source: str) -> dict[str, object] | None:
    """内置的极简 YAML 子集解析器：标量、引号、行内列表、块列表、块标量。

    只覆盖 Markdown 头部常见写法；遇到嵌套映射等复杂结构返回 None（退化为原文显示）。
    装了 PyYAML 时走不到这里。
    """
    result: dict[str, object] = {}
    lines = source.splitlines()
    index = 0
    while index < len(lines):
        line = lines[index]
        if not line.strip() or line.strip().startswith("#"):
            index += 1
            continue
        if line[:1].isspace() or ":" not in line:
            return None
        key, _, value = line.partition(":")
        key, value = key.strip(), value.strip()
        if not key:
            return None
        if value in ("|", "|-", ">", ">-"):  # 块标量
            index += 1
            block: list[str] = []
            while index < len(lines) and (not lines[index].strip() or lines[index][:1].isspace()):
                block.append(lines[index].strip())
                index += 1
            text = "\n".join(block).strip()
            result[key] = " ".join(text.split()) if value.startswith(">") else text
            continue
        if value.startswith("[") and value.endswith("]"):  # 行内列表
            result[key] = [item for item in (_plain_scalar(p) for p in value[1:-1].split(",")) if item != ""]
            index += 1
            continue
        if value == "":  # 可能是块列表
            index += 1
            items: list[object] = []
            while index < len(lines) and lines[index][:1].isspace() and lines[index].strip():
                stripped = lines[index].strip()
                if not stripped.startswith("- "):
                    return None
                items.append(_plain_scalar(stripped[2:]))
                index += 1
            result[key] = items if items else ""
            continue
        result[key] = _plain_scalar(value)
        index += 1
    return result or None


def parse_front_matter(source: str) -> dict[str, object] | None:
    """解析 YAML 头部；拿不到映射就返回 None（调用方退化为原文显示）。"""
    module = _yaml_module()
    if module is not None:
        try:
            data = module.safe_load(source)
        except Exception:  # YAML 有语法错误时再用内置解析器兜一次
            data = None
        if isinstance(data, dict):
            return {str(key): value for key, value in data.items()}
        if data is None:
            return _parse_simple_yaml(source)
        return None
    return _parse_simple_yaml(source)


def _fm_value_html(value: object) -> str:
    """字段值：列表 → chips，嵌套映射 → 子 dl，多行 → pre，其余按行内。"""
    if isinstance(value, (list, tuple)):
        chips = "".join(f"<li>{html_mod.escape(str(item))}</li>" for item in value)
        return f'<ul class="fm-chips">{chips}</ul>'
    if isinstance(value, dict):
        rows = "".join(
            f"<dt>{html_mod.escape(str(k))}</dt><dd>{_fm_value_html(v)}</dd>" for k, v in value.items()
        )
        return f'<dl class="fm-nested">{rows}</dl>'
    text = str(value)
    if "\n" in text:
        return f"<pre>{html_mod.escape(text)}</pre>"
    return html_mod.escape(text)


def front_matter_html(meta: dict[str, object] | None, raw: str, mode: str = "card") -> str:
    """把 YAML 头部渲染成信息卡（mode: card / raw / off）。"""
    if mode == "off":
        return ""
    if mode == "raw" or meta is None:
        hint = '<p class="fm-hint">头部无法解析为映射，按原文显示</p>' if meta is None else ""
        return (
            '<section class="front-matter" data-format="raw">'
            f'<pre class="fm-raw">{html_mod.escape(raw)}</pre>{hint}</section>\n'
        )

    title_key = next((k for k in _TITLE_KEYS if str(meta.get(k, "")).strip()), None)
    title = str(meta[title_key]) if title_key else ""
    chips = [f"{k} {meta[k]}" for k in _CHIP_KEYS if k in meta and not isinstance(meta[k], (list, dict))]
    keys = [k for k in meta if k not in _TITLE_KEYS and k not in _CHIP_KEYS]
    keys.sort(key=lambda k: 0 if k in ("description", "summary") else 1)  # 描述放最前面

    head = ""
    if title or chips:
        chip_html = "".join(f'<span class="fm-chip">{html_mod.escape(chip)}</span>' for chip in chips)
        head = f'<div class="fm-title"><span class="fm-name">{html_mod.escape(title)}</span>{chip_html}</div>'
    rows = "".join(f"<dt>{html_mod.escape(str(key))}</dt><dd>{_fm_value_html(meta[key])}</dd>" for key in keys)
    fields = f'<dl class="fm-fields">{rows}</dl>' if rows else ""
    return f'<section class="front-matter" data-format="yaml">{head}{fields}</section>\n'


# ---------------------------------------------------------------- 渲染
def _theme_link(css_path: pathlib.Path | None, media: str | None = None) -> str:
    if css_path is None:
        return ""
    attr = f' media="{media}"' if media else ""
    return f'<link rel="stylesheet"{attr} href="{css_path.resolve().as_uri()}">'


def _flag_on(cfg: dict[str, str], key: str, default: bool = True) -> bool:
    """读一个开关型配置：math / mermaid，默认开；off/none/0/false/no 视为关。"""
    value = cfg.get(key, "").strip().lower()
    if not value:
        return default
    return value not in ("off", "none", "0", "false", "no")


def render_html(src_path: pathlib.Path, css: str, cfg: dict[str, str], mode: str) -> tuple[pathlib.Path, pathlib.Path, dict]:
    theme_name = cfg.get("theme", "github")
    dark_name = cfg.get("dark_theme", "")
    pdf_name = cfg.get("pdf_theme", "")

    theme = theme_path(theme_name)
    if theme is None and theme_name and theme_name != "none":
        print(f"md-preview: 主题 {theme_name!r} 不存在，改用内置兜底样式", file=sys.stderr)
    if theme is None:
        theme = FALLBACK_THEME if FALLBACK_THEME.exists() else PACKAGE_FALLBACK

    if mode == "pdf":
        active_name, active = (pdf_name or theme_name), (theme_path(pdf_name) if pdf_name else theme)
    else:
        active_name, active = theme_name, theme

    dark = theme_path(dark_name) if (dark_name and mode != "pdf") else None
    is_dark = is_dark_theme(active)
    # 有些主题把页面底色交给宿主应用处理，自己只定义 --bg-color 变量，
    # 单独渲染 HTML/PDF 时必须补上，否则深色主题会变成「白底浅字」。
    page_bg_css = ""
    if _first_page_bg(active) is None:
        page_bg_css = (
            "body { background-color: var(--bg-color, #ffffff); }\n"
            "body.md-dark { background-color: var(--bg-color, #1f2328); }"
        )

    key = hashlib.sha1(str(src_path.resolve()).encode("utf-8")).hexdigest()[:12]
    outdir = CACHE / key
    outdir.mkdir(parents=True, exist_ok=True)

    raw_text = src_path.read_text(encoding="utf-8", errors="replace")
    fm_mode = (cfg.get("front_matter", "card") or "card").strip().lower()
    if fm_mode not in FRONT_MATTER_MODES:
        fm_mode = "card"
    fm_source, text = split_front_matter(raw_text)
    if fm_mode == "off":
        fm_source = None  # off = 剥掉头部但不渲染（既不显示卡片，也不留原始 YAML）
    fm_meta = parse_front_matter(fm_source) if fm_source is not None else None
    fm_card = front_matter_html(fm_meta, fm_source or "", fm_mode) if fm_source is not None else ""
    katex_dir = resolve_assets("katex", cfg) if _flag_on(cfg, "math") else None
    mermaid_dir = resolve_assets("mermaid", cfg) if _flag_on(cfg, "mermaid") else None
    md, HtmlFormatter = make_markdown(math=katex_dir is not None, mermaid=mermaid_dir is not None)
    body = fm_card + _add_heading_ids(md.render(text))

    needs_math = "data-tex=" in body
    needs_mermaid = '<pre class="mermaid">' in body
    if needs_math and katex_dir is None:
        print("md-preview: 文档里有公式但没找到 KaTeX 资源，先按源码显示；"
              "可运行 md-preview --fetch-assets katex", file=sys.stderr)
    if 'class="mermaid-source"' in body:
        print("md-preview: 文档里有 mermaid 图表但没找到 mermaid 资源，先按代码块显示；"
              "可运行 md-preview --fetch-assets mermaid", file=sys.stderr)
    use_katex = katex_dir if needs_math else None
    use_mermaid = mermaid_dir if needs_mermaid else None

    title = src_path.stem
    first = re.search(r"<h1[^>]*>(.*?)</h1>", body, re.S)
    if first:
        title = re.sub(r"<[^>]+>", "", first.group(1)).strip() or title
    elif fm_meta:
        fm_title = str(fm_meta.get("name") or fm_meta.get("title") or "").strip()
        if fm_title:
            title = fm_title

    links = _theme_link(active, None)
    if dark is not None and dark != active:
        links += "\n" + _theme_link(dark, "screen and (prefers-color-scheme: dark)")

    asset_links = _asset_links(use_katex, use_mermaid, is_dark)
    uses_js = bool(use_katex or use_mermaid)

    html = TEMPLATE.format(
        base=src_path.resolve().parent.as_uri() + "/",
        title=html_mod.escape(title),
        body_class=" md-dark" if is_dark else "",
        bridge=BASE_CSS,
        page_bg=page_bg_css,
        pyg_light=HtmlFormatter(style="github-dark" if is_dark else "default").get_style_defs(".md-fences"),
        pyg_dark=HtmlFormatter(style="github-dark").get_style_defs(".md-fences"),
        theme_links=links,
        asset_links=asset_links,
        print_css=PRINT_CSS,
        body=body,
    )
    html_path = outdir / (src_path.stem + ".html")
    html_path.write_text(html, encoding="utf-8")
    return html_path, outdir, {
        "theme": active_name,
        "theme_file": str(active) if active else "",
        "dark": str(dark) if dark else "",
        "assets": [str(p) for p in (use_katex, use_mermaid) if p is not None],
        "js": uses_js,
    }


def _find_chromium() -> str | None:
    for path in CHROMIUM_CANDIDATES:
        if os.access(path, os.X_OK):
            return path
    return None


def _needs_no_sandbox() -> bool:
    """受限环境里 Chromium 的沙箱会 SIGABRT（CI 容器、以 root 运行等），需要显式关掉。

    只在 CI（设置了 CI 环境变量）或以 root 运行时关闭；普通桌面用户保持沙箱开启。
    """
    if os.environ.get("CI"):
        return True
    try:
        return os.geteuid() == 0
    except AttributeError:  # 非 POSIX 平台
        return False


def _js_budget(cfg: dict[str, str]) -> int:
    """给 JS 渲染留的虚拟时间预算（毫秒）；图表复杂的文档可以调大。"""
    try:
        return max(0, int(cfg.get("js_budget", "") or 10000))
    except ValueError:
        return 10000


def to_pdf(html_path: pathlib.Path, outdir: pathlib.Path, pdf_path: pathlib.Path, sig: str, js_budget: int = 0) -> pathlib.Path | None:
    stamp = outdir / ".stamp"
    if pdf_path.exists() and stamp.exists() and stamp.read_text(encoding="utf-8") == sig:
        return pdf_path

    chrome = _find_chromium()
    if chrome is None:
        print("md-preview: 找不到 Chromium 系浏览器，改用浏览器打开 HTML", file=sys.stderr)
        return None

    pdf_path.unlink(missing_ok=True)
    cmd = [
        chrome,
        "--headless=new",
        "--disable-gpu",
        "--no-pdf-header-footer",
        "--no-first-run",
        "--no-default-browser-check",
        f"--user-data-dir={CACHE / 'chrome-profile'}",
        f"--print-to-pdf={pdf_path}",
        html_path.as_uri(),
    ]
    if js_budget > 0:
        # 给要跑 JS 的页面（KaTeX 公式、Mermaid 图表）留出渲染时间再快照
        cmd.append(f"--virtual-time-budget={int(js_budget)}")
    if _needs_no_sandbox():
        cmd.append("--no-sandbox")
    try:
        result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=180)
    except subprocess.TimeoutExpired:
        print("md-preview: 生成 PDF 超时", file=sys.stderr)
        result = None

    if pdf_path.exists() and pdf_path.stat().st_size > 0:
        stamp.write_text(sig, encoding="utf-8")
        return pdf_path

    # 打不出来的话把浏览器的话带回来，方便排查（CI、无沙箱环境等）
    if result is not None and result.returncode not in (0, None):
        detail = (result.stderr or b"").decode("utf-8", "replace").strip().splitlines()
        print(f"md-preview: 无头浏览器返回 {result.returncode}，未能生成 PDF"
              + (f"：{detail[-1]}" if detail else ""), file=sys.stderr)
    return None


# ---------------------------------------------------------------- 可选主题集（只收录许可明确的来源）
# 本项目不打包、也不再分发第三方 CSS：只在用户显式执行 --fetch-themes 时，
# 直接从上游仓库下载到用户自己的主题目录。许可与出处见 THIRD-PARTY.md。
THEME_SETS: dict[str, dict[str, object]] = {
    "drake": {
        "repo": "liangjingkanji/DrakeTyporaTheme",
        "branch": "master",
        "prefix": "",
        "assets": False,
        "extra": [
            "drake/font.css",
            "drake/JetBrainsMono-Regular.woff2",
            "drake/JetBrainsMono-Bold.woff2",
            "drake/JetBrainsMono-Italic.woff2",
            "drake/JetBrainsMono-BoldItalic.woff2",
        ],
        "license": "MIT License, Copyright (c) 2023 劉強東",
    },
    "mdmdt": {
        "repo": "cayxc/Mdmdt",
        "branch": "main",
        "prefix": "",
        "assets": False,
        "license": "Apache-2.0",
    },
}


def _http_get(url: str, timeout: int = 60) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "md-preview"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def fetch_themes(sets: list[str]) -> bool:
    """从上游仓库拉取主题（含字体等资源）到 ~/.config/md-preview/themes/。"""
    ok = True
    THEMES.mkdir(parents=True, exist_ok=True)
    for name in sets:
        spec = THEME_SETS.get(name)
        if spec is None:
            print(f"未知主题集 {name!r}，可选: {', '.join(THEME_SETS)}", file=sys.stderr)
            ok = False
            continue
        repo, branch, prefix = str(spec["repo"]), str(spec["branch"]), str(spec["prefix"])
        try:
            tree = json.loads(_http_get(f"https://api.github.com/repos/{repo}/git/trees/{branch}?recursive=1"))
            blobs = [item["path"] for item in tree.get("tree", []) if item.get("type") == "blob"]
        except Exception as exc:  # 网络/JSON 出问题都只提示，不中断
            print(f"[{name}] 读取仓库清单失败: {exc}", file=sys.stderr)
            ok = False
            continue

        wanted = [p for p in blobs if re.fullmatch(re.escape(prefix) + r"[^/]+\.css", p)]
        if spec.get("assets"):
            # 主题若带字体等资源，放在与 css 同名的子目录里，一并拉下来
            for path in list(wanted):
                stem = pathlib.Path(path).stem
                wanted += [p for p in blobs if p.startswith(f"{prefix}{stem}/")]
        for extra in spec.get("extra") or []:
            if extra in blobs:
                wanted.append(str(extra))

        print(f"[{name}] {len(set(wanted))} 个文件  |  {spec['license']}")
        for path in dict.fromkeys(wanted):
            target = THEMES / path[len(prefix) :]
            target.parent.mkdir(parents=True, exist_ok=True)
            try:
                target.write_bytes(_http_get(f"https://raw.githubusercontent.com/{repo}/{branch}/{path}"))
            except Exception as exc:  # 网络出问题只提示
                print(f"  ✗ {path}: {exc}", file=sys.stderr)
                ok = False
                continue
            print(f"  ✓ {target.relative_to(THEMES)}")
    return ok


def run(args: list[str]) -> int:
    if "--version" in args:
        print(f"md-preview {__version__}")
        return 0
    if "--fetch-themes" in args:
        i = args.index("--fetch-themes")
        wanted = [a for a in args[i + 1 :] if not a.startswith("-")] or list(THEME_SETS)
        return 0 if fetch_themes(wanted) else 1
    if "--fetch-assets" in args:
        i = args.index("--fetch-assets")
        wanted = [a for a in args[i + 1 :] if not a.startswith("-")] or list(ASSET_SETS)
        return 0 if fetch_assets(wanted, read_config()) else 1
    # --- 简单选项 ---
    if "--list-themes" in args:
        for t in list_themes():
            print(t)
        return 0
    if "--theme-dir" in args:
        print(THEMES)
        return 0
    if "--install-theme" in args:
        i = args.index("--install-theme")
        if i + 1 >= len(args):
            print("用法: md-preview --install-theme <URL 或 .css 路径>", file=sys.stderr)
            return 2
        src = args[i + 1]
        THEMES.mkdir(parents=True, exist_ok=True)
        dest = THEMES / (pathlib.Path(src.split("?")[0]).name or "theme.css")
        if src.startswith(("http://", "https://")):
            if shutil.which("curl") is None:
                print("需要 curl 才能从 URL 安装主题", file=sys.stderr)
                return 2
            if subprocess.run(["curl", "-sSL", "--max-time", "60", "-o", str(dest), src]).returncode != 0:
                print("下载失败", file=sys.stderr)
                return 2
        else:
            shutil.copy2(pathlib.Path(src).expanduser(), dest)
        print(f"已安装主题: {dest.stem}  ({dest})")
        return 0

    mode = "pdf"
    for flag in ("--html", "--browser"):
        if flag in args:
            args.remove(flag)
            mode = "html"

    cfg = read_config()
    for opt, key in (
        ("--theme", "theme"),
        ("--dark-theme", "dark_theme"),
        ("--pdf-theme", "pdf_theme"),
        ("--assets-dir", "assets_dir"),
        ("--front-matter", "front_matter"),
    ):
        if opt in args:
            i = args.index(opt)
            if i + 1 < len(args):
                cfg[key] = args[i + 1]
                del args[i : i + 2]

    for flag, key in (("--no-math", "math"), ("--no-mermaid", "mermaid")):
        if flag in args:
            args.remove(flag)
            cfg[key] = "off"

    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        return 0 if args else 1

    CONF.mkdir(parents=True, exist_ok=True)

    for raw in args:
        src = pathlib.Path(raw).expanduser()
        if not src.is_file():
            print(f"md-preview: 跳过不存在的文件 {src}", file=sys.stderr)
            continue

        html_path, outdir, meta = render_html(src, BASE_CSS, cfg, mode)

        if mode == "html":
            subprocess.Popen(["xdg-open", str(html_path)], start_new_session=True)
            continue

        # 缓存签名：源文件 mtime + 脚本自身 + 主题文件 + 配置
        sig_parts = [str(BRIDGE_VERSION), str(src.stat().st_mtime_ns), str(pathlib.Path(__file__).stat().st_mtime_ns)]
        for p in [meta["theme_file"], meta["dark"], *meta.get("assets", [])]:
            if p and pathlib.Path(p).exists():
                st = pathlib.Path(p).stat()
                sig_parts += [p, str(st.st_mtime_ns), str(st.st_size)]
        sig_parts += [str(cfg.get("math", "auto")), str(cfg.get("mermaid", "auto"))]
        sig = hashlib.sha1(":".join(sig_parts).encode("utf-8")).hexdigest()

        pdf_path = outdir / (src.stem + ".pdf")
        pdf = to_pdf(html_path, outdir, pdf_path, sig, js_budget=_js_budget(cfg) if meta.get("js") else 0)

        if pdf is None:
            subprocess.Popen(["xdg-open", str(html_path)], start_new_session=True)
            continue
        if os.access("/usr/bin/" + VIEWER_PDF, os.X_OK):
            subprocess.Popen([VIEWER_PDF, str(pdf)], start_new_session=True)
        else:
            subprocess.Popen(["xdg-open", str(pdf)], start_new_session=True)

    return 0


def main(argv: list[str] | None = None) -> int:
    """命令行入口（pyproject 的 console_scripts 指向这里）。"""
    try:
        return run(list(sys.argv[1:] if argv is None else argv))
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
