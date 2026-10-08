"""md-preview 的测试：纯函数 + 渲染结构 + 可选端到端 PDF。

    python3 -m pytest -q                    # 全部
    python3 -m pytest -q -k "not pdf"       # 跳过需要浏览器的端到端
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parent.parent
SRC = REPO / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import md_preview.cli as cli  # noqa: E402

SAMPLE = REPO / "tests" / "sample.md"


def load_module(name: str, path: pathlib.Path):
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


# ------------------------------------------------------------------ 纯函数
@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("#fff", pytest.approx(1.0)),
        ("#000", pytest.approx(0.0)),
        ("#1b1b1f", pytest.approx(0.109, abs=0.01)),
        ("rgb(255, 255, 255)", pytest.approx(1.0)),
        ("rgba(0, 0, 0, 0.5)", pytest.approx(0.0)),
        ("white", pytest.approx(1.0)),
        ("black", pytest.approx(0.0)),
        ("rebeccapurple", None),
    ],
)
def test_color_luminance(value, expected):
    result = cli._color_luminance(value, {})
    if expected is None:
        assert result is None
    else:
        assert result == expected


def test_color_luminance_resolves_variable():
    assert cli._color_luminance("var(--bg-color)", {"--bg-color": "#000"}) == 0.0
    assert cli._color_luminance("var(--missing)", {}) is None


def test_is_dark_theme_of_bundled_fallback():
    assert cli.is_dark_theme(SRC / "md_preview" / "fallback.css") is False


def test_is_dark_theme_reads_variable(tmp_path):
    css = tmp_path / "dark.css"
    css.write_text(":root{--bg-color:#1b1b1f}\nbody{background-color:var(--bg-color)}\n", encoding="utf-8")
    assert cli.is_dark_theme(css) is True


def test_is_dark_theme_uses_first_variable_definition(tmp_path):
    # mdmdt-light 这类主题会在文件后面再定义一份暗色变体，不能因此判成深色
    css = tmp_path / "light.css"
    css.write_text(
        ":root{--bg-color:rgb(250, 250, 252)}\nbody{background:var(--bg-color)}\n"
        "body.dark{--bg-color:#1b1b1f}\n",
        encoding="utf-8",
    )
    assert cli.is_dark_theme(css) is False


def test_is_dark_theme_skips_dark_media_query(tmp_path):
    css = tmp_path / "auto.css"
    css.write_text(
        "@media (prefers-color-scheme: dark){ body{background:#111} }\nbody{background:#fff}\n",
        encoding="utf-8",
    )
    assert cli.is_dark_theme(css) is False


def test_is_dark_theme_ignores_commented_out_declaration(tmp_path):
    css = tmp_path / "commented.css"
    css.write_text("body{/*background:#000*/background:#fff}\n", encoding="utf-8")
    assert cli.is_dark_theme(css) is False


def test_map_tokens_adds_codemirror_classes():
    out = cli._map_tokens('<span class="k">def</span><span class="s2">"x"</span>')
    assert 'class="k cm-keyword"' in out
    assert 'class="s2 cm-string"' in out
    # 未知 token 保持原样，不会丢类名
    assert cli._map_tokens('<span class="zz">x</span>') == '<span class="zz">x</span>'


def test_heading_ids_are_added():
    out = cli._add_heading_ids("<h2>二级 标题 / Test</h2><p>x</p>")
    assert '<h2 id="' in out
    assert "  " not in cli._slug("二级  标题")


# ------------------------------------------------------------------ 主题解析
def test_theme_path_resolution(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "THEMES", tmp_path)
    (tmp_path / "alpha.css").write_text("body{}", encoding="utf-8")
    assert cli.theme_path("alpha") == tmp_path / "alpha.css"
    assert cli.theme_path("missing") is None
    assert cli.theme_path("") is None
    custom = tmp_path / "outside.css"
    custom.write_text("body{}", encoding="utf-8")
    assert cli.theme_path(str(custom)) == custom


def test_list_themes_ignores_asset_subdirs(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "THEMES", tmp_path)
    (tmp_path / "alpha.css").write_text("", encoding="utf-8")
    (tmp_path / "beta.css").write_text("", encoding="utf-8")
    (tmp_path / "alpha").mkdir()
    (tmp_path / "alpha" / "font.css").write_text("", encoding="utf-8")
    assert {"alpha", "beta"} <= set(cli.list_themes())  # 自带主题也会列出
    assert "font" not in cli.list_themes()  # 资源子目录里的 font.css 不算主题


def test_fetch_themes_rejects_unknown_set(capsys):
    assert cli.fetch_themes(["nope"]) is False
    assert "未知主题集" in capsys.readouterr().err


# ------------------------------------------------------------------ 渲染
def _prepare(tmp_path, monkeypatch, theme_css: str | None = None):
    themes = tmp_path / "themes"
    themes.mkdir(exist_ok=True)
    if theme_css is not None:
        (themes / "test.css").write_text(theme_css, encoding="utf-8")
    monkeypatch.setattr(cli, "THEMES", themes)
    monkeypatch.setattr(cli, "CACHE", tmp_path / "cache")
    monkeypatch.setattr(cli, "CONF", tmp_path / "conf")
    monkeypatch.setattr(cli, "CONFIG_FILE", tmp_path / "conf" / "config")
    monkeypatch.setattr(cli, "FALLBACK_THEME", tmp_path / "conf" / "style.css")
    return themes


def test_render_html_structure_and_theme_link(tmp_path, monkeypatch):
    _prepare(tmp_path, monkeypatch, "#write{max-width:640px}\nbody{background:#fff}\n")
    html_path, _, meta = cli.render_html(SAMPLE, cli.BASE_CSS, {"theme": "test"}, "html")
    html = html_path.read_text(encoding="utf-8")
    assert '<body class="typora-export">' in html
    assert '<div id="write" class="typora-export">' in html
    assert 'class="md-fences"' in html
    assert "cm-keyword" in html  # Pygments token 映射
    assert "test.css" in html  # 主题以 link 引入
    assert "print-color-adjust" in html
    assert meta["theme"] == "test"


def test_render_html_marks_dark_theme(tmp_path, monkeypatch):
    # 主题只给变量、把页面底色交给宿主（Drake 系列就是这样），我们需要自己补页面底色
    _prepare(tmp_path, monkeypatch, ":root{--bg-color:#1b1b1f}\n")
    themes = tmp_path / "themes"
    (themes / "dark-test.css").write_text(":root{--bg-color:#1b1b1f}\n", encoding="utf-8")
    html_path, _, _ = cli.render_html(SAMPLE, cli.BASE_CSS, {"theme": "dark-test"}, "html")
    html = html_path.read_text(encoding="utf-8")
    assert '<body class="typora-export md-dark">' in html
    assert "background-color: var(--bg-color, #1f2328)" in html


def test_render_html_keeps_theme_page_background(tmp_path, monkeypatch):
    # 主题自己给了 body 底色时不要去覆盖它
    _prepare(tmp_path, monkeypatch, ":root{--bg-color:#1b1b1f}\nbody{background-color:var(--bg-color)}\n")
    html_path, _, _ = cli.render_html(SAMPLE, cli.BASE_CSS, {"theme": "test"}, "html")
    html = html_path.read_text(encoding="utf-8")
    assert '<body class="typora-export md-dark">' in html
    assert "background-color: var(--bg-color, #1f2328)" not in html


def test_render_html_falls_back_without_theme(tmp_path, monkeypatch):
    _prepare(tmp_path, monkeypatch, None)
    html_path, _, _ = cli.render_html(SAMPLE, cli.BASE_CSS, {"theme": "does-not-exist"}, "html")
    html = html_path.read_text(encoding="utf-8")
    assert "fallback.css" in html  # 解析到包内兜底样式


def test_cli_version(capsys):
    assert cli.main(["--version"]) == 0
    assert cli.__version__ in capsys.readouterr().out


def test_cli_unknown_missing_file_is_skipped(capsys, tmp_path, monkeypatch):
    _prepare(tmp_path, monkeypatch, None)
    assert cli.main([str(tmp_path / "nope.md")]) == 0
    assert "跳过" in capsys.readouterr().err


# ------------------------------------------------------------------ 端到端
@pytest.mark.skipif(cli._find_chromium() is None, reason="需要 Chromium 系浏览器（Edge/Chrome/Chromium）")
def test_end_to_end_pdf(tmp_path, monkeypatch):
    _prepare(tmp_path, monkeypatch, None)
    html_path, outdir, meta = cli.render_html(SAMPLE, cli.BASE_CSS, {"theme": ""}, "pdf")
    pdf = outdir / f"{SAMPLE.stem}.pdf"
    assert cli.to_pdf(html_path, outdir, pdf, "test-sig") == pdf
    data = pdf.read_bytes()
    assert data.startswith(b"%PDF")
    assert len(data) > 2000
    # 第二次调用命中缓存（不再调用浏览器）
    assert cli.to_pdf(html_path, outdir, pdf, "test-sig") == pdf


# ------------------------------------------------------------------ mimeapps 合并
def test_merge_mimeapps_preserves_rest_and_is_reversible(tmp_path):
    module = load_module("merge_mimeapps", REPO / "contrib" / "merge-mimeapps.py")
    path = tmp_path / "mimeapps.list"
    original = "[Added Associations]\nimage/svg+xml=lunacy.desktop;\n"
    path.write_text(original, encoding="utf-8")

    module.main([
        "--file", str(path),
        "--mime", "text/markdown",
        "--default", "org.kde.kate.desktop",
        "--order", "md-preview.desktop;md-preview-browser.desktop;okularApplication_md.desktop",
    ])
    text = path.read_text(encoding="utf-8")
    assert "image/svg+xml=lunacy.desktop;" in text
    assert "[Default Applications]" in text
    assert "text/markdown=org.kde.kate.desktop" in text
    assert "text/markdown=md-preview.desktop;md-preview-browser.desktop;okularApplication_md.desktop" in text
    assert (tmp_path / "mimeapps.list.bak-md-preview").exists()

    # 幂等：再跑一次不重复添加
    module.main(["--file", str(path), "--mime", "text/markdown", "--order", "md-preview.desktop"])
    text = path.read_text(encoding="utf-8")
    assert text.count("text/markdown=") == 2

    module.main(["--file", str(path), "--mime", "text/markdown", "--restore"])
    assert path.read_text(encoding="utf-8") == original
    assert not (tmp_path / "mimeapps.list.bak-md-preview").exists()
