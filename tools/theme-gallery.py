#!/usr/bin/env python3
"""给所有已安装主题生成对比截图，并拼成一张图用来挑主题。

用法:
    python3 tools/theme-gallery.py                          # 用 tests/sample.md
    python3 tools/theme-gallery.py --src 文档.md --out ~/图片/主题对比
    python3 tools/theme-gallery.py --cols 3 --width 800 --height 1000

输出: <out>/<主题>.png（单图）、<out>/<主题>.html（渲染结果）、<out>/_contact-sheet.png（拼版）
依赖: Pillow + Chromium 系浏览器（Edge/Chrome/Chromium）
"""

from __future__ import annotations

import argparse
import pathlib
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

import md_preview.cli as cli  # noqa: E402

try:
    from PIL import Image, ImageDraw, ImageStat
except ImportError:  # pragma: no cover - 只在缺依赖时触发
    sys.exit("需要 Pillow: pip install Pillow")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--src", default=str(REPO / "tests" / "sample.md"), help="用于截图的 Markdown 文件")
    parser.add_argument(
        "--out",
        default=str(pathlib.Path.home() / ".cache" / "md-preview" / "gallery"),
        help="输出目录",
    )
    parser.add_argument("--cols", type=int, default=4, help="拼版列数")
    parser.add_argument("--width", type=int, default=900, help="截图视口宽度")
    parser.add_argument("--height", type=int, default=1150, help="截图视口高度")
    parser.add_argument("--themes", nargs="*", help="只截这些主题（默认全部）")
    args = parser.parse_args(argv)

    chromium = cli._find_chromium()
    if chromium is None:
        return int(bool(sys.stderr.write("找不到 Chromium 系浏览器，无法截图\n")))

    out_dir = pathlib.Path(args.out).expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)
    src = pathlib.Path(args.src).expanduser().resolve()
    themes = args.themes or cli.list_themes()
    if not themes:
        return int(bool(sys.stderr.write("没有已安装主题，先跑 md-preview --fetch-themes\n")))

    shots: list[tuple[str, pathlib.Path, str]] = []
    for theme in themes:
        try:
            html_path, _, _ = cli.render_html(src, cli.BASE_CSS, {"theme": theme}, "html")
        except Exception as exc:  # 单个主题失败不影响其它主题
            print(f"跳过 {theme}: {exc}", file=sys.stderr)
            continue
        view = out_dir / f"{theme}.html"
        view.write_text(html_path.read_text(encoding="utf-8"), encoding="utf-8")
        png = out_dir / f"{theme}.png"
        subprocess.run(
            [chromium, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run",
             f"--user-data-dir={out_dir / '.chrome-profile'}", f"--window-size={args.width},{args.height}",
             f"--screenshot={png}", view.as_uri()],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=180,
        )
        if not png.exists():
            print(f"截图失败: {theme}", file=sys.stderr)
            continue
        stat = ImageStat.Stat(Image.open(png).convert("L"))
        kind = "深色" if stat.mean[0] < 128 else "浅色"
        shots.append((theme, png, f"{kind} {stat.mean[0]:.0f}"))
        print(f"shot: {theme:16s} {kind}  平均亮度 {stat.mean[0]:5.1f}")

    if not shots:
        return 1

    cols, tile_w, tile_h, pad, label_h = args.cols, 300, 384, 12, 22
    rows = (len(shots) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * (tile_w + pad) + pad, rows * (tile_h + label_h + pad) + pad), "#e9ecf1")
    draw = ImageDraw.Draw(sheet)
    for i, (theme, png, note) in enumerate(shots):
        thumb = Image.open(png).convert("RGB")
        thumb.thumbnail((tile_w, tile_h))
        x = pad + (i % cols) * (tile_w + pad)
        y = pad + (i // cols) * (tile_h + label_h + pad)
        sheet.paste(thumb, (x, y))
        draw.rectangle([x - 1, y - 1, x + tile_w, y + tile_h], outline="#b6bec9")
        draw.text((x + 4, y + tile_h + 4), f"{theme}  ({note})", fill="#1f2328")

    contact = out_dir / "_contact-sheet.png"
    sheet.save(contact)
    print(f"\n拼版: {contact}  {sheet.size[0]}x{sheet.size[1]}")
    print(f"单图: {out_dir}/<主题>.png")
    return 0


if __name__ == "__main__":
    sys.exit(main())
