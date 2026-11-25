# -*- coding: utf-8 -*-
"""字幕质量量化统计：对 subs/<slug>.json 逐条算。

用法：python3 scripts/quant_subs.py [--tag before] [snap.json]

指标：
  cues            条数
  lead_punct      以标点开头的条数
  short<0.6       时长 < 0.6 秒的条数
  split_en        把英文单词切成两半的条数（前一条以字母结尾、后一条以字母开头）
  chars           总字数
  cps_avg         平均字/秒（总字数 / 字幕覆盖时长）
  cps_p95         95 分位单条字/秒
  cps_max         单条最高字/秒
  max_chars       单条最长字数
  lines1/2/3      单行/双行/三行以上的条数
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PUNCT = set("，。！？；：、…,.!?;:")   # 只统计分隔标点，引号开头是正常的


def is_ascii_letter(ch: str) -> bool:
    return ch.isascii() and ch.isalpha()


def analyse(cues: list[dict]) -> dict:
    cues = [c for c in cues if c.get("text")]
    n = len(cues)
    lead = 0
    short = 0
    split_en = 0
    chars = 0
    cps = []
    max_chars = 0
    line_counts = {1: 0, 2: 0, 3: 0}
    covered = 0.0
    for i, c in enumerate(cues):
        t = c["text"]
        plain = t.replace("\n", "")
        chars += len(plain)
        dur = max(1e-3, c["end"] - c["start"])
        covered += dur
        cps.append(len(plain) / dur)
        max_chars = max(max_chars, len(plain))
        nl = t.count("\n") + 1
        line_counts[3 if nl > 2 else nl] += 1
        if plain and plain[0] in PUNCT:
            lead += 1
        if dur < 0.6:
            short += 1
        if i and plain and is_ascii_letter(plain[0]):
            prev = cues[i - 1]["text"].rstrip()
            if prev and is_ascii_letter(prev[-1]):
                split_en += 1
    cps.sort()
    p95 = cps[int(0.95 * (len(cps) - 1))] if cps else 0
    return {
        "cues": n,
        "lead_punct": lead,
        "short<0.6": short,
        "split_en": split_en,
        "chars": chars,
        "covered": round(covered, 1),
        "cps_avg": round(chars / covered, 2) if covered else 0,
        "cps_p95": round(p95, 2),
        "cps_max": round(max(cps), 2) if cps else 0,
        "max_chars": max_chars,
        "lines1": line_counts[1],
        "lines2": line_counts[2],
        "lines3": line_counts[3],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="")
    ap.add_argument("--snap", default="")
    a = ap.parse_args()
    rows = {}
    for f in sorted((ROOT / "subs").glob("*.json")):
        rows[f.stem] = analyse(json.loads(f.read_text(encoding="utf-8")))
    keys = ["cues", "lead_punct", "short<0.6", "split_en", "chars", "cps_avg", "cps_p95",
            "cps_max", "max_chars", "lines1", "lines2", "lines3"]
    print(f"{'film':16s}" + "".join(f"{k:>10s}" for k in keys))
    for slug, r in rows.items():
        print(f"{slug:16s}" + "".join(f"{r[k]:>10}" for k in keys))
    tot = {k: sum(r[k] for r in rows.values() if k not in ("cps_avg", "cps_p95"))
           for k in keys if k not in ("cps_avg", "cps_p95", "cps_max")}
    tot["cps_avg"] = round(tot["chars"] / tot["covered"], 2) if tot.get("covered") else 0
    tot["cps_p95"] = max(r["cps_p95"] for r in rows.values())
    tot["cps_max"] = max(r["cps_max"] for r in rows.values())
    print(f"{'ALL':16s}" + "".join(f"{tot.get(k, 0):>10}" for k in keys))
    if a.snap:
        Path(a.snap).write_text(json.dumps({"tag": a.tag, "films": rows, "total": tot},
                                           ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"\nsnapshot -> {a.snap}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
