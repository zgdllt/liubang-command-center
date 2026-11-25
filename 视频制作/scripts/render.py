# -*- coding: utf-8 -*-
"""把 pages/<slug>.html 逐帧截成无声视频 segs/<slug>.mp4（30fps, 1080p）。

用法：
  uv run -q --no-project --with playwright python scripts/render.py --film overview
  ... --film overview --start 0 --end 20 --out /tmp/test.mp4   # 试片段
"""
from __future__ import annotations

import argparse
import functools
import http.server
import socket
import socketserver
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PORT = 8765


class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


def serve() -> socketserver.TCPServer:
    global PORT
    handler = functools.partial(Handler, directory=str(ROOT))
    socketserver.ThreadingTCPServer.allow_reuse_address = True
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    PORT = s.getsockname()[1]
    s.close()
    httpd = socketserver.ThreadingTCPServer(("127.0.0.1", PORT), handler)
    httpd.daemon_threads = True
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--film", required=True)
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--out", default="")
    ap.add_argument("--start", type=float, default=0)
    ap.add_argument("--end", type=float, default=0)
    ap.add_argument("--q", type=int, default=90)
    a = ap.parse_args()

    sys.path.insert(0, str(ROOT / "scripts"))
    import json
    data = json.loads((ROOT / "work" / f"manifest_{a.film}.json").read_text(encoding="utf-8"))
    duration = data["duration"]
    start = a.start
    end = a.end or duration
    n = int(round((end - start) * a.fps))
    frames_dir = ROOT / "work" / "frames" / a.film
    frames_dir.mkdir(parents=True, exist_ok=True)
    out = Path(a.out) if a.out else ROOT / "segs" / f"{a.film}.mp4"
    out.parent.mkdir(parents=True, exist_ok=True)

    httpd = serve()
    from playwright.sync_api import sync_playwright
    url = f"http://127.0.0.1:{PORT}/pages/{a.film}.html?record"
    t0 = time.time()
    with sync_playwright() as pw:
        browser = pw.chromium.launch(args=["--force-color-profile=srgb",
                                           "--font-render-hinting=none",
                                           "--disable-lcd-text"])
        page = browser.new_page(viewport={"width": 1920, "height": 1080}, device_scale_factor=1)
        page.goto(url, wait_until="load")
        page.wait_for_function("window.__ready === true", timeout=120000)
        cues = json.loads((ROOT / "subs" / f"{a.film}.json").read_text(encoding="utf-8"))
        page.evaluate("([c, r]) => window.__setSubs(c, r)", [cues, 1e9])
        page.evaluate(f"() => window.__DURATION")
        shot = page.screenshot
        for i in range(n):
            t = start + i / a.fps
            page.evaluate("(t) => window.__seek(t)", t)
            shot(path=str(frames_dir / f"{i:05d}.jpg"), type="jpeg", quality=a.q)
            if i % 300 == 0:
                print(f"  {a.film} {i}/{n}  {time.time()-t0:.0f}s", flush=True)
        browser.close()
    httpd.shutdown()
    print(f"capture {a.film}: {n} frames in {time.time()-t0:.0f}s", flush=True)

    subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(a.fps),
                    "-i", str(frames_dir / "%05d.jpg"),
                    "-c:v", "libx264", "-preset", "medium", "-crf", "18",
                    "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out)], check=True)
    for p in frames_dir.glob("*.jpg"):
        p.unlink()
    print(f"wrote {out}  ({out.stat().st_size/1e6:.1f} MB)", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
