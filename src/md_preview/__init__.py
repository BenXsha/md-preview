"""md-preview —— 用纯 CSS 主题把 Markdown 渲染成带样式的 PDF / HTML。

设计目标是「中键一点就能看」：默认转成 PDF 交给 Okular，或用浏览器打开 HTML。
"""

from .cli import __version__, fetch_themes, list_themes, main, run, theme_path

__all__ = ["__version__", "fetch_themes", "list_themes", "main", "run", "theme_path"]
