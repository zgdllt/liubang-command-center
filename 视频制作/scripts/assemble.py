# -*- coding: utf-8 -*-
"""配乐（合成古琴/鼓点）+ 音效 + 旁白混音 → out/<slug>.mp4 与 out/<slug>.srt。

用法：python3 scripts/assemble.py [--films slug,...] [--keep-stems]
"""
from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
SR = 48000
# 旁白已在 build.py 里做过 atempo 放慢，这里直接用 work/trim 的成品
VOICE_RMS_DB = -20.0  # 旁白目标 RMS
MUSIC_UNDER = -11.0   # 人声下音乐相对压低
SEED_BASE = 20261124


# ───────────── 基础合成工具 ─────────────
def db(x: float) -> float:
    return 10 ** (x / 20)


def fade(x: np.ndarray, a: float, b: float) -> np.ndarray:
    n = len(x)
    na, nb = int(a * SR), int(b * SR)
    y = x.copy()
    if na:
        y[:na] *= np.linspace(0, 1, na) ** 0.6
    if nb:
        y[-nb:] *= np.linspace(1, 0, nb) ** 1.4
    return y


def lowpass(x: np.ndarray, cutoff: float) -> np.ndarray:
    """一阶 IIR 低通（够用，速度快）。"""
    a = math.exp(-2 * math.pi * cutoff / SR)
    y = np.empty_like(x)
    acc = 0.0
    for i in range(len(x)):
        acc = a * acc + (1 - a) * x[i]
        y[i] = acc
    return y


def fft_lowpass(x: np.ndarray, cutoff: float, order: int = 4) -> np.ndarray:
    spec = np.fft.rfft(x)
    freqs = np.fft.rfftfreq(len(x), 1 / SR)
    resp = 1 / np.sqrt(1 + (freqs / cutoff) ** (2 * order))
    return np.fft.irfft(spec * resp, n=len(x))


def pluck(freq: float, dur: float, rng: np.random.Generator, bright: float = 0.5,
          decay: float = 0.996) -> np.ndarray:
    """Karplus-Strong 拨弦。"""
    n = int(dur * SR)
    period = max(2, int(SR / freq))
    buf = rng.uniform(-1, 1, period)
    buf = 0.5 * buf + 0.5 * np.roll(buf, 1)
    buf = fft_lowpass(buf, 1200 + 5000 * bright)
    out = np.empty(n)
    idx = 0
    for i in range(n):
        out[i] = buf[idx]
        nxt = (idx + 1) % period
        buf[idx] = decay * 0.5 * (buf[idx] + buf[nxt])
        idx = nxt
    return fade(out, 0.005, dur * 0.35) * 0.55


def pad(freq: float, dur: float, amp: float = 0.05) -> np.ndarray:
    n = int(dur * SR)
    t = np.arange(n) / SR
    lfo = 0.75 + 0.25 * np.sin(2 * np.pi * 0.09 * t + 1.3)
    x = (np.sin(2 * np.pi * freq * t) + 0.5 * np.sin(2 * np.pi * freq * 1.003 * t)
         + 0.25 * np.sin(2 * np.pi * freq * 2.001 * t))
    return fade(x * lfo * amp, dur * 0.25, dur * 0.4)


def thump(dur: float = 0.5, freq: float = 62.0, amp: float = 0.5,
          rng: np.random.Generator | None = None) -> np.ndarray:
    n = int(dur * SR)
    t = np.arange(n) / SR
    body = np.sin(2 * np.pi * freq * t * (1 - 0.25 * t / dur)) * np.exp(-t * 12)
    click = np.zeros(n)
    if rng is not None:
        k = int(0.02 * SR)
        click[:k] = fft_lowpass(rng.uniform(-1, 1, k), 3000) * np.exp(-np.arange(k) / (0.006 * SR))
    return (body * 0.9 + click * 0.5) * amp


def whoosh(dur: float = 0.35, amp: float = 0.16, rng: np.random.Generator | None = None) -> np.ndarray:
    n = int(dur * SR)
    noise = rng.uniform(-1, 1, n)
    out = np.empty(n)
    seg = 512
    for i in range(0, n, seg):
        tt = i / n
        cutoff = 400 + 3800 * math.sin(math.pi * tt)
        out[i:i + seg] = fft_lowpass(noise[i:i + seg], max(200, cutoff))
    env = np.sin(np.pi * np.arange(n) / n) ** 2
    return out * env * amp


