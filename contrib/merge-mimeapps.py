#!/usr/bin/env python3
"""安全地改写 ~/.config/mimeapps.list 里某个 MIME 的处理顺序（可还原）。

为什么要它：Dolphin 的鼠标中键 = 「该 MIME 类型应用列表的第 2 个应用」
（KDE Dolphin 源码 src/dolphinviewcontainer.cpp 的 slotfileMiddleClickActivated），
顺序由 ~/.config/mimeapps.list 决定，所以要精确控制就得按顺序写进去。
脚本只动指定 MIME 的那两行，其余内容逐字节保留，并在首次修改时做一份备份。

用法:
  merge-mimeapps.py --mime text/markdown --default org.kde.kate.desktop \
                    --order "md-preview.desktop;md-preview-browser.desktop;okularApplication_md.desktop"
  merge-mimeapps.py --mime text/markdown --restore
"""

from __future__ import annotations

import argparse
import pathlib
import shutil
import sys

BACKUP_SUFFIX = ".bak-md-preview"
DEFAULT_SECTION = "Default Applications"
ADDED_SECTION = "Added Associations"


def read_lines(path: pathlib.Path) -> list[str]:
    if not path.exists():
        return []
    return path.read_text(encoding="utf-8").splitlines()


def section_range(lines: list[str], section: str) -> tuple[int, int] | None:
    """返回 [start, end) —— 该 section 内可写行的范围（不含标题行）。"""
    header = f"[{section}]"
    start = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped == header:
            start = i + 1
            continue
        if start is not None and stripped.startswith("[") and stripped.endswith("]"):
            return start, i
    if start is None:
        return None
    return start, len(lines)


def set_key(lines: list[str], section: str, key: str, value: str) -> list[str]:
    """在 section 中设置 key=value：有则改，无则加，section 不存在则创建到文件末尾。"""
    prefix = f"{key}="
    span = section_range(lines, section)
    if span is None:
        if lines and lines[-1].strip():
            lines.append("")
        lines.append(f"[{section}]")
        lines.append(prefix + value)
        return lines

    start, end = span
    for i in range(start, end):
        if lines[i].startswith(prefix):
            lines[i] = prefix + value
            return lines
    insert_at = end
    while insert_at > start and not lines[insert_at - 1].strip():
        insert_at -= 1  # 插在 section 内容末尾，别落到下一节前面
    lines.insert(insert_at, prefix + value)
    return lines


def remove_key(lines: list[str], section: str, key: str) -> list[str]:
    span = section_range(lines, section)
    if span is None:
        return lines
    start, end = span
    return [line for i, line in enumerate(lines) if not (start <= i < end and line.startswith(f"{key}="))]


def merge(path: pathlib.Path, mime: str, default_app: str | None, order: str | None) -> None:
    backup = path.with_name(path.name + BACKUP_SUFFIX)
    if path.exists() and not backup.exists():
        shutil.copy2(path, backup)
        print(f"已备份: {backup}")

    lines = read_lines(path)
    if default_app:
        lines = set_key(lines, DEFAULT_SECTION, mime, default_app)
    if order:
        lines = set_key(lines, ADDED_SECTION, mime, order)

    path.parent.mkdir(parents=True, exist_ok=True)
    text = "\n".join(lines).rstrip("\n") + "\n"
    path.write_text(text, encoding="utf-8")
    print(f"已更新: {path}")


def restore(path: pathlib.Path, mime: str) -> None:
    backup = path.with_name(path.name + BACKUP_SUFFIX)
    if backup.exists():
        shutil.copy2(backup, path)
        backup.unlink()
        print(f"已从备份还原 {path}（备份已删除）")
        return
    lines = read_lines(path)
    lines = remove_key(lines, DEFAULT_SECTION, mime)
    lines = remove_key(lines, ADDED_SECTION, mime)
    if path.exists():
        path.write_text("\n".join(lines).rstrip("\n") + "\n", encoding="utf-8")
    print(f"没有备份，已移除 {mime} 的相关条目: {path}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--file", default="~/.config/mimeapps.list", help="mimeapps.list 路径")
    parser.add_argument("--mime", required=True, help="MIME 类型，如 text/markdown")
    parser.add_argument("--default", dest="default_app", help=f"{DEFAULT_SECTION} 里写的默认应用（省略则不改）")
    parser.add_argument("--order", help=f"{ADDED_SECTION} 里按顺序写的分号列表（省略则不改）")
    parser.add_argument("--restore", action="store_true", help="从备份还原（没有备份则移除相关条目）")
    args = parser.parse_args(argv)

    path = pathlib.Path(args.file).expanduser()
    if args.restore:
        restore(path, args.mime)
    else:
        merge(path, args.mime, args.default_app, args.order)
    return 0


if __name__ == "__main__":
    sys.exit(main())
