# 渲染主题测试 / Render smoke test

正文段落：中文与 English 混排，包含 **加粗**、*斜体*、`inline code`、[链接](https://kde.org)、~~删除线~~，
以及一个较长的句子用来看行距与两端对齐的效果：判定的核心在于 join key 究竟落在哪一层，而不是扩展的数量。

## 二级标题 Heading 2

- 列表项一
- 列表项二，带 `code`
- 列表项三

1. 有序一
2. 有序二

### 三级标题

> 引用块：注意背景、左边框与文字颜色是否随主题变化。
> 第二行引用。

#### 表格

| 维度 | 方案 A | 方案 B | 备注 |
|---|---|---|---|
| 延迟 | 12 ms | 38 ms | 越小越好 |
| 成本 | 高 | 低 | — |
| 可维护性 | 中 | 高 | `join` 在网关层 |

#### 代码块

```python
from dataclasses import dataclass

@dataclass(slots=True)
class Ledger:
    """账本落在哪个进程，决定 join 的语义。"""
    owner: str
    entries: list[str] = None  # type: ignore[assignment]

    def commit(self, n: int = 1) -> int:
        return n * 42
```

```javascript
const joinKey = (row) => `${row.tenant}:${row.id}`;  // 复合键
console.log(joinKey({ tenant: "a", id: 7 }));
```

```bash
md-preview --theme newsprint doc.md   # 生成带主题样式的 PDF
```

#### 结语

最后一段：用来确认段落间距、页面底部留白是否正常。


#### 内容规则：任务列表 / 告警块 / 脚注

- [ ] 待办：把 join key 落到网关层
- [x] 已完成：把账本移出请求进程

> [!NOTE]
> 告警块在浅色与深色主题下都应当保持可读。

> [!WARNING] 容量
> 账本超过 2 GB 时触发 compaction。

脚注：正文里写 `[^1]` 这种上标引用，文末给出定义[^sample]。

[^sample]: 脚注正文，用来确认脚注区的分隔线、字号与回链位置。