def paper(dur: float = 0.28, amp: float = 0.10, rng: np.random.Generator | None = None) -> np.ndarray:
    n = int(dur * SR)
    x = fft_lowpass(rng.uniform(-1, 1, n), 5000) * np.exp(-np.arange(n) / (0.07 * SR))
    n2 = int(0.06 * SR)
    x2 = np.zeros(n)
    x2[-n2:] = fft_lowpass(rng.uniform(-1, 1, n2), 6500) * np.exp(-np.arange(n2) / (0.02 * SR))
    return (x + 0.6 * x2) * amp


def inkping(dur: float = 0.6, freq: float = 880.0, amp: float = 0.06) -> np.ndarray:
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = np.sin(2 * np.pi * freq * t) * np.exp(-t * 7) + 0.4 * np.sin(2 * np.pi * freq * 1.5 * t) * np.exp(-t * 9)
    return x * amp


def reverb(x: np.ndarray, rng: np.random.Generator, mix: float = 0.28, decay: float = 1.6) -> np.ndarray:
    n = int(decay * SR)
    ir = rng.uniform(-1, 1, n) * np.exp(-np.arange(n) / (0.28 * SR))
    ir = fft_lowpass(ir, 3800)
    ir /= np.sqrt((ir ** 2).sum()) + 1e-9
    wet = np.convolve(x, ir)[: len(x)]
    return (1 - mix) * x + mix * wet


