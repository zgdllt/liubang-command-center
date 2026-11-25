# -*- coding: utf-8 -*-
"""把 films.py + vo 时长 → pages/<slug>.html、subs/<slug>.json、work/manifest_<slug>.json。

用法：python3 scripts/build.py [--films slug,...] [--no-webp]
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import films  # noqa: E402

WORK = ROOT / "work"
SPEED = 0.86    # 与 assemble.py 一致：旁白整体放慢，保音高
GAP = 0.38          # 句间停顿
LEAD_IN = 1.10      # 片头留白
BEAT_LEAD = 0.90    # 画面比台词早出
BEAT_TAIL = 1.10
TAIL = 1.40         # 片尾压黑
SUBC = 17           # 字幕每行最多字数


def dur_of(path: Path) -> float:
    out = subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                   "-of", "csv=p=0", str(path)])
    return float(out.strip())


def trim_edges(path: Path, work: Path) -> Path:
    """去首尾静音（保留约 50ms），返回处理后的文件。"""
    work.mkdir(parents=True, exist_ok=True)
    dest = work / (path.stem + ".wav")
    if dest.exists() and dest.stat().st_mtime >= path.stat().st_mtime:
        return dest
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(path),
                    "-af", "silenceremove=start_periods=1:start_silence=0.05:start_threshold=-45dB:"
                           "stop_periods=-1:stop_silence=0.06:stop_threshold=-45dB,"
                           f"atempo={SPEED}",
                    "-ac", "1", "-ar", "48000", "-c:a", "pcm_s16le", str(dest)], check=True)
    return dest


# ───────────── 字幕切分 ─────────────
# 规则：句末标点先断句；超长再在逗号/顿号/冒号处软断；仍超长才硬断，
# 断点落在标点前、不切 ASCII 单词；不出现以标点开头的条；合并过短的条；
# 时长按「字重」分配（汉字 1、英文词 2、标点 0.4）。
LINE_W = 15.0        # 每行目标字重（约 14–15 个汉字）
CUE_W = 30.0         # 每条最多两行、约 30 个字重
MIN_CUE = 0.90       # 太短的条合并（秒）
LEAD_STRIP = "，、：；。！？…,.!?;:"   # 只吃掉行首的分隔标点，不动引号括号
SENT_END = "。！？；…!?;"
SOFT = "，、：:"
PUNCT_ALL = SENT_END + SOFT + "「」『』（）()《》〈〉—·,."
ASCII_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9'’\-\.\+#/]*(?: [A-Za-z0-9][A-Za-z0-9'’\-\.\+#/]*)*")


def _tokens(text: str) -> list[list]:
    """切成 [片段, 字重, 类型]；ASCII 词整词一块，标点单独一块。"""
    out, i = [], 0
    while i < len(text):
        ch = text[i]
        m = ASCII_RE.match(text, i)
        if m and ch.isascii():
            w = m.group(0)
            out.append([w, 2.0 + 1.2 * w.count(" "), "en"])
            i = m.end()
            continue
        if ch.isspace():
            i += 1
            continue
        if ch in PUNCT_ALL:
            out.append([ch, 0.4, "p"])
        else:
            out.append([ch, 1.0, "han"])
        i += 1
    return out


def _lines(toks: list[list], max_w: float = LINE_W) -> list[list[list]]:
    """按字重切行；优先在软标点后断，行首不留标点。"""
    lines, cur, curw = [], [], 0.0
    for t in toks:
        if cur and curw + t[1] > max_w:
            lines.append(cur); cur, curw = [], 0.0
        cur.append(t); curw += t[1]
        if t[2] == "p" and t[0] in SOFT and curw >= max_w * 0.55:
            lines.append(cur); cur, curw = [], 0.0
    if cur:
        lines.append(cur)
    fixed = []
    for ln in lines:
        if fixed and ln and ln[0][2] == "p":      # 行首标点并入上一行
            fixed[-1].extend(ln)
        elif ln:
            fixed.append(ln)
    return fixed


def _brief(t: str) -> str:
    return t.strip()


def split_subs(text: str, start: float, end: float) -> list[dict]:
    """把一句旁白切成字幕条（每条 1–2 行），时间按字重分配。"""
    text = re.sub(r"\[[^\]]*\]", "", text).strip()   # TTS 停顿标签不进字幕
    if not text:
        return []
    cues: list[dict] = []
    for sent in [p for p in re.split(rf"(?<=[{re.escape(SENT_END)}])", text) if p.strip()]:
        lines = _lines(_tokens(sent))
        groups, cur, curw = [], [], 0.0
        for ln in lines:
            w = sum(t[1] for t in ln)
            if cur and (len(cur) >= 2 or curw + w > CUE_W):
                groups.append(cur); cur, curw = [], 0.0
            cur.append(ln); curw += w
        if cur:
            groups.append(cur)
        for g in groups:
            cues.append({"text": "\n".join("".join(t[0] for t in ln) for ln in g),
                         "w": sum(t[1] for ln in g for t in ln)})
    if not cues:
        return []
    total_w = sum(c["w"] for c in cues) or 1.0
    span = max(0.2, end - start)
    cur_t = start
    for c in cues:
        d = span * c["w"] / total_w
        c["start"], c["end"] = cur_t, cur_t + d
        cur_t += d
    # 合并过短的条（保留两行以内）
    merged: list[dict] = []
    for c in cues:
        short_prev = merged and (merged[-1]["end"] - merged[-1]["start"] < MIN_CUE)
        if merged and (short_prev or c["end"] - c["start"] < MIN_CUE):
            prev = merged[-1]
            joined = prev["text"].replace("\n", "") + c["text"].replace("\n", "")
            if joined.count("\n") == 0 and len(joined.replace("\n", "")) <= 32:
                prev["text"] = joined
                prev["end"] = c["end"]
                continue
        merged.append(c)
    out = []
    for c in merged:
        t = c["text"].replace("\n", "").lstrip(LEAD_STRIP)
        if not t:
            continue
        out.append({"text": t, "start": round(c["start"], 3), "end": round(c["end"], 3)})
    # 说得偏快：把开头往前挪一点（字幕先于语音出现，是常见做法），降低阅读速度
    for i, c in enumerate(out):
        d = c["end"] - c["start"]
        plain = c["text"].replace("\n", "")
        if d > 0 and len(plain) / d > 9.5:
            room = min(0.45, (len(plain) / 9.5) - d)
            if i > 0:
                room = min(room, (out[i - 1]["end"] - out[i - 1]["start"]) * 0.25)
            if room > 0:
                c["start"] = round(c["start"] - room, 3)
    # 仍然过短：向后借、向前借，最后吃句间空隙
    for i, c in enumerate(out):
        d = c["end"] - c["start"]
        if d >= MIN_CUE:
            continue
        need = MIN_CUE - d
        if i + 1 < len(out):
            nxt = out[i + 1]
            take = min(need, (nxt["end"] - nxt["start"]) * 0.5)
            c["end"] = round(c["end"] + take, 3)
            nxt["start"] = round(nxt["start"] + take, 3)
            need -= take
        if need > 0 and i > 0:
            prv = out[i - 1]
            take = min(need, (prv["end"] - prv["start"]) * 0.3)
            c["start"] = round(c["start"] - take, 3)
            prv["end"] = round(prv["end"] - take, 3)
            need -= take
        if need > 0:
            c["end"] = round(c["end"] + min(need, 0.30), 3)
    # 兜底：两行重新按 CUE 字数均分（避免出现 1 行 28 字）
    final = []
    for c in out:
        plain = c["text"]
        if len(plain) > 15:
            half = _best_cut(plain, len(plain) // 2)
            c = dict(c)
            c["text"] = plain[:half] + "\n" + plain[half:]
        final.append(c)
    return final


def _best_cut(text: str, around: int) -> int:
    """在 around 附近找切点：不切进 ASCII 词组，优先切在软标点后。"""
    spans = [(m.start(), m.end()) for m in ASCII_RE.finditer(text)]

    def inside(k: int) -> bool:
        return any(a < k < b for a, b in spans)

    lo, hi = max(1, around - 8), min(len(text) - 1, around + 8)
    best, best_score = max(1, min(around, len(text) - 1)), 10 ** 9
    for k in range(lo, hi + 1):
        if inside(k):
            continue
        score = abs(k - around)
        if text[k - 1] in SOFT:
            score -= 3
        if score < best_score:
            best, best_score = k, score
    return best



def build(slug: str, no_webp: bool = False) -> dict:
    f = films.FILMS[slug]
    vodir = ROOT / "vo" / slug
    beats_out = []
    cues = []
    cursor = LEAD_IN
    for bi, beat in enumerate(f["beats"]):
        line_recs = []
        for li, text in enumerate(beat["lines"]):
            src = vodir / f"b{bi:02d}l{li:02d}.wav"
            if not src.exists():
                raise FileNotFoundError(src)
            d = dur_of(trim_edges(src, WORK / "trim" / slug))
            line_recs.append({"text": text, "start": cursor, "end": cursor + d, "dur": d,
                              "file": f"{slug}/b{bi:02d}l{li:02d}.wav"})
            cursor += d + GAP
        b = {k: v for k, v in beat.items() if k != "lines"}
        b["start"] = 0.0 if bi == 0 else round(max(0.0, line_recs[0]["start"] - BEAT_LEAD), 3)
        b["end"] = round(line_recs[-1]["end"] + BEAT_TAIL, 3)
        b["lines"] = [{"text": r["text"], "start": round(r["start"], 3), "end": round(r["end"], 3)}
                      for r in line_recs]
        for r in line_recs:
            cues.extend(split_subs(r["text"], r["start"], r["end"]))
        beats_out.append(b)
    duration = round(beats_out[-1]["end"] + TAIL, 3)

    # 资源清单（只收本片用到的）
    keys = []
    for b in beats_out:
        if b.get("asset") and b["asset"] not in keys:
            keys.append(b["asset"])
    keys.append("ink_splash")
    assets = {}
    for k in keys:
        png = ROOT / "assets" / f"{k}.png"
        if not png.exists():
            print(f"  ! missing asset {k}")
            continue
        if no_webp:
            assets[k] = f"../assets/{k}.png"
        else:
            jpg = ROOT / "assets/jpg" / f"{k}.jpg"
            jpg.parent.mkdir(exist_ok=True)
            if not jpg.exists() or jpg.stat().st_mtime < png.stat().st_mtime:
                subprocess.run(["sips", "-s", "format", "jpeg", "-s", "formatOptions", "86",
                                "--resampleWidth", "1536", str(png), "--out", str(jpg)],
                               check=True, capture_output=True)
            assets[k] = f"../assets/jpg/{k}.jpg"

    data = {"slug": slug, "title": f["title"], "kicker": f["kicker"], "epno": f["epno"],
            "duration": duration, "tail": TAIL, "beats": beats_out}
    tpl = (ROOT / "scripts/page_template.html").read_text(encoding="utf-8")
    html = (tpl.replace("__TITLE__", f'{f["epno"]} · {f["title"]}')
               .replace("__FONT_ZHIMANG__", "../fonts/zhimangxing.ttf")
               .replace("__FONT_MASHAN__", "../fonts/mashanzheng.ttf")
               .replace("__FONT_WENKAI__", "../fonts/lxgwwenkai.ttf")
               .replace("__FONT_CAVEAT__", "../fonts/caveat.ttf")
               .replace("__DATA__", json.dumps(data, ensure_ascii=False))
               .replace("__ASSETS__", json.dumps(assets, ensure_ascii=False)))
    pages = ROOT / "pages"
    pages.mkdir(exist_ok=True)
    (pages / f"{slug}.html").write_text(html, encoding="utf-8")
    (ROOT / "subs").mkdir(exist_ok=True)
    (ROOT / "subs" / f"{slug}.json").write_text(json.dumps(cues, ensure_ascii=False, indent=0),
                                                encoding="utf-8")
    all_lines = []
    for bi, bb in enumerate(beats_out):
        for li, r in enumerate(bb["lines"]):
            all_lines.append({"beat": bi, "file": f"{slug}/b{bi:02d}l{li:02d}.wav",
                              "text": r["text"], "start": r["start"], "end": r["end"],
                              "seconds": round(r["end"] - r["start"], 3)})
    (ROOT / "work" / f"manifest_{slug}.json").write_text(
        json.dumps({"slug": slug, "title": f["title"], "duration": duration,
                    "lines": all_lines, "beats": beats_out}, ensure_ascii=False, indent=1),
        encoding="utf-8")
    return {"slug": slug, "duration": duration, "beats": len(beats_out), "cues": len(cues),
            "assets": len(assets)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--films", default="")
    ap.add_argument("--no-webp", action="store_true")
    a = ap.parse_args()
    slugs = [s for s in a.films.split(",") if s] or list(films.FILMS)
    for slug in slugs:
        try:
            info = build(slug, a.no_webp)
            print(f"{slug:16s} {info['duration']:6.1f}s  beats={info['beats']} cues={info['cues']} assets={info['assets']}")
        except Exception as e:  # noqa: BLE001
            print(f"FAIL {slug}: {e}", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
