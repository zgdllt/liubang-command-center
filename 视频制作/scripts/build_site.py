# -*- coding: utf-8 -*-
"""生成 GitHub Pages 站点：media/（成片+VTT+封面+字体）+ index.html + .nojekyll。

用法（从仓库根目录）：
  python3 视频制作/scripts/build_site.py
"""
from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]          # 仓库根
REPO = "https://github.com/zgdllt/liubang-command-center"
FILMS = ROOT / "视频" / "成片"
MEDIA = ROOT / "media"
FONTS = ROOT / "视频制作" / "fonts"

FILM_LIST = [
    ("overview", "总述 · 七关，一场实验", "1:45", "课程介绍 + 七关玩法 + 三步开始实验"),
    ("ep00", "第 0 集 · 朕正在洗脚", "2:10", "一个看大门的老头，当众把老板骂服了"),
    ("ep01", "第 1 集 · 他一晚上只说了三句话", "2:07", "一场必死的饭局，他靠问对人活着出来了"),
    ("ep02", "第 2 集 · 拜将之前，先问对策", "2:35", "不看履历看对策；拜将之前先问计划"),
    ("ep03", "第 3 集 · 要一把刀，不要一尊像", "2:05", "没有完人，只有配置"),
    ("ep04", "第 4 集 · 印都刻好了", "2:25", "能销的印才是印，销不了的印是债"),
    ("ep05", "第 5 集 · 说「别去」的人", "2:17", "多数不是证据"),
    ("ep06", "第 6 集 · 你的产出是别人做成的事", "1:56", "陛下不能将兵，而善将将"),
]

SRC = {
    "overview": FILMS / "overview.mp4",
    "ep00": FILMS / "ep00-xijiao.mp4",
    "ep01": FILMS / "ep01-hongmen.mp4",
    "ep02": FILMS / "ep02-hanxin.mp4",
    "ep03": FILMS / "ep03-chenping.mp4",
    "ep04": FILMS / "ep04-xiaoyin.mp4",
    "ep05": FILMS / "ep05-baideng.mp4",
    "ep06": FILMS / "ep06-sanjie.mp4",
}

LEVELS = [
    ("0", "朕正在洗脚", "别人的反对意见，哪一条值得听", "10–15 分钟"),
    ("1", "鸿门宴彩排", "你写的指令，决定它在饭局上死不死", "15–20 分钟"),
    ("2", "盲选拜将", "挑人别看他多强，看他怎么说「我没把握」", "20–25 分钟"),
    ("3", "汉营招聘会", "缺点不是问题，放错岗位才是", "15–20 分钟"),
    ("4", "销印大会", "在「印刻好」之前，找个人专门说「不对」", "20 分钟"),
    ("5", "白登五探", "自信不等于正确，复探要花钱", "15 分钟"),
    ("6", "汉营编制表", "你的产出，是别人做成的事", "25–30 分钟"),
]


def srt_to_vtt(srt: Path, vtt: Path) -> None:
    text = srt.read_text(encoding="utf-8").strip()
    text = re.sub(r"(\d\d:\d\d:\d\d),(\d\d\d)", r"\1.\2", text)
    vtt.write_text("WEBVTT\n\n" + text + "\n", encoding="utf-8")


def sync_media() -> None:
    MEDIA.mkdir(exist_ok=True)
    (MEDIA / "covers").mkdir(exist_ok=True)
    (MEDIA / "subs").mkdir(exist_ok=True)
    (MEDIA / "fonts").mkdir(exist_ok=True)
    for slug, src in SRC.items():
        dst = MEDIA / f"{slug}.mp4"
        if not dst.exists() or dst.stat().st_mtime < src.stat().st_mtime:
            shutil.copy2(src, dst)
        srt = src.with_suffix(".srt")
        if srt.exists():
            srt_to_vtt(srt, MEDIA / "subs" / f"{slug}.vtt")
    for jpg in (FILMS / "covers").glob("*.jpg"):
        shutil.copy2(jpg, MEDIA / "covers" / jpg.name)
    shutil.copy2(FONTS / "mashanzheng.ttf", MEDIA / "fonts" / "mashanzheng.ttf")