# ───────────── 音乐 ─────────────
def music(duration: float, key: float, seed: int, density: float = 1.0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    n = int((duration + 1.0) * SR)
    out = np.zeros(n)
    scale = [0, 3, 5, 7, 10]          # 小调五声
    base = key
    # 低音持续
    for f, a in ((base / 2, 0.030), (base * 0.75, 0.018)):
        p = pad(f, duration, a)
        out[: len(p)] += p
    # 拨弦
    t = 1.2
    motif = [0, 2, 4, 2, 1, 3, 2, 0]
    step = 0
    while t < duration - 0.8:
        deg = scale[motif[step % len(motif)]] + 12 * (2 if rng.random() < 0.18 else 1)
        freq = base * (2 ** (deg / 12))
        dur = rng.uniform(1.8, 3.2)
        note = pluck(freq, dur, rng, bright=rng.uniform(0.25, 0.7), decay=0.9965)
        i = int(t * SR)
        if i + len(note) < n:
            out[i:i + len(note)] += note * rng.uniform(0.10, 0.22) * density
        # 偶尔加八度泛音
        if rng.random() < 0.22:
            note2 = pluck(freq * 2, dur * 0.7, rng, bright=0.8, decay=0.995)
            j = int((t + 0.02) * SR)
            if j + len(note2) < n:
                out[j:j + len(note2)] += note2 * 0.06
        t += rng.uniform(2.2, 4.6) / density
    # 鼓点
    beats = np.arange(4.0, duration - 1.0, 7.2 / density)
    for bt in beats:
        if rng.random() < 0.55:
            k = thump(0.55, 64 if rng.random() < 0.7 else 82, amp=rng.uniform(0.10, 0.18), rng=rng)
            i = int(bt * SR)
            out[i:i + len(k)] += k
    out = reverb(out, rng, mix=0.30, decay=1.9)
    return fade(out, 1.2, min(3.0, duration * 0.25))


# ───────────── 音效 ─────────────
def sfx_track(beats: list, duration: float, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed + 7)
    n = int(duration * SR)
    out = np.zeros(n)
    prev_kind = None
    for b in beats:
        i = int(max(0, b["start"] - 0.06) * SR)
        if i >= n:
            continue
        kind = b.get("layout", "")
        hit = None
        if kind in ("title",):
            hit = whoosh(0.5, 0.13, rng)
        elif kind in ("bigline", "end"):
            hit = thump(0.6, 58, 0.10, rng)
            if kind == "bigline":
                ping = inkping(0.7, 760, 0.035)
                n2 = max(len(hit), len(ping))
                hit = (np.pad(hit, (0, n2 - len(hit)))
                       + np.pad(ping, (0, n2 - len(ping))))
        elif prev_kind is not None:
            hit = paper(0.26, 0.055, rng) if rng.random() < 0.7 else None
        if hit is not None:
            k = min(len(hit), n - i)
            out[i:i + k] += hit[:k]
        prev_kind = kind
    return out


# ───────────── 旁白 ─────────────
def load_wav(path: Path) -> np.ndarray:
    raw = subprocess.check_output(["ffmpeg", "-v", "error", "-i", str(path),
                                   "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"])
    return np.frombuffer(raw, dtype=np.float32).astype(np.float64)


def narration(manifest: dict, duration: float) -> np.ndarray:
    n = int(duration * SR)
    out = np.zeros(n)
    for line in manifest["lines"]:
        x = load_wav(ROOT / "work" / "trim" / line["file"])
        # 归一化到目标 RMS
        rms = math.sqrt(float((x ** 2).mean()) + 1e-12)
        x = x * (db(VOICE_RMS_DB) / rms)
        peak = float(np.abs(x).max())
        if peak > db(-6):
            x *= db(-6) / peak
        x = fade(x, 0.01, 0.02)
        i = int(line["start"] * SR)
        k = min(len(x), n - i)
        out[i:i + k] += x[:k]
    return out


def duck_env(narr: np.ndarray, depth: float = MUSIC_UNDER) -> np.ndarray:
    """按人声包络给音乐做侧链：人声越响，音乐越低。"""
    win = int(0.12 * SR)
    env = np.abs(narr)
    env = np.convolve(env, np.ones(win) / win, mode="same")
    env = env / (env.max() + 1e-9)
    # 平滑
    env = np.convolve(env, np.ones(int(0.25 * SR)) / int(0.25 * SR), mode="same")
    gain = 1.0 - (1.0 - db(depth)) * np.clip(env * 2.2, 0, 1)
    return gain


def master(x: np.ndarray) -> np.ndarray:
    x = np.tanh(x * 1.05) * 0.98
    peak = float(np.abs(x).max())
    if peak > 0:
        x = x * (db(-1.6) / peak)
    return x


def write_wav(path: Path, x: np.ndarray) -> None:
    y = np.clip(x, -1, 1)
    raw = (y * 32767).astype("<i2").tobytes()
    import wave
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(raw)


def write_srt(cues: list, path: Path) -> None:
    def tc(t: float) -> str:
        h = int(t // 3600); m = int(t % 3600 // 60); s = int(t % 60)
        ms = int(round((t - int(t)) * 1000))
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
    lines = []
    for i, c in enumerate(cues, 1):
        lines.append(f"{i}\n{tc(c['start'])} --> {tc(c['end'])}\n{c['text']}\n")
    path.write_text("\n".join(lines), encoding="utf-8")


def loudnorm(inp: Path, out: Path) -> None:
    """两级 loudnorm 到 -14 LUFS / TP -1.5。"""
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(inp), "-af",
                        "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"],
                       capture_output=True, text=True)
    txt = r.stderr
    js = txt[txt.rfind("{"):txt.rfind("}") + 1]
    m = json.loads(js)
    af = (f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
          f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:"
          "linear=true")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(inp), "-af", af,
                    "-ar", "48000", "-c:a", "aac", "-b:a", "192k", str(out)], check=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--films", default="")
    a = ap.parse_args()
    slugs = [s for s in a.films.split(",") if s] or sorted(
        p.stem.replace("manifest_", "") for p in (ROOT / "work").glob("manifest_*.json"))
    (ROOT / "out").mkdir(exist_ok=True)
    for slug in slugs:
        mf = ROOT / "work" / f"manifest_{slug}.json"
        if not mf.exists():
            print(f"skip {slug}: no manifest")
            continue
        manifest = json.loads(mf.read_text(encoding="utf-8"))
        duration = manifest["duration"]
        seed = SEED_BASE + sum(ord(c) for c in slug)
        key = 220.0 * (2 ** (SEED_BASE % 5 / 12)) if False else 196.0
        print(f"[{slug}] {duration:.1f}s  music...", flush=True)
        mus = music(duration, key, seed)
        sfx = sfx_track(manifest["beats"], duration, seed)
        print(f"[{slug}] narration...", flush=True)
        nar = narration(manifest, duration)
        n = len(nar)
        mus = mus[:n] if len(mus) >= n else np.pad(mus, (0, n - len(mus)))
        sfx = sfx[:n] if len(sfx) >= n else np.pad(sfx, (0, n - len(sfx)))
        gain = duck_env(nar)
        mix = nar + mus * gain * db(-2) + sfx * db(-6)
        mix = master(mix)
        wav = ROOT / "work" / "mix" / f"{slug}.wav"
        wav.parent.mkdir(parents=True, exist_ok=True)
        write_wav(wav, mix)
        cues = json.loads((ROOT / "subs" / f"{slug}.json").read_text(encoding="utf-8"))
        srt = ROOT / "out" / f"{slug}.srt"
        write_srt(cues, srt)
        # mux
        seg = ROOT / "segs" / f"{slug}.mp4"
        if not seg.exists():
            print(f"skip mux {slug}: no segment")
            continue
        tmp_out = ROOT / "out" / f"{slug}_pre.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(seg), "-i", str(wav),
                        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest",
                        "-movflags", "+faststart", str(tmp_out)], check=True)
        out = ROOT / "out" / f"{slug}.mp4"
        loudnorm(tmp_out, out)
        tmp_out.unlink(missing_ok=True)
        print(f"[{slug}] -> {out.name} ({out.stat().st_size/1e6:.1f} MB)", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
