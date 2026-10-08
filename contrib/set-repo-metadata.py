#!/usr/bin/env python3
"""把仓库的「元数据 / Release / 调试分支」一次处理好（需要一个临时 GitHub token）。

这三件事都得走 GitHub API（git push 做不到）：

1. 仓库简介与话题（About 区）
2. 为 CHANGELOG 里列出的版本创建 Release（说明直接取自 CHANGELOG 对应章节）
3. 删除调试分支 `ci-logs`（若存在）

用法::

    python3 contrib/set-repo-metadata.py --dry-run          # 不需要 token，只打印将要发送的内容
    GITHUB_TOKEN=ghp_xxx python3 contrib/set-repo-metadata.py                # 全做
    GITHUB_TOKEN=ghp_xxx python3 contrib/set-repo-metadata.py --metadata      # 只改简介与话题
    GITHUB_TOKEN=ghp_xxx python3 contrib/set-repo-metadata.py --releases      # 只建 Release
    GITHUB_TOKEN=ghp_xxx python3 contrib/set-repo-metadata.py --delete-branch ci-logs

Token 权限：classic token 勾 `repo` 即可；fine-grained token 需要
"Administration: Read and write"（改简介/话题）与 "Contents: Read and write"（建 Release / 删分支）。
**用完请立刻到 https://github.com/settings/tokens 撤销**，不要把它写进任何文件。
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import sys
import urllib.error
import urllib.request

REPO = os.environ.get("MD_PREVIEW_REPO", "BenXsha/md-preview")
DESCRIPTION = (
    "Render Markdown into styled PDF/HTML with plain-CSS themes — "
    "one middle-click preview in KDE Dolphin"
)
TOPICS = [
    "kde",
    "kde-plasma",
    "markdown",
    "markdown-preview",
    "dolphin",
    "okular",
    "css-themes",
    "pdf",
    "python",
    "cli",
]
CHANGELOG = pathlib.Path(__file__).resolve().parent.parent / "CHANGELOG.md"
API = "https://api.github.com"
SECTION_RE = re.compile(r"^##\s*\[?([0-9]+\.[0-9]+\.[0-9]+)\]?.*$", re.M)


def release_notes(version: str) -> str | None:
    """从 CHANGELOG 里取出某个版本的章节（含它下面的所有小节）。"""
    text = CHANGELOG.read_text(encoding="utf-8")
    matches = list(SECTION_RE.finditer(text))
    for index, match in enumerate(matches):
        if match.group(1) != version:
            continue
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = text[match.start() : end].strip()
        return body
    return None


def versions() -> list[str]:
    return [match.group(1) for match in SECTION_RE.finditer(CHANGELOG.read_text(encoding="utf-8"))]


def call(method: str, path: str, token: str, payload: dict | None = None) -> tuple[int, str]:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(f"{API}{path}", data=data, method=method)
    request.add_header("Authorization", f"Bearer {token}")
    request.add_header("Accept", "application/vnd.github+json")
    request.add_header("X-GitHub-Api-Version", "2022-11-28")
    request.add_header("User-Agent", "md-preview-release-helper")
    if data is not None:
        request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status, response.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", "replace")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo", default=REPO, help=f"owner/name（默认 {REPO}）")
    parser.add_argument("--dry-run", action="store_true", help="只打印将要发送的内容，不联网")
    parser.add_argument("--metadata", action="store_true", help="改简介与话题")
    parser.add_argument("--releases", action="store_true", help="按 CHANGELOG 建 Release")
    parser.add_argument("--delete-branch", metavar="NAME", help="删除指定分支（如 ci-logs）")
    args = parser.parse_args(argv)

    do_metadata = args.metadata or not (args.releases or args.delete_branch)
    do_releases = args.releases or not (args.metadata or args.delete_branch)
    wanted = versions()

    if args.dry_run:
        print(f"仓库        : {args.repo}")
        if do_metadata:
            print(f"简介        : {DESCRIPTION}")
            print(f"话题        : {', '.join(TOPICS)}")
        if do_releases:
            print(f"Release 标签: {', '.join('v' + v for v in wanted)}")
            for version in wanted:
                body = release_notes(version) or ""
                first = next((line for line in body.splitlines() if line.strip() and not line.startswith("#")), "")
                print(f"  v{version}: {first[:90]}")
        if args.delete_branch:
            print(f"删除分支    : {args.delete_branch}")
        print("\n（--dry-run 没有联网；去掉它并设置 GITHUB_TOKEN 即真正执行）")
        return 0

    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if not token:
        print("缺少 GITHUB_TOKEN 环境变量；先跑 --dry-run 看看会做什么，", file=sys.stderr)
        print("或在浏览器里手动设置：Settings → About（简介/话题）与 Releases 页。", file=sys.stderr)
        return 2

    ok = True
    if do_metadata:
        status, body = call("PATCH", f"/repos/{args.repo}", token, {"description": DESCRIPTION})
        print(f"简介  : {'✓' if status == 200 else '✗'} HTTP {status} {body[:160] if status != 200 else ''}")
        ok &= status == 200
        status, body = call("PUT", f"/repos/{args.repo}/topics", token, {"names": TOPICS})
        print(f"话题  : {'✓' if status == 200 else '✗'} HTTP {status} {body[:160] if status != 200 else ''}")
        ok &= status == 200

    if do_releases:
        for version in wanted:
            tag = f"v{version}"
            status, _ = call("GET", f"/repos/{args.repo}/releases/tags/{tag}", token)
            if status == 200:
                print(f"Release {tag}: 已存在，跳过")
                continue
            body = release_notes(version) or f"md-preview {version}"
            status, text = call(
                "POST",
                f"/repos/{args.repo}/releases",
                token,
                {"tag_name": tag, "name": tag, "body": body, "draft": False, "prerelease": False},
            )
            print(f"Release {tag}: {'✓' if status == 201 else '✗'} HTTP {status} {text[:160] if status != 201 else ''}")
            ok &= status == 201

    if args.delete_branch:
        status, text = call("DELETE", f"/repos/{args.repo}/git/refs/heads/{args.delete_branch}", token)
        # 404/422 表示本来就不存在，也算处理完成
        fine = status in (204, 404, 422)
        print(f"删除分支 {args.delete_branch}: {'✓' if fine else '✗'} HTTP {status} {text[:160] if not fine else ''}")
        ok &= fine

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
