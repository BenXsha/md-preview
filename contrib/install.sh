#!/usr/bin/env bash
# md-preview 用户级安装：脚本 + 兜底样式 + 主题 + desktop 项 + Dolphin 中键顺序。
# 全部落在 ~/.local / ~/.config / ~/.cache，不需要 sudo。
set -euo pipefail

REPO_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
BIN_DIR="${XDG_BIN_HOME:-$HOME/.local/bin}"
DATA_DIR="${XDG_DATA_HOME:-$HOME/.local/share}"
CONF_HOME="${XDG_CONFIG_HOME:-$HOME/.config}"
APP_DIR="$DATA_DIR/applications"
SERVICE_DIR="$DATA_DIR/kio/servicemenus"
CONF_DIR="$CONF_HOME/md-preview"
MIMEAPPS="$CONF_HOME/mimeapps.list"
MIMES=(text/markdown text/x-markdown)
THEME_SETS=""   # 默认不联网：自带 default / default-dark 即可用；需要更多风格时用 --fetch 指定
DO_THEMES=1
DO_ASSOC=1

usage() {
    cat <<EOF
用法: contrib/install.sh [选项]

  --skip-themes              不下载主题（之后可手动跑 md-preview --fetch-themes）
  --skip-associations        不改 mimeapps.list（即不接管 Dolphin 中键预览）
  --fetch "drake mdmdt"       可选：额外拉取带明确开源许可的社区主题集（默认不联网）
  -h, --help                 显示本帮助

会写入:
  \$BIN_DIR/md-preview                                  (单文件脚本)
  \$CONF_DIR/config, \$CONF_DIR/style.css                (配置与兜底样式)
  \$APP_DIR/md-preview.desktop, md-preview-browser.desktop
  \$SERVICE_DIR/md-preview-servicemenu.desktop           (Dolphin 右键服务菜单)
  \$MIMEAPPS 里 text/markdown 与 text/x-markdown 的顺序   (首次修改前备份为 *.bak-md-preview)

中键顺序会排成: 双击=原编辑器 → 中键=md-preview(PDF) → Shift+中键=浏览器预览 → 其后=原 Okular
EOF
}

while [ $# -gt 0 ]; do
    case "$1" in
        --skip-themes) DO_THEMES=0 ;;
        --skip-associations) DO_ASSOC=0 ;;
        --fetch) shift; THEME_SETS="${1:-}" ;;
        -h|--help) usage; exit 0 ;;
        *) echo "未知参数: $1" >&2; usage >&2; exit 2 ;;
    esac
    shift
done

echo "== 1/5 安装脚本 =="
install -Dm755 "$REPO_DIR/src/md_preview/cli.py" "$BIN_DIR/md-preview"
echo "   $BIN_DIR/md-preview"

echo "== 2/5 配置与兜底样式 =="
mkdir -p "$CONF_DIR/themes"
if [ -f "$CONF_DIR/style.css" ]; then
    echo "   保留已有 $CONF_DIR/style.css"
else
    install -Dm644 "$REPO_DIR/src/md_preview/fallback.css" "$CONF_DIR/style.css"
    echo "   写入 $CONF_DIR/style.css"
fi
if [ -f "$CONF_DIR/config" ]; then
    echo "   保留已有 $CONF_DIR/config"
else
    cat > "$CONF_DIR/config" <<'EOF'
# md-preview 配置（改完下次预览自动生效）
#
# theme      : 默认主题。自带 default（浅色）与 default-dark（深色），无需联网；
#              --list-themes 看所有可用主题，把任意 .css 丢进
#              ~/.config/md-preview/themes/ 也能用（主题许可请自行确认）。
#              可选：md-preview --fetch-themes drake mdmdt 拉取 MIT/Apache-2.0 社区主题集。
# dark_theme : 浏览器预览时，系统切到深色模式则替换成这个（留空 = 不换）
# pdf_theme  : PDF 模式专用主题（留空 = 同 theme）。想让 Okular 里也走深色就填 default-dark
theme      = default
dark_theme = default-dark
pdf_theme  =
EOF
    echo "   写入 $CONF_DIR/config"
