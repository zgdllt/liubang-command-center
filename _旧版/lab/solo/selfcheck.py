"""上一任的自检脚本。

它只覆盖三个最简单的情况，不覆盖 ACCEPTANCE.md 的完整规则。
不要把它当成监军验收。
"""

from granary import allocate_grain


def check(name, fn):
    try:
        fn()
        print(f"PASS {name}")
        return True
    except Exception as exc:  # noqa: BLE001 - 自检脚本，打印所有异常
        print(f"FAIL {name}: {type(exc).__name__}: {exc}")
        return False


def equal_split():
    out = allocate_grain(
        100,
        [
            {"name": "A", "need": 50, "priority": 1},
            {"name": "B", "need": 50, "priority": 1},
        ],
    )
    assert out["allocations"][0]["grain"] == 50
    assert out["allocations"][1]["grain"] == 50


def single():
    out = allocate_grain(30, [{"name": "A", "need": 100, "priority": 3}])
    assert out["allocations"][0]["grain"] == 30


def zero():
    out = allocate_grain(0, [{"name": "A", "need": 10, "priority": 1}])
    assert out["allocations"][0]["grain"] == 0


if __name__ == "__main__":
    results = [
        check("equal_split", equal_split),
        check("single", single),
        check("zero", zero),
    ]
    print()
    print("自检结束。记住：这不是监军验收。")
    raise SystemExit(0 if all(results) else 1)
