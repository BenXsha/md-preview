#!/usr/bin/env python3
"""md-preview —— 把 Markdown 渲染成带样式的 PDF / HTML，专为「中键看一眼」设计。

最适合的场景是 KDE(Dolphin) 的鼠标中键预览：中键点一个 .md，直接得到排版漂亮的预览
（默认渲染成 PDF 交给 Okular，或 --html 用浏览器打开）。

样式来自**纯 CSS 主题**：项目生成的 HTML 遵循通用的 Markdown 主题 DOM 约定
（`#write` / `pre.md-fences` / `div.CodeMirror.cm-s-inner` / `.cm-*` token 类），
任何按这套约定书写的 CSS 都能直接用。自带两个 MIT 许可的主题（`default` / `default-dark`），
开箱即用、不需要联网；需要更多风格时可安装自己信任的主题文件。

用法:
  md-preview FILE.md                渲染成带主题样式的 PDF，用 Okular 打开（默认，带缓存）
  md-preview --html FILE.md         渲染成 HTML，用默认浏览器打开
  md-preview --theme default-dark FILE.md
  md-preview --list-themes          列出可用主题（自带 + 已安装）
  md-preview --fetch-themes         可选：拉取带明确开源许可的社区主题集（见 THIRD-PARTY.md）
  md-preview --install-theme <URL 或 .css 路径>
  md-preview --theme-dir            打印主题目录（把任意 .css 丢进去即可生效）
  md-preview --version

配置: ~/.config/md-preview/config
    theme      = default       # 默认主题（default / default-dark 为自带主题）
    dark_theme = default-dark  # 浏览器预览时系统为深色模式则换成这个（可留空）
    pdf_theme  =               # PDF 模式专用主题（留空 = 用 theme）

主题目录: ~/.config/md-preview/themes/   缓存目录: ~/.cache/md-preview/<hash>/
许可说明: 主题由使用者自行添加；本项目只收录许可明确的来源，详见 THIRD-PARTY.md
"""

from __future__ import annotations

import html as html_mod
import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
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
__version__ = "0.2.0"

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
:root { --mp-fence-bg: #f6f8fa; --mp-inline-bg: #f6f8fa; }
body.md-dark { --mp-fence-bg: #22272e; --mp-inline-bg: #2d333b; }

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
    if bundled is not None:
        return bundled if bundled.is_file() else None
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


def make_markdown():
    from markdown_it import MarkdownIt
    from pygments import highlight
    from pygments.formatters import HtmlFormatter
    from pygments.lexers import get_lexer_by_name
    from pygments.util import ClassNotFound

    def pyg(code: str, lang: str, _attrs: str = "") -> str:
        lang = (lang or "").strip()
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

    return MarkdownIt("gfm-like", {"linkify": linkify, "highlight": pyg, "html": True}).enable("table"), HtmlFormatter


# ---------------------------------------------------------------- 渲染
def _theme_link(css_path: pathlib.Path | None, media: str | None = None) -> str:
    if css_path is None:
        return ""
    attr = f' media="{media}"' if media else ""
    return f'<link rel="stylesheet"{attr} href="{css_path.resolve().as_uri()}">'


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

    text = src_path.read_text(encoding="utf-8", errors="replace")
    md, HtmlFormatter = make_markdown()
    body = _add_heading_ids(md.render(text))

    title = src_path.stem
    first = re.search(r"<h1[^>]*>(.*?)</h1>", body, re.S)
    if first:
        title = re.sub(r"<[^>]+>", "", first.group(1)).strip() or title

    links = _theme_link(active, None)
    if dark is not None and dark != active:
        links += "\n" + _theme_link(dark, "screen and (prefers-color-scheme: dark)")

    html = TEMPLATE.format(
        base=src_path.resolve().parent.as_uri() + "/",
        title=html_mod.escape(title),
        body_class=" md-dark" if is_dark else "",
        bridge=BASE_CSS,
        page_bg=page_bg_css,
        pyg_light=HtmlFormatter(style="github-dark" if is_dark else "default").get_style_defs(".md-fences"),
        pyg_dark=HtmlFormatter(style="github-dark").get_style_defs(".md-fences"),
        theme_links=links,
        print_css=PRINT_CSS,
        body=body,
    )
    html_path = outdir / (src_path.stem + ".html")
    html_path.write_text(html, encoding="utf-8")
    return html_path, outdir, {"theme": active_name, "theme_file": str(active) if active else "", "dark": str(dark) if dark else ""}


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


def to_pdf(html_path: pathlib.Path, outdir: pathlib.Path, pdf_path: pathlib.Path, sig: str) -> pathlib.Path | None:
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
    for opt, key in (("--theme", "theme"), ("--dark-theme", "dark_theme"), ("--pdf-theme", "pdf_theme")):
        if opt in args:
            i = args.index(opt)
            if i + 1 < len(args):
                cfg[key] = args[i + 1]
                del args[i : i + 2]

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
        for p in (meta["theme_file"], meta["dark"]):
            if p and pathlib.Path(p).is_file():
                st = pathlib.Path(p).stat()
                sig_parts += [p, str(st.st_mtime_ns), str(st.st_size)]
        sig = hashlib.sha1(":".join(sig_parts).encode("utf-8")).hexdigest()

        pdf_path = outdir / (src.stem + ".pdf")
        pdf = to_pdf(html_path, outdir, pdf_path, sig)

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
