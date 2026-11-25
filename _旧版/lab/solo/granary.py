"""粮草分配器（待修复）。

客户验收标准见 ACCEPTANCE.md。不要修改函数签名。
"""

from typing import Dict, List


def allocate_grain(total: int, requests: List[Dict]) -> Dict:
    """按需求比例分配粮草。

    Args:
        total: 粮草总量（石）。
        requests: [{"name": str, "need": int, "priority": int}, ...]

    Returns:
        {"allocations": [{"name": str, "grain": int}, ...], "reserve": int}
    """
    result = []
    need_sum = sum(req["need"] for req in requests)

    for req in requests:
        share = int(round(total * req["need"] / need_sum))
        share = min(share, req["need"])
        result.append({"name": req["name"], "grain": share})

    return {"allocations": result, "reserve": 0}