fi

if ! python3 -c 'import markdown_it, pygments' >/dev/null 2>&1; then
    echo "!! 缺少 Python 依赖，请先安装: pipx install markdown-it-py pygments  (或系统包 python3-markdown-it python3-pygments)" >&2
fi

echo "== 3/5 主题 =="
if [ "$DO_THEMES" = 1 ]; then
    "$BIN_DIR/md-preview" --fetch-themes $THEME_SETS || echo "   主题下载失败（不影响使用，可稍后重试）"
else
    echo "   跳过（--skip-themes）"
fi

echo "== 4/5 desktop 项与服务菜单 =="
mkdir -p "$APP_DIR" "$SERVICE_DIR"
python3 - "$REPO_DIR" "$BIN_DIR/md-preview" "$APP_DIR" "$SERVICE_DIR" <<'PY'
import pathlib, sys

repo, exec_path, app_dir, service_dir = (pathlib.Path(v) for v in sys.argv[1:5])
targets = [
    ("md-preview.desktop", app_dir),                      # 「打开方式」里的 PDF 预览
    ("md-preview-browser.desktop", app_dir),               # 「打开方式」里的浏览器预览
    ("md-preview-servicemenu.desktop", service_dir),       # Dolphin 右键服务菜单
]
for name, dest in targets:
    text = (repo / "contrib" / f"{name}.in").read_text(encoding="utf-8").replace("@BIN@", str(exec_path))
    (dest / name).write_text(text, encoding="utf-8")
    print("   ", dest / name)
PY

echo "== 5/5 文件关联顺序 =="
if [ "$DO_ASSOC" = 1 ]; then
    DEFAULT_APP=""
    if command -v xdg-mime >/dev/null 2>&1; then
        DEFAULT_APP="$(xdg-mime query default text/markdown 2>/dev/null || true)"
    fi
    case "$DEFAULT_APP" in
        md-preview*.desktop) DEFAULT_APP="" ;;   # 重装时不要把预览器当默认编辑器
    esac
    if [ -z "$DEFAULT_APP" ] && [ -f /usr/share/applications/org.kde.kate.desktop ]; then
        DEFAULT_APP="org.kde.kate.desktop"
    fi
    ORDER="md-preview.desktop;md-preview-browser.desktop"
    [ -f /usr/share/applications/okularApplication_md.desktop ] && ORDER="$ORDER;okularApplication_md.desktop"

    for mime in "${MIMES[@]}"; do
        args=(--file "$MIMEAPPS" --mime "$mime" --order "$ORDER")
        [ -n "$DEFAULT_APP" ] && args+=(--default "$DEFAULT_APP")
        python3 "$REPO_DIR/contrib/merge-mimeapps.py" "${args[@]}"
    done
    if command -v kbuildsycoca6 >/dev/null 2>&1; then
        kbuildsycoca6 --noincremental >/dev/null 2>&1 || true
        echo "   已刷新 KDE 服务缓存 (kbuildsycoca6)"
    fi
    if command -v update-desktop-database >/dev/null 2>&1; then
        update-desktop-database "$APP_DIR" >/dev/null 2>&1 || true
    fi
else
    echo "   跳过（--skip-associations）"
fi

cat <<EOF

完成 ✅

现在可以直接用:
  md-preview --list-themes            列出主题
  md-preview --theme default-dark 文档.md  生成带样式的 PDF 并用 Okular 打开
  md-preview --html 文档.md            用浏览器预览

在 Dolphin 里对任意 .md 按【鼠标中键】即可看到效果；Shift+中键 = 浏览器预览。
不满意就 ./contrib/uninstall.sh 一键还原。
EOF
