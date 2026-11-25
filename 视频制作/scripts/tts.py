# -*- coding: utf-8 -*-
"""把 films.py 的旁白逐句合成（Fish Audio 云 API, s2.1-pro-free）。

用法：
  FISH_API_KEY=... python3 scripts/tts.py [--films slug1,slug2] [--workers 2]

产物：vo/<slug>/<line-id>.wav（跳过已存在），以及 work/lines_<slug>.json。
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import films  # noqa: E402

SKILL = Path.home() / ".agents/skills/synthesizing-voiceovers/scripts/fish_cloud_tts.py"
MODEL = "s2.1-pro-free"
REF_AUDIO = ROOT / "work/ref/ref_yingshi.wav"
# 只给 TTS 看的读音纠正：字幕仍用原字
PRON = {
    "郦食其": "郦义基",   # lì yì jī
    "郦生": "郦生",
}
REF_TEXT = ("说实话，现在的网剧质量真是越来越差了。编剧为了省事，剧情全是复制粘贴，"
            "男主角非富即贵，女主角不是傻白甜就是霸道总裁。最离谱的是，三集不到就给你"
            "塞进去十几个品牌广告，观众的体验完全不顾了。")


def load_tts():
    spec = importlib.util.spec_from_file_location("fish_cloud_tts", SKILL)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def lines_of(slug: str) -> list[dict]:
    f = films.FILMS[slug]
    out = []
    for bi, beat in enumerate(f["beats"]):
        for li, text in enumerate(beat["lines"]):
            out.append({"file": f"b{bi:02d}l{li:02d}.wav", "text": text,
                        "beat": bi, "text_index": li})
    return out


def run(slug: str, workers: int, force: bool) -> int:
    tts = load_tts()
    key = os.environ.get("FISH_API_KEY", "").strip()
    if not key:
        print("FISH_API_KEY missing", file=sys.stderr)
        return 2
    ref = {"audio": REF_AUDIO.read_bytes(), "text": REF_TEXT}
    items = lines_of(slug)
    outdir = ROOT / "vo" / slug
    outdir.mkdir(parents=True, exist_ok=True)
    (ROOT / "work").mkdir(exist_ok=True)
    (ROOT / "work" / f"lines_{slug}.json").write_text(
        json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")

    # 记下每个文件对应的文本：文案改过的句子必须重录，不能沿用旧音频
    mapfile = outdir / "texts.json"
    old_map = json.loads(mapfile.read_text(encoding="utf-8")) if mapfile.exists() else {}
    todo = [it for it in items
            if force
            or not (outdir / it["file"]).exists()
            or old_map.get(it["file"]) != it["text"]]
    if todo:
        print("  retake:", ", ".join(it["file"] for it in todo[:8]), flush=True)
    print(f"[{slug}] {len(items)} lines, {len(todo)} to synthesize", flush=True)

    def one(it):
        for attempt in range(5):
            try:
                say = it["text"]
                for k, v in PRON.items():
                    say = say.replace(k, v)
                audio = tts.synthesize(say, key, MODEL, ref, 0.7, 0.7, 180, retries=2)
                (outdir / it["file"]).write_bytes(audio)
                cur_map = json.loads(mapfile.read_text(encoding="utf-8")) if mapfile.exists() else {}
                cur_map[it["file"]] = it["text"]
                mapfile.write_text(json.dumps(cur_map, ensure_ascii=False, indent=1), encoding="utf-8")
                print(f"  ok {slug}/{it['file']} {len(audio)//1024}KB", flush=True)
                return None
            except Exception as exc:  # noqa: BLE001
                wait = 4 * (attempt + 1)
                print(f"  retry {slug}/{it['file']} in {wait}s: {exc}", flush=True)
                time.sleep(wait)
        return f"{slug}/{it['file']} failed"

    fails = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for res in pool.map(one, todo):
            if res:
                fails.append(res)
    if fails:
        print("FAILED:\n" + "\n".join(fails), file=sys.stderr)
        return 1
    print(f"[{slug}] done", flush=True)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--films", default="")
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    slugs = [s for s in a.films.split(",") if s] or list(films.FILMS)
    rc = 0
    for slug in slugs:
        try:
            rc |= run(slug, a.workers, a.force)
        except Exception:  # noqa: BLE001
            traceback.print_exc()
            rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main())
