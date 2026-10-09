# AUR 打包（md-preview）

`PKGBUILD` 把 md-preview 装成系统包：`/usr/bin/md-preview`、包内自带主题，外加两个 desktop 项
（PDF / 浏览器）与 Dolphin 右键服务菜单。运行时依赖 `python-markdown-it` + `python-pygments`，
PDF 输出需要 Chromium 系浏览器（写在 `optdepends`）。

## 状态：⚠️ 未经本机实测

作者本机是 Ubuntu，没有 `makepkg`，所以这份 PKGBUILD **只做过静态检查**（`bash -n`、
desktop 模板替换与 `desktop-file-validate`、`python -m build` + `python -m installer` 的等价流程
在本地用 wheel 走通过）。首次提交 AUR 前请在有 Arch 的环境里过一遍：

```console
$ updpkgsums                         # 把 sha256sums 的 SKIP 换成真实值
$ makepkg -si                        # 真装一遍
$ md-preview --version && md-preview --list-themes    # 命令与自带主题（default / default-dark）
$ namcap PKGBUILD *.pkg.tar.zst      # 静态检查
$ makepkg --printsrcinfo > .SRCINFO  # AUR 要求的元数据
```

## 发布到 AUR

AUR 是 **git 仓库**，推上去即发布（不能用网页上传）：

```console
# 1. 一次性：把 SSH 公钥贴到 https://aur.archlinux.org/account 的 My Account → SSH Public Key
$ ssh -T aur@aur.archlinux.org            # 应回答 "Welcome to AUR"，并提示仓库还不存在

# 2. 建包并推送（包名 md-preview 目前未被占用）
$ git clone ssh://aur@aur.archlinux.org/md-preview.git ~/aur-md-preview
$ cp contrib/aur/PKGBUILD ~/aur-md-preview/ && cd ~/aur-md-preview
$ updpkgsums && makepkg --printsrcinfo > .SRCINFO
$ git add PKGBUILD .SRCINFO && git commit -m "md-preview 0.4.0" && git push
```

之后每次发版：改 `pkgver`/`pkgrel` → `updpkgsums` → 重新生成 `.SRCINFO` → push。

## 装完还要做一步：排中键槽位

Dolphin 的鼠标中键 = 该 MIME 应用列表里的**第 2 个应用**，顺序在 `~/.config/mimeapps.list` 里定。
系统包装好之后，用户侧这样排（详见 `docs/kde-dolphin-middle-click.md`）：

```ini
[Default Applications]
text/markdown=org.kde.kate.desktop;          # 第 0 位：双击/回车 = 编辑器

[Added Associations]
text/markdown=md-preview.desktop;md-preview-browser.desktop;okularApplication_md.desktop;
#             ↑ 中键            ↑ Shift+中键                  ↑ 其后 = 原来的 Okular
```

## 可选：`-git` 变体

想跟 main 分支可以用 `md-preview-git`（AUR 上同样没被占用）：`source=("git+$url.git")`、
`pkgver()` 用 `git describe --long --tags | sed 's/^v//;s/-/./;s/\.r/.r/'`，其余与本体相同。
不提供它是为了让默认包保持在「打过标签的版本」上。
