# 渲染人工验收 · 超长代码行与不换行长串

这份文件是给**人眼**看的验收清单：用 `md-preview` 打开它，逐条对照下面的清单。

每个用例都在超长行的**结尾**放了 `TAIL-xxx` 标记 —— 屏幕上（或 PDF 里）能看见这个标记，
就说明那一行没被裁掉。**旧版本的表现是：PDF 里标记连同整段行尾一起消失，屏幕上是横向滚动条。**

## 怎么打开

```console
$ ./bin/md-preview --html MANUAL-CHECK.md                    # 浏览器：看屏幕观感
$ ./bin/md-preview MANUAL-CHECK.md                           # PDF：用 Okular 打开，看纸面上的结果
$ ./bin/md-preview --no-code-wrap --html MANUAL-CHECK.md     # 对照：屏幕回到横向滚动
```

找不到生成的 PDF 时：

```console
$ find ~/.cache/md-preview -name 'MANUAL-CHECK.pdf'
$ pdftotext -layout "$PDF" - | tr -d '[:space:]-' | grep -oE 'TAIL[A-Z0-9]{2,}' | sort -u
```

最后那条命令应当能认出**全部 13 个** `TAIL-` 标记（`TAIL-CN1` 会被打印成 `TAILCN1` —— 命令故意去掉了
空格与连字符，这样即使折行正好断在标记中间也认得出来；也可能和下一行的文字粘在一起）。少任何一个都算不合格。

## 验收点

| # | 看什么 | 合格的样子 |
|---|---|---|
| 1 | 屏幕上的代码块 | **没有横向滚动条**，长行在代码块右边缘折到下一行 |
| 2 | 折行的续行 | 从代码块**左边缘**开始（不会对齐到注释起始列，这是折行的固有代价） |
| 3 | 每个 `TAIL-` 标记 | 看得见 —— 代码块、行内代码、表格单元格里都要看得见 |
| 4 | PDF | 与屏幕一致：长行折行后**完整**落在纸面上，一个字都不少 |
| 5 | 表格 | 长串所在的列被压窄换行，**表格整体不超出页面右边** |
| 6 | 复制粘贴 | 复制折行的那行代码到编辑器，还原成**完整的一行**（折行只是显示效果） |
| 7 | `--no-code-wrap` 对照 | 屏幕出现横向滚动条；**PDF 仍然折行**（打印必须折行，否则丢字） |
| 8 | 短代码块 | 完全不受影响：不折行、不缩进、不改变对齐 |

## 1. 中文长注释（最容易翻车的场景）

中文字符是双宽，一条 60 字的注释就能顶破 A4 的正文宽度。

```python
def commit(n: int = 1) -> int:
    # 这是一段非常长的中文注释，用来验证代码块里的长行会不会被裁掉：判定的核心在于折行之后行尾的标记是否仍然可见，而不是折行本身发生在第几个字符处 TAIL-CN1
    return n * 42
```

```python
@dataclass(slots=True)
class Ledger:
    """账本落在哪个进程决定 join 的语义，所以同一份数据在不同进程里可能得出不同的结果，这里必须把 owner 显式记下来才能避免歧义 TAIL-CN2"""
    owner: str
```

## 2. 英文长注释与长表达式

```python
# This comment is deliberately long enough to exceed the printable column width of an A4 page so that the old build silently truncated the tail of the line TAIL-EN1
joined = gateway.join(ledger, on=["tenant", "id"], how="left", validate="many_to_one", suffixes=("_l", "_r"), keep_order=True)  # TAIL-EN2
```

## 3. 无空格的长串（路径 / URL / 哈希 / base64）

这类内容**没有任何断句点**，只能靠 `overflow-wrap: anywhere` 在任意位置断开。

```python
CACHE = "/var/lib/some/very/deep/directory/layout/that/keeps/going/and/going/until/it/definitely/exceeds/the/column/width/TAIL-PATH"
```

```python
URL = "https://example.com/api/v2/tenants/acme/ledgers/2025/10/items?filter=status%3Dopen&sort=-created_at&page=7&per_page=200#fragment-TAIL-URL"
```

```bash
sha256sum="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855e3b0c44298fc1c149afbf4c8996fb924TAIL-HASH"
```

```bash
payload="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJsZWRnZXIiLCJ0ZW5hbnQiOiJhY21lIiwiaWF0IjoxNzAwMDAwMDAwfQ.TAIL-B64"
```

## 4. 超长单行命令（管道链）

AI 给出的"一条命令"经常是这样。

```bash
kubectl get pods -A -o json | jq -r '.items[] | select(.status.phase != "Running") | [.metadata.namespace, .metadata.name, .status.phase] | @tsv' | sort -k1,1 -k3,3 | column -t -s $'\t' | sed -n '1,200p' TAIL-SHELL
```

## 5. 行内代码（不在代码块里）

```markdown
行内代码也会撑破版面：`sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855TAIL-INLINE`
```

上面那个反引号里的长串在渲染后是 `<code>`，旧版本会把它整段推出页面右边并裁掉。

## 6. 表格里的长串

| 场景 | 内容 | 结果 |
|---|---|---|
| 长路径 | `/srv/gateway/tenants/acme/ledgers/2025-10/partitions/00/segments/00000000000000000000/offsets.idx` | 应当折行 TAIL-TD1 |
| 长行内代码 | `SELECT tenant, id, count(*) FROM events WHERE created_at >= now() - interval '7 days' GROUP BY 1, 2 TAIL-TD2` | 应当折行 |

## 7. 对照组：短代码块

下面两个块**不应**有任何变化（既不折行，也不改变缩进或背景）。

```python
print("hello")  # 短注释 TAIL-SHORT
```

```python
def f():
    return 42
```

## 8. 贴成一行复制（可选）

把第 1 节里那条带 `TAIL-CN1` 的注释整行复制到编辑器：应当得到**和源文件一样的一行**，
中间不会多出换行（折行是 CSS 的事，不影响剪贴板）。

## 结果记录

| # | 检查项 | 结果 |
|---|---|---|
| 1 | 屏幕无横向滚动条 | ☐ 通过 / ☐ 不通过 |
| 2 | 续行从左边缘起排 | ☐ 通过 / ☐ 不通过 |
| 3 | 全部 `TAIL-` 标记可见（屏幕） | ☐ 通过 / ☐ 不通过 |
| 4 | 全部 `TAIL-` 标记可见（PDF） | ☐ 通过 / ☐ 不通过 |
| 5 | 表格未超出页面右边 | ☐ 通过 / ☐ 不通过 |
| 6 | 复制粘贴还原为一行 | ☐ 通过 / ☐ 不通过 |
| 7 | `--no-code-wrap`：屏幕滚动、PDF 仍折行 | ☐ 通过 / ☐ 不通过 |
| 8 | 短代码块未受影响 | ☐ 通过 / ☐ 不通过 |

## 顺便复看的主题

```console
$ ./bin/md-preview --theme default-dark --html MANUAL-CHECK.md   # 深色主题下同样不丢字、无横向滚动
$ ./bin/md-preview --theme default MANUAL-CHECK.md               # 换成 PDF 主题再出一份
```

第三方主题如果自己写了 `white-space: pre`，屏幕上的折行会被它盖掉，但**打印时仍有 `!important` 兜底**：
这一类主题请以 PDF 的观感为准，并可用第 4 条检查项确认没有丢字。
