# 对外分享计划（维护者自用）

先分享**知识**，再分享**工具**。理由：两个 Okular wish 已经开了 4–6 年、评论寥寥；「Dolphin 中键 = 第二个
MIME 应用」这件事几乎没人知道（连带着 `mimeapps.list` 的排序规则）。把机制讲清楚，比贴一个工具链接更容易
被接受，也不会被当成推广。工具在同一条推文/帖子里作为附注出现即可。

## 发布前必须先满足（硬门槛）

| # | 事项 | 状态 |
|---|---|---|
| 1 | 装得上：`pipx install md-preview-kde`（PyPI 名）或 `pipx install git+https://github.com/BenXsha/md-preview`；AUR 包 | ✅ 发行名/打包数据已就绪；⚠️ 尚未在 PyPI / AUR 真正发布 |
| 2 | 3–5 秒演示动图（中键点 `.md` → 排版好的 PDF） | 工具：`python3 tools/middle-click-demo.py`（见 `tools/`）；「中键那一下」需要自己录屏 |
| 3 | README 首页三行内说清「它是什么 / 不是什么」 | ✅ 已有 Features + Known limitations |
| 4 | 许可与署名自查 | ✅ `THIRD-PARTY.md`；主题均为 MIT / Apache-2.0 |

## 顺序与渠道

| 阶段 | 渠道 | 主体 | 提醒 |
|---|---|---|---|
| ① | okular#400529、#426682 各留一条评论 | **机制 + 绕法** | 措辞：这是过渡方案，不是修复；明确「第三方、与 KDE 无隶属」。两条不要同一天发，第二条交叉引用第一条 |
| ① | discuss.kde.org（Tips & Tricks / Brainstorm） | **机制长文** | 帖子标题别写「我的工具」，写「中键槽位是怎么选应用的」 |
| ② | r/kde（英文）、r/linux | 工具 + 动图 | 先发 r/kde，观察半天再决定要不要发 r/linux |
| ② | Show HN | 「未文档化的桌面行为 + 一个补槽位的工具」 | HN 对 Linux 桌面小工具冷淡，卖点是机制与那两个 wish，不是功能清单 |
| ② | Linux.do、V2EX、小众软件 | 踩坑记录 + 工具 | 比英文社区晚 1–2 周，语气偏「我在用的小工具」 |
| ③ | AUR（`md-preview`）、可选 `-git` | 打包 | 见 `contrib/aur/README.md`，注意「未经 makepkg 实测」的说明要先摘掉 |
| ✗ | 求 KDE 上游收录 | — | 不是 KDE 应用、不依赖 KDE 框架，进不了 KDE 仓库；正确定位是第三方小工具 |

## 常见质疑与回答（提前写好，回帖时别现想）

- **「为什么不直接用 Obsidian / marktext / VS Code / ghostwriter？」** —— 那些都是「打开一个应用再找文件」；
  这里改的是 Dolphin 里对文件按中键的那一下，预览完就回到文件管理器，不换任何默认应用、双击仍然是 Kate。
- **「为什么不给 Okular 写插件 / 提交补丁？」** —— Markdown 后端把纸面底色与文字颜色写死了
  （`image.fill(Qt::white)`、`QPalette::Text`），而且第三方 generator 没有 ABI 承诺、每次 Okular 升级都要重编，
  还要受 QTextDocument 的 CSS 子集限制。真正的修复在 Okular 侧（那两个 wish），本工具是在那之前把槽位让给
  一个完整的 CSS 引擎。
- **「为什么要装 Chromium？」** —— PDF 由无头 Chromium 生成（复用系统已有的 Edge/Chrome/Chromium/Brave）；
  没有时自动退回浏览器预览，不会失败。
- **「为什么发行名带 kde？」** —— PyPI 的 `md-preview` 已被别的项目占用；命令名仍是 `md-preview`。
- **「装完没生效？」** —— 见 README「升级」小节：安装位是 `cli.py` 的拷贝，`git pull` 后要重跑 `install.sh`。

## 期望值

受众是「KDE Plasma ∩ 有中键习惯 ∩ 常读 Markdown 长文」的交集，天花板不高但转化率高。真正值得追的信号：
KDE 侧有人说「原来中键是这个语义」、有人拿这份机制说明去配别的 MIME 类型、出现第三方主题适配或发行版打包。
如果两周内没有任何自然增长，就只留知识帖，不再推工具。
