#!/usr/bin/env bash
# 卸载 md-preview 的用户级安装：还原 mimeapps.list、删掉 desktop 项与脚本。
# 默认保留主题、配置与缓存（--purge 才删）。
set -euo pipefail

REPO_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
BIN_DIR="${XDG_BIN_HOME:-$HOME/.local/bin}"
DATA_DIR="${XDG_DATA_HOME:-$HOME/.local/share}"
CONF_HOME="${XDG_CONFIG_HOME:-$HOME/.config}"
APP_DIR="$DATA_DIR/applications"
CONF_DIR="$CONF_HOME/md-preview"
MIMEAPPS="$CONF_HOME/mimeapps.list"
MIMES=(text/markdown text/x-markdown)
PURGE=0

usage() {
    cat <<EOF
用法: contrib/uninstall.sh [选项]

  --purge   连带删除 $CONF_DIR 与 \${XDG_CACHE_HOME:-\$HOME/.cache}/md-preview
  -h, --help
EOF
}

while [ $# -gt 0 ]; do
    case "$1" in
        --purge) PURGE=1 ;;
        -h|--help) usage; exit 0 ;;
        *) echo "未知参数: $1" >&2; usage >&2; exit 2 ;;
    esac
    shift
done

echo "== 还原文件关联 =="
for mime in "${MIMES[@]}"; do
    python3 "$REPO_DIR/contrib/merge-mimeapps.py" --file "$MIMEAPPS" --mime "$mime" --restore
done
if command -v kbuildsycoca6 >/dev/null 2>&1; then
    kbuildsycoca6 --noincremental >/dev/null 2>&1 || true
    echo "   已刷新 KDE 服务缓存 (kbuildsycoca6)"
fi

echo "== 删除 desktop 项与脚本 =="
for name in md-preview.desktop md-preview-browser.desktop; do
    if [ -f "$APP_DIR/$name" ]; then
        rm -f "$APP_DIR/$name"
        echo "   rm $APP_DIR/$name"
    fi
done
if [ -f "$BIN_DIR/md-preview" ]; then
    rm -f "$BIN_DIR/md-preview"
    echo "   rm $BIN_DIR/md-preview"
fi
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$APP_DIR" >/dev/null 2>&1 || true
fi

if [ "$PURGE" = 1 ]; then
    echo "== 清除配置与缓存 =="
    rm -rf "$CONF_DIR" "${XDG_CACHE_HOME:-$HOME/.cache}/md-preview"
    echo "   已删除 $CONF_DIR 与 \${XDG_CACHE_HOME:-\$HOME/.cache}/md-preview"
else
    echo "（主题/配置/缓存保留；要一起删就加 --purge）"
fi

echo "卸载完成。"