CSS = """
:root{--ink:#1d1a16;--ink2:#3b352d;--ink3:#6a6155;--paper:#efe6d3;--paper2:#e7dbc2;
--red:#b03a2b;--red2:#c9553f;--gold:#8f7238}
*{margin:0;padding:0;box-sizing:border-box}
@font-face{font-family:'Brush';src:url('media/fonts/mashanzheng.ttf') format('truetype');font-display:swap}
body{background:var(--paper);color:var(--ink);font-family:"Kaiti SC","KaiTi","STKaiti","LXGW WenKai",serif;
line-height:1.75;-webkit-font-smoothing:antialiased}
body:before{content:"";position:fixed;inset:0;pointer-events:none;z-index:0;opacity:.5;mix-blend-mode:multiply;
background-image:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='240' height='240'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='3'/><feColorMatrix type='saturate' values='0'/></filter><rect width='240' height='240' filter='url(%23n)' opacity='0.14'/></svg>")}
.wrap{position:relative;z-index:1;max-width:1120px;margin:0 auto;padding:0 24px 80px}
header{padding:64px 0 24px;display:flex;align-items:flex-start;gap:28px;flex-wrap:wrap}
.seal{flex:none;width:86px;height:86px;background:var(--red);color:#f7efe0;font-family:'Brush',serif;
font-size:26px;line-height:1.15;display:flex;align-items:center;justify-content:center;text-align:center;
transform:rotate(-3deg);box-shadow:3px 4px 0 rgba(120,40,25,.18)}
h1{font-family:'Brush',serif;font-size:64px;font-weight:400;line-height:1.15;letter-spacing:.02em}
.tagline{margin-top:12px;color:var(--ink2);font-size:19px}
.kicker{color:var(--red);letter-spacing:.3em;font-size:14px;border-left:3px solid var(--red);padding-left:12px}
h2{font-family:'Brush',serif;font-size:36px;font-weight:400;margin:64px 0 8px}
h2 .n{color:var(--red);font-size:22px;margin-right:12px;font-family:inherit}
.lead{color:var(--ink3);margin-bottom:24px;font-size:17px}
.player{background:#f8f2e3;border:1px solid rgba(120,96,62,.3);padding:14px;box-shadow:0 18px 44px rgba(60,42,20,.18)}
.player video{width:100%;display:block;background:#000}
.player .cap{display:flex;justify-content:space-between;gap:16px;padding:12px 6px 2px;font-size:15px;color:var(--ink3);flex-wrap:wrap}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:20px;margin-top:8px}
.card{background:#f8f2e3;border:1px solid rgba(120,96,62,.3);cursor:pointer;transition:transform .15s,box-shadow .15s;
box-shadow:0 8px 20px rgba(60,42,20,.12);display:flex;flex-direction:column}
.card:hover{transform:translateY(-3px);box-shadow:0 16px 32px rgba(60,42,20,.2)}
.card img{width:100%;aspect-ratio:16/9;object-fit:cover;display:block;border-bottom:1px solid rgba(120,96,62,.2)}
.card .meta{padding:12px 14px 16px}
.card .t{font-family:'Brush',serif;font-size:22px;line-height:1.3}
.card .d{font-size:14px;color:var(--ink3);margin-top:4px}
.card .dur{font-size:13px;color:var(--red);margin-top:8px;letter-spacing:.08em}
.steps{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:18px;margin-top:20px}
.step{background:linear-gradient(175deg,#faf4e5,#efe4cb);border:1px solid rgba(120,96,62,.3);padding:22px 20px}
.step .n{width:44px;height:44px;border:2px solid var(--red);color:var(--red);border-radius:50%;
display:flex;align-items:center;justify-content:center;font-family:'Brush',serif;font-size:22px;margin-bottom:12px}
.step h3{font-size:19px;font-weight:600;margin-bottom:6px}
.step p{font-size:15px;color:var(--ink3)}
pre.cmd{position:relative;margin-top:18px;background:#201c17;color:#f4ecdc;padding:20px 22px;font-family:ui-monospace,Menlo,monospace;
font-size:17px;line-height:1.7;overflow:auto;border-left:4px solid var(--red)}
pre.cmd button{position:absolute;right:10px;top:10px;background:transparent;color:#d8c9ad;border:1px solid #6b5c44;
padding:4px 10px;font-size:12px;cursor:pointer;font-family:inherit}
pre.cmd button:hover{color:#fff;border-color:#a08b68}
table{width:100%;border-collapse:collapse;margin-top:18px;font-size:16px}
th,td{text-align:left;padding:12px 10px;border-bottom:1px solid rgba(120,96,62,.25)}
th{font-weight:600;color:var(--ink2);font-size:14px;letter-spacing:.14em}
td .no{color:var(--red);font-family:'Brush',serif;font-size:20px;margin-right:6px}
a{color:var(--red);text-decoration:none;border-bottom:1px solid rgba(176,58,43,.35)}
a:hover{border-bottom-color:var(--red)}
.links{display:flex;flex-wrap:wrap;gap:10px 26px;font-size:16px;margin-top:12px}
footer{margin-top:72px;padding-top:24px;border-top:1px solid rgba(120,96,62,.3);color:var(--ink3);font-size:14px}
footer p{margin:6px 0}
.now{display:inline-block;background:var(--red);color:#f7efe0;font-size:12px;letter-spacing:.2em;padding:3px 8px;margin-left:10px;vertical-align:middle}
@media (max-width:640px){
h1{font-size:42px}h2{font-size:30px}header{padding-top:32px;gap:16px}
.seal{width:58px;height:58px;font-size:18px}
.tagline{font-size:17px}.player{padding:8px}
td,th{padding:10px 6px;font-size:15px}
}
"""

