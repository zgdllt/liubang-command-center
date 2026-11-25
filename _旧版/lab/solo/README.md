# 实验 A：萧何的粮道

> "镇国家，抚百姓，给馈饷，不绝粮道，吾不如萧何。"  
> 现在你是萧何。你要把一个粮草分配器修好，让监军验收通过。

## 你的任务

用你自己的 agent 修好 `granary.py`，让 `allocate_grain` 满足 `ACCEPTANCE.md`。

## 规则

1. 你可以让 agent 做任何事：读文件、改代码、跑测试。
2. 你不能修改 `ACCEPTANCE.md`（客户验收标准）。
3. 你有 15 分钟。
4. 提交时，把两样东西放到 `submissions/<你的名字>/`：
   - `granary.py`
   - `criteria.md`：你给 agent 的验收清单（你要求它满足哪些条件）

## 先看什么

```bash
cd lab/solo
cat ACCEPTANCE.md          # 客户验收标准
cat README.md              # 本文件
python3 test_visible.py    # 上一任留下的测试
python3 selfcheck.py       # 上一任的自检
```

## 关键提示

- `test_visible.py` 全部通过，不代表监军验收通过。
- 监军验收在讲师机器上，覆盖 `ACCEPTANCE.md` 里的全部规则。
- 你给 agent 的 brief 里写了什么，它就会优化什么。你没写下的维度，它不会替你想。

## 计分

| 项 | 分值 |
|---|---|
| 隐藏验收（10 项） | 10 |
| 验收清单覆盖（6 组关键词） | 6 |
| 合计 | 16 |

## 提交示例

```text
submissions/韩信/
├── granary.py
└── criteria.md
```

`criteria.md` 可以很短，例如：

```markdown
# 我给 agent 的验收清单
- 总量守恒：分配 + 余粮 = total
- 优先级：高优先级先满足
- 上限：不超过 need
- 非法输入抛 ValueError
- 同优先级按 need 比例，最大余数法
- 同样输入同样输出
```
