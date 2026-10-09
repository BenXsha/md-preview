#!/usr/bin/env python3
"""录一段 README/发帖用的演示动图：把渲染好的预览从上到下滚一遍。

产出（默认写到 demo/）：
    md-preview-demo.gif   默认 15 fps、缩到 800px 宽，Pillow 合成（不需要 ffmpeg）
    md-preview-demo.mp4   H.264，装了 ffmpeg 才有（发 HN/Reddit 用视频更清晰）

用法:
    python3 tools/middle-click-demo.py                      # tests/sample.md + 默认主题
    python3 tools/middle-click-demo.py --src 你的文档.md --theme newsprint
    python3 tools/middle-click-demo.py --caption "中键点 .md → 排版好的 PDF"
    python3 tools/middle-click-demo.py --no-mp4 --gif-width 1000 --fps 20

依赖: websockets + Pillow（pip install websockets Pillow）+ Chromium 系浏览器；MP4 额外需要 ffmpeg。

注意：脚本录的是**预览本身**（滚动效果）。「在 Dolphin 里按鼠标中键」那一下是桌面手势，录不了 ——
用 Spectacle（录屏）或 kooha 单独录 1–2 秒，跟这里的动图拼在一起即可。
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import io
import json
import pathlib
import shutil
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

try:
    from PIL import Image, ImageDraw
except ImportError:  # pragma: no cover
    sys.exit("需要 Pillow: pip install Pillow")

PORT = 9455


class Cdp:
    """极简 CDP 客户端：够用就行（发命令、等回包、给 screencast 帧回 ack）。"""

    def __init__(self, ws) -> None:
        self.ws = ws
        self.seq = 0

    async def call(self, method: str, params: dict | None = None) -> dict:
        self.seq += 1
        mine = self.seq
        await self.ws.send(json.dumps({"id": mine, "method": method, "params": params or {}}))
        while True:
            message = _decode(await self.ws.recv())
            if message is not None and message.get("id") == mine:
                return message.get("result") or {}

    async def ack(self, session_id: int) -> None:
        self.seq += 1
        await self.ws.send(json.dumps({
            "id": self.seq,
            "method": "Page.screencastFrameAck",
            "params": {"sessionId": session_id},
        }))

    async def evaluate(self, expression: str):
        result = await self.call("Runtime.evaluate", {"expression": expression, "returnByValue": True})
        return (result.get("result") or {}).get("value")


def _decode(raw) -> dict | None:
    """CDP 消息偶尔不是 JSON（或收尾时是空帧），解析不了就跳过。"""
    try:
        message = json.loads(raw)
    except (TypeError, ValueError):
        return None
    return message if isinstance(message, dict) else None


def _launch(html_path: pathlib.Path, chromium: str, args: argparse.Namespace) -> tuple[subprocess.Popen, str, str]:
    profile = tempfile.mkdtemp(prefix="md-preview-demo-")
    proc = subprocess.Popen(
        [
            chromium,
            "--headless=new",
            "--disable-gpu",
            "--no-first-run",
            "--hide-scrollbars",
            f"--window-size={args.width},{args.height}",
            f"--user-data-dir={profile}",
            f"--remote-debugging-port={PORT}",
            html_path.as_uri(),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    targets: list[dict] = []
    last_error: Exception | None = None
    for _ in range(80):  # 端口起来要一点时间，轮询到有页面目标为止
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json/list", timeout=1) as response:
                found = json.load(response)
            if isinstance(found, list):
                targets = [t for t in found if isinstance(t, dict)]
            if any(t.get("type") == "page" and t.get("webSocketDebuggerUrl") for t in targets):
                break
        except Exception as exc:
            last_error = exc
        time.sleep(0.25)

    page = next((t for t in targets if t.get("type") == "page" and t.get("webSocketDebuggerUrl")), None)
    if page is None:
        proc.terminate()
        shutil.rmtree(profile, ignore_errors=True)
        raise RuntimeError(f"连不上无头浏览器的调试端口（{last_error or '没有页面目标'}）")
    return proc, str(page["webSocketDebuggerUrl"]), profile


async def record(html_path: pathlib.Path, chromium: str, args: argparse.Namespace) -> list[bytes]:
    proc, url, profile = _launch(html_path, chromium, args)
    frames: list[bytes] = []
    try:
        async with websockets.connect(url, max_size=None) as ws:
            cdp = Cdp(ws)
            await cdp.call("Page.enable")
            await cdp.call("Runtime.enable")
            await asyncio.sleep(1.2)  # 等主题样式表与字体加载完
            height = int(await cdp.evaluate("document.body.scrollHeight") or 0)
            view = int(await cdp.evaluate("window.innerHeight") or 0)
            print(f"   页面高 {height}px / 视口 {view}px")

            await cdp.call("Page.startScreencast", {
                "format": "jpeg",
                "quality": 82,
                "maxWidth": args.width,
                "maxHeight": args.height,
                "everyFrame": True,
            })

            async def pump(seconds: float) -> None:
                """收一段时间内的 screencast 帧（收到就 ack，否则浏览器不再发下一帧）。"""
                deadline = time.monotonic() + seconds
                while True:
                    left = deadline - time.monotonic()
                    if left <= 0:
                        return
                    try:
                        raw = await asyncio.wait_for(ws.recv(), timeout=left)
                    except (asyncio.TimeoutError, TimeoutError):
                        return
                    message = _decode(raw)
                    if message is None or message.get("method") != "Page.screencastFrame":
                        continue
                    params = message.get("params") or {}
                    frames.append(base64.b64decode(params.get("data", "")))
                    await cdp.ack(int(params.get("sessionId", 0)))

            await pump(0.8)  # 开头停一下，让人看清标题
            steps = max(1, args.steps)
            span = max(0, height - view)
            for index in range(steps):
                await cdp.evaluate(f"window.scrollTo(0, {int(span * (index + 1) / steps)})")
                await pump(1 / args.fps)
            await pump(0.5)  # 结尾停一下
            await cdp.call("Page.stopScreencast")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        if profile:
            shutil.rmtree(profile, ignore_errors=True)
    return frames


def add_caption(image: Image.Image, text: str) -> Image.Image:
    """左上角压一条半透明字幕；字号跟着图片宽度走，缩过的 GIF 上也清楚。"""
    if not text:
        return image
    font_size = max(11, round(image.width / 62))
    bar = font_size * 3
    draw = ImageDraw.Draw(image, "RGBA")
    draw.rectangle([0, 0, image.width, bar], fill=(20, 22, 28, 190))
    draw.text((round(font_size * 0.8), font_size), text, fill=(240, 242, 246))
    return image


def _scale(image: Image.Image, width: int) -> Image.Image:
    if not width or width >= image.width:
        return image
    height = round(image.height * width / image.width)
    return image.resize((width, height), Image.Resampling.LANCZOS)


def _dump_frames(images: list[Image.Image], frames_dir: pathlib.Path) -> None:
    for index, image in enumerate(images):
        image.save(frames_dir / f"f{index:04d}.png")


def write_gif(images: list[Image.Image], out: pathlib.Path, args: argparse.Namespace) -> None:
    """优先用 ffmpeg：它做帧间差分、自己生成调色板，同样内容比 Pillow 小好几倍。"""
    with tempfile.TemporaryDirectory(prefix="md-preview-demo-frames-") as tmp:
        frames_dir = pathlib.Path(tmp)
        _dump_frames(images, frames_dir)
        if shutil.which("ffmpeg"):
            filters = (
                f"scale={args.gif_width}:-1:flags=lanczos,split[a][b];"
                f"[a]palettegen=max_colors={args.gif_colors}[p];"
                "[b][p]paletteuse=dither=none"
            )
            command = [
                "ffmpeg", "-y", "-loglevel", "error",
                "-framerate", str(args.fps), "-i", str(frames_dir / "f%04d.png"),
                "-vf", filters, "-loop", "0", str(out),
            ]
            if subprocess.run(command).returncode == 0 and out.exists():
                print(f"   GIF  {out}  {len(images)} 帧 / {args.gif_width}px 宽 / {out.stat().st_size / 1024:.0f} KB（ffmpeg）")
                return
            print("   GIF  ffmpeg 合成失败，改用 Pillow 兜底", file=sys.stderr)

    # 没装 ffmpeg 时的兜底：体积大一些，但一条命令就能出图
    scaled = [im.convert("P", palette=Image.Palette.ADAPTIVE, colors=args.gif_colors) for im in images]
    scaled[0].save(
        out,
        save_all=True,
        append_images=scaled[1:],
        duration=int(1000 / args.fps),
        loop=0,
        optimize=True,
    )
    print(f"   GIF  {out}  {len(scaled)} 帧 / {scaled[0].width}×{scaled[0].height} / {out.stat().st_size / 1024:.0f} KB（Pillow）")


def write_mp4(images: list[Image.Image], out: pathlib.Path, args: argparse.Namespace) -> None:
    with tempfile.TemporaryDirectory(prefix="md-preview-demo-frames-") as tmp:
        frames_dir = pathlib.Path(tmp)
        _dump_frames(images, frames_dir)
        command = [
            "ffmpeg", "-y", "-loglevel", "error",
            "-framerate", str(args.fps),
            "-i", str(frames_dir / "f%04d.png"),
            "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", "-movflags", "+faststart",
            str(out),
        ]
        if subprocess.run(command).returncode == 0:
            print(f"   MP4  {out}  {out.stat().st_size / 1024:.0f} KB")
        else:
            print("   MP4  合成失败（ffmpeg 返回非 0）", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--src", default=str(REPO / "tests" / "sample.md"), help="要预览的 Markdown")
    parser.add_argument("--theme", default="default", help="主题名（默认 default；--list-themes 看全部）")
    parser.add_argument("--outdir", default=str(REPO / "demo"), help="产物目录")
    parser.add_argument("--width", type=int, default=1100, help="视口宽（默认 1100）")
    parser.add_argument("--height", type=int, default=760, help="视口高（默认 760）")
    parser.add_argument("--steps", type=int, default=28, help="滚动步数（默认 28；越小越省体积、也越跳）")
    parser.add_argument("--fps", type=int, default=12, help="帧率（默认 12，GIF 别调太高）")
    parser.add_argument("--gif-width", type=int, default=720, help="GIF 缩放宽度（默认 720）")
    parser.add_argument("--gif-colors", type=int, default=72, help="GIF 调色板颜色数（默认 72，越小越省体积）")
    parser.add_argument("--caption", default="", help="左上角字幕（留空则不加）")
    parser.add_argument("--no-mp4", action="store_true", help="不生成 mp4")
    args = parser.parse_args(argv)

    chromium = cli._find_chromium()
    if chromium is None:
        sys.stderr.write("找不到 Chromium 系浏览器\n")
        return 1
    src = pathlib.Path(args.src).expanduser().resolve()
    if not src.is_file():
        sys.stderr.write(f"找不到 {src}\n")
        return 1

    outdir = pathlib.Path(args.outdir).expanduser()
    outdir.mkdir(parents=True, exist_ok=True)
    html_path, _, meta = cli.render_html(src, cli.BASE_CSS, {"theme": args.theme}, "html")
    print(f"== {src.name} 主题={meta['theme']} 浏览器={pathlib.Path(chromium).name}")
    print(f"   预览 HTML: {html_path}")

    frames = asyncio.run(record(html_path, chromium, args))
    if len(frames) < 5:
        sys.stderr.write(f"只抓到 {len(frames)} 帧，放弃（试试调大 --steps 或 --fps）\n")
        return 1
    print(f"   抓到 {len(frames)} 帧")

    raw = [Image.open(io.BytesIO(frame)).convert("RGB") for frame in frames]
    gif_frames = [add_caption(_scale(image, args.gif_width), args.caption) for image in raw]
    write_gif(gif_frames, outdir / "md-preview-demo.gif", args)
    if not args.no_mp4 and shutil.which("ffmpeg"):
        write_mp4([add_caption(image, args.caption) for image in raw], outdir / "md-preview-demo.mp4", args)
    print("   提示：Dolphin 里按中键那一下录不到，用 Spectacle 单独录 1–2 秒再拼上")
    return 0


if __name__ == "__main__":
    sys.exit(main())