JS = """
const srcs={overview:'media/overview.mp4',ep00:'media/ep00.mp4',ep01:'media/ep01.mp4',ep02:'media/ep02.mp4',
ep03:'media/ep03.mp4',ep04:'media/ep04.mp4',ep05:'media/ep05.mp4',ep06:'media/ep06.mp4'};
const titles={overview:'总述 · 七关，一场实验',ep00:'第 0 集 · 朕正在洗脚',ep01:'第 1 集 · 他一晚上只说了三句话',
ep02:'第 2 集 · 拜将之前，先问对策',ep03:'第 3 集 · 要一把刀，不要一尊像',ep04:'第 4 集 · 印都刻好了',
ep05:'第 5 集 · 说「别去」的人',ep06:'第 6 集 · 你的产出是别人做成的事'};
const v=document.getElementById('player'),cap=document.getElementById('cap'),tb=document.getElementById('track');
function play(slug){
  v.src=srcs[slug]; tb.src='media/subs/'+slug+'.vtt';
  cap.textContent=titles[slug];
  document.getElementById('playerbox').scrollIntoView({behavior:'smooth',block:'center'});
  v.play().catch(()=>{});
}
document.querySelectorAll('.card').forEach(c=>c.addEventListener('click',()=>play(c.dataset.slug)));
document.getElementById('copy').addEventListener('click',async()=>{
  try{await navigator.clipboard.writeText('开始');document.getElementById('copy').textContent='已复制';}
  catch(e){document.getElementById('copy').textContent='请手动输入';}
});
"""


