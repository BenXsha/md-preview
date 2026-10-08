# Dolphin 的「鼠标中键预览」是怎么选应用的

这份笔记是 md-preview 的由来：先搞清楚中键到底调用了谁，才知道该在哪里换掉渲染器。

## 结论先行

- **鼠标中键 = 打开该 MIME 类型应用列表里的第 2 个应用**，**Shift + 中键 = 第 3 个**。
- 顺序由 `~/.config/mimeapps.list`（配合 desktop 文件的 `InitialPreference`）决定。
- 所以想让中键「换个渲染器」，**不需要写 Okular 插件**，只要把想要的那个应用排到第 2 位。

## 出处（KDE Dolphin 源码）

`src/dolphinviewcontainer.cpp`：

```cpp
void DolphinViewContainer::slotfileMiddleClickActivated(const KFileItem &item)
{
    KService::List services = KApplicationTrader::queryByMimeType(item.mimetype());
    const auto modifiers = QGuiApplication::keyboardModifiers();

    int indexOfAppToOpenFileWith = 1;                                   // 中键 → 第 2 个
    if (modifiers & Qt::ShiftModifier) {
        indexOfAppToOpenFileWith = 2;                                   // Shift+中键 → 第 3 个
    }

    // 可执行的文本脚本会先弹出「运行还是打开」，那种情况下索引再往前挪一格
    auto mimeType = item.currentMimeType();
    if (item.isLocalFile() && mimeType.inherits(QStringLiteral("application/x-executable"))
        && mimeType.inherits(QStringLiteral("text/plain")) && item.isExecutable()) {
        // …读取 kiorc 的 behaviourOnLaunch，必要时 --indexOfAppToOpenFileWith
    }

    if (services.length() >= indexOfAppToOpenFileWith + 1) {             // 数量不够就什么也不做
        const auto &service = services.at(indexOfAppToOpenFileWith);
        KIO::ApplicationLauncherJob *job = new KIO::ApplicationLauncherJob(service, this);
        job->setUrls({item.targetUrl()});
        …
    } else {
        // 退化成「当作压缩包用新标签页打开」，普通文件等于什么都不发生
    }
}
```

触发链：`KItemListController` 判定中键 → `DolphinView::slotItemMiddleClicked` →
`DolphinViewContainer::slotfileMiddleClickActivated` → `KIO::ApplicationLauncherJob`。

## 列表顺序由谁决定

`KApplicationTrader::queryByMimeType()` 返回的是 sycoca 里的服务列表，顺序由
`kservice/src/sycoca/kmimeassociations.cpp` 在构建缓存时算出来：

1. 逐个读 `mimeapps.list`（按「全局 → 用户」的顺序，越靠后的文件基础权重越高），
   在每个文件内：
   - `[Default Applications]` 的条目拿 `base + 25` 分；
   - `[Added Associations]` 的条目拿 `base` 分；
   - 同一个列表里按书写顺序依次递减（第一个分最高）。
2. desktop 文件自己声明的 `MimeType=` 通过 `InitialPreference` 参与排序（分值远低于 mimeapps 条目）。
3. 综合后按分数降序 → **第 0 个就是「双击/回车」用的默认应用，第 1 个是鼠标中键**。
4. 同一服务如果同时被 mimeapps 和 `InitialPreference` 命中，取两者中更高的分数（并记录 MIME 继承层级）。

所以在 `~/.config/mimeapps.list` 里写这样三行，就能精确指定三个槽位：

```ini
[Default Applications]
text/markdown=org.kde.kate.desktop;              # 第 0 位：双击/回车 = 编辑器

[Added Associations]
text/markdown=md-preview.desktop;md-preview-browser.desktop;okularApplication_md.desktop;
#             ↑ 第 1 位：中键      ↑ 第 2 位：Shift+中键            ↑ 第 3 位：原来的 Okular
```

## 查看当前顺序

```console
$ xdg-mime query default text/markdown      # GIO 视角的“默认”（≈ 第 0 位）
$ gio mime text/markdown                    # 默认 + 已注册应用列表
$ ktraderclient6 --mimetype text/markdown   # KDE 视角的完整顺序（装了 kservice 工具时）
```

最可靠的还是直接试：双击一次、中键一次，看分别打开了谁。

## 改完为什么有时不生效

- **必须刷新 KDE 服务缓存**：`kbuildsycoca6 --noincremental`（KDE 走 sycoca，不是 GIO 的缓存）。
  `contrib/install.sh` 会自动做这一步。
- **候选应用少于 2 个**：中键会退化成分支里的「当作压缩包打开」，对普通文件等于什么都不发生。
  至少要保证列表里有 2 个应用。
- **`NoDisplay=true` 不影响**：Okular 的 Markdown 后端就是 `NoDisplay=true` 的
  `okularApplication_md.desktop`，照样能作为中键目标。
- **MIME 继承也会进列表**：`org.kde.kate.desktop` 只声明了 `text/plain`，但 `text/markdown` 继承
  `text/plain`，加上它的 `InitialPreference=9` 高于 Okular 的 7，所以在没有任何 mimeapps 条目的机器上
  它就是第 0 位，Okular 是第 1 位 —— 这正是「双击进编辑器、中键出预览」的默认体验来源。
- **可执行脚本的索引会前移**：文件同时是 `text/plain` + `application/x-executable` 且可执行时，
  中键相当于打开第 1 个应用（见上面的源码）。

## md-preview 的安装脚本做了什么

`contrib/install.sh` 调用 `contrib/merge-mimeapps.py`，只改这两个 MIME 的那两行，
首次修改前把原文件备份成 `~/.config/mimeapps.list.bak-md-preview`；
`contrib/uninstall.sh` 会从备份还原。合并脚本是纯文本编辑，其余行逐字节保留。

## 我们是怎么验证渲染真的生效的

换渲染器这事的坑在于「看起来变了」不等于「主题真的命中了 DOM」。项目里用两层验证：

1. `tools/probe-styles.py`：用 DevTools Protocol 连上无头浏览器，读 `getComputedStyle`，
   检查 `#write` 的宽度、`pre.md-fences` 的底色、`.cm-keyword` 的颜色是否等于主题里的值
   （例：`drake-jb` 的 `pre` 底色应为 `#2b2b2b`，`night` 的 `body` 应为 `rgb(54,59,64)`）。
2. `tools/theme-gallery.py` + `pdftoppm`/PIL：截图与 PDF 页面亮度对比，确认深色主题在 PDF 里
   没有变成「白底浅字」（`print-color-adjust: exact` 是否生效）。
