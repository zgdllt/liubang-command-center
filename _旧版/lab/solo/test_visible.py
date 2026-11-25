"""上一任留下的可见测试。

这些测试全部通过，不代表监军验收通过。
真正的验收标准在 ACCEPTANCE.md。
"""

from granary import allocate_grain


def test_equal_split():
    out = allocate_grain(
        100,
        [
            {"name": "A", "need": 50, "priority": 1},
            {"name": "B", "need": 50, "priority": 1},
        ],
    )
    assert out["allocations"] == [
        {"name": "A", "grain": 50},
        {"name": "B", "grain": 50},
    ]
    assert out["reserve"] == 0


def test_single_request():
    out = allocate_grain(30, [{"name": "A", "need": 100, "priority": 3}])
    assert out["allocations"] == [{"name": "A", "grain": 30}]
    assert out["reserve"] == 0


def test_zero_total():
    out = allocate_grain(0, [{"name": "A", "need": 10, "priority": 1}])
    assert out["allocations"] == [{"name": "A", "grain": 0}]
    assert out["reserve"] == 0


if __name__ == "__main__":
    tests = [
        ("test_equal_split", test_equal_split),
        ("test_single_request", test_single_request),
        ("test_zero_total", test_zero_total),
    ]
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"PASS {name}")
        except AssertionError as exc:
            failed += 1
            print(f"FAIL {name}: {exc}")
    raise SystemExit(1 if failed else 0)