def build_html() -> str:
    cards = "\n".join(
        f"""      <article class="card" data-slug="{slug}">
        <img src="media/covers/{cover}" alt="{title}" loading="lazy">
        <div class="meta">
          <div class="t">{title}</div>
          <div class="d">{desc}</div>
          <div class="dur">时长 {dur} · 点击播放</div>
        </div>
      </article>"""
        for slug, title, dur, desc, cover in [
            (s, t, d, desc, ("overview.jpg" if s == "overview" else
                             [p.name for p in (FILMS / "covers").glob("*.jpg") if p.name.startswith(s)][0]))
            for s, t, d, desc in FILM_LIST
        ]
    )
    levels = "\n".join(
        f"""        <tr><td><span class="no">{no}</span>{name}</td><td>{what}</td><td>{dur}</td></tr>"""
        for no, name, what, dur in LEVELS
    )
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>刘邦的指挥部 · 用《史记》学带团队</title>
<meta name="description" content="七个关卡，七个《史记》名场面。你扮演刘邦，你的张良、萧何、韩信都是 AI——不用发工资，但会一本正经地骗你。">
<style>{CSS}</style>
</head>
<body>
<div class="wrap">
  <header>
    <div class="seal">汉营</div>
    <div>
      <div class="kicker">七关 · 一门用《史记》学带团队的课</div>
      <h1>刘邦的指挥部</h1>
      <p class="tagline">你扮演刘邦，你的张良、萧何、韩信都是 AI——不用发工资，但会一本正经地骗你。<br>
      七个关卡，七个《史记》名场面。不写代码，说话就行。</p>
    </div>
  </header>

  <h2><span class="n">壹</span>先看总述</h2>
  <p class="lead">1 分 45 秒，讲清三件事：这门课是什么、七关怎么玩、<strong>怎么开始实验</strong>。</p>
  <div class="player" id="playerbox">
    <video id="player" controls preload="metadata" poster="media/covers/overview.jpg" playsinline>
      <source src="media/overview.mp4" type="video/mp4">
      <track id="track" kind="subtitles" srclang="zh" label="中文字幕（可选）" src="media/subs/overview.vtt">
    </video>
    <div class="cap"><span id="cap">总述 · 七关，一场实验</span><span>1080p · 中文字幕 · AI 配音</span></div>
  </div>

  <h2><span class="n">贰</span>七个关卡</h2>
  <p class="lead">一关十分钟到半小时。只考一个判断，不叠加。可以只打一关，也可以七关连打。</p>
  <table>
    <thead><tr><th>关卡</th><th>打完你会知道</th><th>时长</th></tr></thead>
    <tbody>
{levels}
    </tbody>
  </table>

  <h2><span class="n">叁</span>七集配套视频</h2>
  <p class="lead">每集两分钟左右，正好在开打前热场。点封面就在上面播放器里放。</p>
  <div class="grid">
{cards}
  </div>

  <h2><span class="n">肆</span>怎么开始实验</h2>
  <div class="steps">
    <div class="step"><div class="n">一</div><h3>拿到这个文件夹</h3><p>课程包解压到本地，随便哪一层目录都行。</p></div>
    <div class="step"><div class="n">二</div><h3>在里面开一个能读文件的 AI 对话</h3><p>Claude Code、Cursor，任何能读文件的都行。</p></div>
    <div class="step"><div class="n">三</div><h3>说两个字：开始</h3><p>军师会出现，报出七关，然后等你说关号。</p></div>
  </div>
  <pre class="cmd">开始<button id="copy">复制</button></pre>
  <p class="lead" style="margin-top:18px">没有 Claude Code 也行：把 <code>任务/00-洗脚.md</code> 整份贴进任意聊天窗口，卡片下半部分就是给它的指令。</p>

  <h2><span class="n">伍</span>课程文件</h2>
  <div class="links">
    <a href="{REPO}/blob/main/课程总览.md">课程总览</a>
    <a href="{REPO}/tree/main/任务">七关卡片</a>
    <a href="{REPO}/tree/main/讲师">讲师手册与答案</a>
    <a href="{REPO}/tree/main/视频">视频脚本</a>
    <a href="{REPO}/blob/main/视频制作/README.md">制作说明</a>
    <a href="{REPO}">GitHub 仓库</a>
  </div>

  <footer>
    <p>画面、脚本、配乐均由 <code>视频制作/</code> 里的代码生成；插画由 Qwen Image 2.1 生成，旁白为 Fish Audio 合成语音（模型 s2.1-pro-free，音色取自其发现页），字体为 SIL OFL 授权的马善政毛笔楷书。</p>
    <p>人物与场景均为虚构再创作，引文以中华书局点校本《史记》为准。发布视频时请按平台要求标注「AI 配音」。</p>
    <p>汉营指挥部 · <span class="now">七关</span></p>
  </footer>
</div>
<script>{JS}</script>
</body>
</html>
"""


def main() -> None:
    sync_media()
    html = build_html()
    (ROOT / "index.html").write_text(html, encoding="utf-8")
    (ROOT / ".nojekyll").write_text("", encoding="utf-8")
    print("wrote index.html", len(html), "bytes")
    print("media", sum(p.stat().st_size for p in MEDIA.rglob("*") if p.is_file()) // 1024 // 1024, "MB")


if __name__ == "__main__":
    main()
