# 监军验收：粮草分配器

> 这是客户（监军）的验收标准，不是上一任的测试。  
> 不要修改本文件。你的实现必须满足这里的每一条。

## 函数

```python
allocate_grain(total: int, requests: list[dict]) -> dict
```

返回：

```python
{
    "allocations": [{"name": str, "grain": int}, ...],
    "reserve": int,
}
```

## 输入

- `total`：非负整数，单位石。
- `requests`：列表，每项为 `{"name": str, "need": int, "priority": int}`。
  - `name`：非空字符串，列表内唯一。
  - `need`：非负整数，单位石。
  - `priority`：1–5 的整数，数字越大越优先。

## 输出

- `allocations`：与输入**同序**的列表，每项 `{"name": str, "grain": int}`。
- `reserve`：未分配完的余粮，非负整数。

## 规则

1. **守恒**：`sum(grain) + reserve == total`。
2. **上限**：对每一项，`0 <= grain <= need`。
3. **优先级**：高优先级先满足。对任意两项，若 `priority_a > priority_b`，则 `grain_a / need_a >= grain_b / need_b`（`need > 0` 时）。
4. **组内比例**：同一优先级内，按 `need` 比例分配。用最大余数法取整：先取整数部分，剩余的单位按小数部分从大到小分配；小数部分相同，按输入顺序。
5. **余粮**：如果 `total >= sum(need)`，所有 `need` 都满足，`reserve = total - sum(need)`。
6. **空请求**：`requests == []` 时，`allocations == []`，`reserve == total`。
7. **确定性**：相同输入，相同输出。
8. **非法输入**：抛出 `ValueError`，消息里包含出错的字段名。
   - `total < 0` 或不是整数；
   - `need < 0` 或不是整数；
   - `priority` 不在 1–5；
   - `name` 为空或重复；
   - `requests` 不是列表，或某项不是字典。

## 一个例子

```python
allocate_grain(10, [
    {"name": "A", "need": 10, "priority": 1},
    {"name": "B", "need": 10, "priority": 1},
    {"name": "C", "need": 10, "priority": 1},
])
# => {"allocations": [{"name": "A", "grain": 4},
#                      {"name": "B", "grain": 3},
#                      {"name": "C", "grain": 3}],
#     "reserve": 0}
```

## 另一个例子

```python
allocate_grain(100, [
    {"name": "前线", "need": 200, "priority": 5},
    {"name": "后方", "need": 50, "priority": 1},
])
# => {"allocations": [{"name": "前线", "grain": 100},
#                      {"name": "后方", "grain": 0}],
#     "reserve": 0}
```

高优先级没有满足之前，低优先级不分配。
