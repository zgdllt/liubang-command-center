# -*- coding: utf-8 -*-
"""批量生成手书风素材：提交 ComfyUI（Qwen Image 2.1）→ 轮询 → 下载到 assets/<key>.png。

用法：
  python3 scripts/gen_assets.py --only ink_splash            # 单张试跑
  python3 scripts/gen_assets.py                              # 全部（跳过已存在）
  python3 scripts/gen_assets.py --force --only wash_feet --seeds 7
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import assets  # noqa: E402

COMFY = "http://127.0.0.1:8188"
OUT = ROOT / "assets"
UNET = "qwen_image_2.1_int8_convrot.safetensors"
CLIP = "qwen3vl_8b_int8_convrot.safetensors"
VAE = "qwen_image_2.1_vae_bf16.safetensors"


def graph(key: str, spec: dict) -> dict:
    return {
        "1": {"class_type": "UNETLoader",
              "inputs": {"unet_name": UNET, "weight_dtype": "default"}},
        "2": {"class_type": "CLIPLoader",
              "inputs": {"clip_name": CLIP, "type": "qwen_image"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": VAE}},
        "4": {"class_type": "TextEncodeQwenImage21",
              "inputs": {"clip": ["2", 0], "prompt": spec["prompt"],
                         "negative_prompt": assets.NEG, "resolution": 1024}},
        "5": {"class_type": "EmptyLatentImage",
              "inputs": {"width": spec["w"], "height": spec["h"], "batch_size": 1}},
        "6": {"class_type": "KSampler",
              "inputs": {"model": ["1", 0], "seed": spec["seed"], "steps": 25, "cfg": 1.0,
                         "sampler_name": "euler", "scheduler": "simple", "denoise": 1.0,
                         "positive": ["4", 0], "negative": ["4", 1],
                         "latent_image": ["5", 0]}},
        "7": {"class_type": "VAEDecode", "inputs": {"samples": ["6", 0], "vae": ["3", 0]}},
        "8": {"class_type": "SaveImage",
              "inputs": {"images": ["7", 0], "filename_prefix": f"liubang/{key}"}},
    }


def post(path: str, payload: dict) -> dict:
    req = urllib.request.Request(COMFY + path, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def get(path: str) -> dict:
    with urllib.request.urlopen(COMFY + path, timeout=60) as r:
        return json.load(r)


def wait(pid: str, timeout: float = 600) -> dict:
    t0 = time.time()
    while time.time() - t0 < timeout:
        h = get(f"/history/{pid}")
        if pid in h:
            item = h[pid]
            status = item.get("status", {})
            if status.get("status_str") == "error" or status.get("completed") is False:
                raise RuntimeError(f"job {pid} failed: {json.dumps(status)[:400]}")
            return item
        time.sleep(2)
    raise TimeoutError(pid)


def save(item: dict, key: str) -> Path:
    outs = item.get("outputs", {})
    for node in outs.values():
        for img in node.get("images", []):
            q = urllib.parse.urlencode({"filename": img["filename"],
                                        "subfolder": img.get("subfolder", ""),
                                        "type": img.get("type", "output")})
            with urllib.request.urlopen(f"{COMFY}/view?{q}", timeout=120) as r:
                data = r.read()
            dest = OUT / f"{key}.png"
            dest.write_bytes(data)
            return dest
    raise RuntimeError(f"no image output for {key}: {json.dumps(outs)[:300]}")


import urllib.parse  # noqa: E402


def run_one(key: str, seed: int | None) -> tuple[str, float]:
    spec = dict(assets.A[key])
    if seed is not None:
        spec["seed"] = seed
    t0 = time.time()
    pid = post("/prompt", {"prompt": graph(key, spec), "client_id": uuid.uuid4().hex})["prompt_id"]
    item = wait(pid)
    dest = save(item, key)
    dt = time.time() - t0
    print(f"{key:24s} {dt:6.1f}s -> {dest.name} ({dest.stat().st_size//1024}KB)", flush=True)
    (ROOT / "work").mkdir(exist_ok=True)
    with open(ROOT / "work/gen_log.jsonl", "a") as fh:
        fh.write(json.dumps({"key": key, "seed": spec["seed"], "w": spec["w"], "h": spec["h"],
                             "prompt": spec["prompt"], "pid": pid, "sec": round(dt, 1),
                             "at": time.strftime("%Y-%m-%dT%H:%M:%S")}, ensure_ascii=False) + "\n")
    return key, dt


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    ap.add_argument("--seeds", default="")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    keys = [k for k in a.only.split(",") if k] or list(assets.A)
    seeds = [int(s) for s in a.seeds.split(",") if s] or [None]
    fail = 0
    for key in keys:
        try:
            if not a.force and (OUT / f"{key}.png").exists() and not seeds[0]:
                continue
            run_one(key, seeds[0] if seeds[0] is not None else assets.A[key]["seed"])
        except Exception as exc:  # noqa: BLE001
            fail += 1
            print(f"FAIL {key}: {exc}", file=sys.stderr, flush=True)
    print(f"done, {fail} failures")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
