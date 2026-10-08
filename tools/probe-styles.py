#!/usr/bin/env python3
"""用 DevTools Protocol 读无头浏览器里的计算样式，验证主题是否真的命中 DOM。

「看起来变了」不等于「主题生效了」——比如把 cm-s-inner 加到 <pre> 上时，代码块底色会被
主题里 `.cm-s-inner.CodeMirror { background: none }` 抹掉，肉眼初看很容易漏掉。
这个脚本把关键属性的真实取值打出来（`#write` 宽度、`pre` 底色、token 颜色、body 类名…）。

用法:
    python3 tools/probe-styles.py github drake-jb night
    python3 tools/probe-styles.py --src 文档.md --json out.json

依赖: websockets（pip install websockets）+ Chromium 系浏览器
"""

from __future__ import annotations

import argparse
import asyncio
import json
import pathlib
import subprocess
import sys
import tempfile
import time
import urllib.request

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

import md_preview.cli as cli  # noqa: E402

try:
    import websockets
except ImportError:  # pragma: no cover
    sys.exit("需要 websockets: pip install websockets")

PORT = 9333

JS = r"""
(() => {
  const cs = (sel, prop) => { const el = document.querySelector(sel); return el ? getComputedStyle(el)[prop] : null; };
  const size = (sel) => { const el = document.querySelector(sel); if (!el) return null;
    const r = el.getBoundingClientRect(); return [Math.round(r.width), Math.round(r.height)]; };
  return {
    ready: document.readyState,
    bodyClass: document.body.className,
    sheets: [...document.styleSheets].map(s => s.href ? decodeURIComponent(s.href.split('/').pop()) : 'inline'),
    bodyBg: cs('body', 'backgroundColor'),
    write: [cs('#write', 'backgroundColor'), cs('#write', 'maxWidth'), cs('#write', 'padding')],
    h1: [cs('#write h1', 'fontSize'), cs('#write h1', 'borderBottomWidth'), cs('#write h1', 'color')],
    p: [cs('#write p', 'fontSize'), cs('#write p', 'lineHeight'), cs('#write p', 'color')],
    pre: [cs('pre.md-fences', 'backgroundColor'), cs('pre.md-fences', 'fontSize'), cs('pre.md-fences', 'padding')],
    tok: [cs('pre.md-fences .cm-keyword', 'color'), cs('pre.md-fences .cm-string', 'color'), cs('pre.md-fences .cm-comment', 'color')],
    th: [cs('#write th', 'backgroundColor'), cs('#write th', 'color')],
    bq: [cs('#write blockquote', 'borderLeftColor'), cs('#write blockquote', 'backgroundColor')],
    fenceStructure: !!document.querySelector('pre.md-fences > .CodeMirror.cm-s-inner > code'),
    inlineCodeBg: cs('#write p code', 'backgroundColor'),
    tableSize: size('#write table'),
    fonts: document.fonts ? document.fonts.status : null,
  };
})()
"""


async def probe(html_path: pathlib.Path, chromium: str, wait: float) -> dict:
    profile = tempfile.mkdtemp(prefix="md-preview-cdp-")
    proc = subprocess.Popen(
        [chromium, "--headless=new", "--disable-gpu", "--no-first-run",
         f"--user-data-dir={profile}", f"--remote-debugging-port={PORT}", html_path.as_uri()],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        targets = None
        for _ in range(80):
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json/list", timeout=1) as response:
                    targets = json.load(response)
                if any(t["type"] == "page" and t.get("webSocketDebuggerUrl") for t in targets):
                    break
            except Exception:
                pass
            time.sleep(0.25)
        page = next(t for t in targets if t["type"] == "page" and t.get("webSocketDebuggerUrl"))
        async with websockets.connect(page["webSocketDebuggerUrl"], max_size=None) as ws:
            await asyncio.sleep(wait)  # 等样式表与字体加载完
            await ws.send(json.dumps({"id": 1, "method": "Runtime.evaluate",
                                      "params": {"expression": JS, "returnByValue": True}}))
            while True:
                message = json.loads(await ws.recv())
                if message.get("id") == 1:
                    return message["result"]["result"].get("value") or {"error": message}
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


async def run(args: argparse.Namespace) -> int:
    chromium = cli._find_chromium()
    if chromium is None:
        return int(bool(sys.stderr.write("找不到 Chromium 系浏览器\n")))
    src = pathlib.Path(args.src).expanduser().resolve()
    themes = args.themes or cli.list_themes()[:4]

    results: dict[str, dict] = {}
    for theme in themes:
        html_path, _, _ = cli.render_html(src, cli.BASE_CSS, {"theme": theme}, "html")
        data = await probe(html_path, chromium, args.wait)
        results[theme] = data
        print(f"== {theme}  bodyClass={data.get('bodyClass')!r}  结构={data.get('fenceStructure')}")
        print(f"   bodyBg {data.get('bodyBg')} | #write {data.get('write')}")
        print(f"   h1 {data.get('h1')} | p {data.get('p')}")
        print(f"   pre {data.get('pre')} | 行内 code {data.get('inlineCodeBg')}")
        print(f"   tokens {data.get('tok')}")
        print(f"   sheets {data.get('sheets')} | fonts {data.get('fonts')}")

    if args.json:
        pathlib.Path(args.json).write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"\n已写入 {args.json}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("themes", nargs="*", help="要检查的主题（默认前 4 个）")
    parser.add_argument("--src", default=str(REPO / "tests" / "sample.md"), help="用于渲染的 Markdown 文件")
    parser.add_argument("--json", help="把结果写到 JSON 文件")
    parser.add_argument("--wait", type=float, default=1.2, help="页面加载后等待秒数（默认 1.2）")
    args = parser.parse_args(argv)
    return asyncio.run(run(args))


if __name__ == "__main__":
    sys.exit(main())
