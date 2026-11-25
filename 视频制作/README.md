# 制作说明 · 手书风配套视频

《刘邦的指挥部》七关 + 总述，共 8 支手书（水墨速写）风格配套视频。

## 成片

| 文件 | 内容 | 时长 |
|---|---|---|
| `overview.mp4` | 总述（课程介绍 + 怎么开始实验） | 1:45 |
| `ep00-xijiao.mp4` | 第 0 集 朕正在洗脚 | 2:10 |
| `ep01-hongmen.mp4` | 第 1 集 鸿门宴 | 2:06 |
| `ep02-hanxin.mp4` | 第 2 集 萧何追韩信 | 2:35 |
| `ep03-chenping.mp4` | 第 3 集 陈平受金 | 2:05 |
| `ep04-xiaoyin.mp4` | 第 4 集 张良借箸 | 2:25 |
| `ep05-baideng.mp4` | 第 5 集 白登之围 | 2:17 |
| `ep06-sanjie.mp4` | 第 6 集 吾不如 | 1:56 |

每支片子都带同名 `.srt` 字幕，1080p30、H.264、−14.5 LUFS。

### 字幕规范（`scripts/build.py: split_subs`）

- 先按句末标点（。！？；…）断句，超长再在逗号/顿号/冒号处软断，仍超长才硬断
- 硬断点落在标点前，不切 ASCII 单词（`Claude Code` 不会被劈开）
- 条目不以来分隔标点开头；每条最多两行、每行 14–16 字
- 时长按字重分配（汉字 1、英文词 2、标点 0.4）；过短的条合并，偏快的条把开头前移一点
- 量化校验：`python3 scripts/quant_subs.py`（以标点开头/超短/切英文/阅读速度/行数）

## 结构

`总述` = 课程是什么 + 六个名场面 → 七关怎么玩 → **三步开始实验**（放文件夹 / 开一个能读文件的 AI 对话 / 说「开始」）→ 没有 Claude Code 怎么办 → 你会带走什么。

每一集 = 冷开场画面 → 《史记》原文（竖排卷轴）→ 白话拆解 → 现代坑（AI 团队）→ 金句 → 关卡预告。

## 生产管线

```
scripts/films.py      旁白 + 分镜数据（唯一需要改文案的地方）
scripts/assets.py     手书插画提示词清单
scripts/tts.py        Fish Audio 云端 TTS（s2.1-pro-free，逐句）
scripts/gen_assets.py ComfyUI（Qwen Image 2.1）批量出图
scripts/build.py      时长 → 时间轴 → pages/*.html + subs/*.json
scripts/render.py     Playwright 逐帧截图 → x264 无声片段
scripts/assemble.py   合成配乐/音效 + 旁白混音 + 响度归一 + 封装
```

画面是代码：`pages/<slug>.html` 里 `render(t)` 是时间的纯函数，改一帧重渲即可复现。

## 素材来源

- 插画：本机 SSH 到 GPU 主机，ComfyUI + Qwen Image 2.1（`qwen_image_2.1_int8_convrot`），25 步，种子写在 `work/gen_log.jsonl`。
- 旁白：Fish Audio 云 API，模型 `s2.1-pro-free`，音色取自 fish.audio 发现页公开音色（「影视解说」），参考音频与文本存在 `work/ref/`。
- 配乐/音效：numpy 合成（Karplus-Strong 拨弦 + 低频持续 + 鼓点 + 纸声/墨声），固定种子，无第三方采样。
- 字体：马善政毛笔楷书（Ma Shan Zheng）、志莽行书（Zhi Mang Xing）、霞鹜文楷（LXGW WenKai）、Caveat —— 均为 SIL OFL 授权。

## 注意

- 旁白为机器合成语音；发布时按平台要求标注「AI 配音」。
- 音色来自 Fish Audio 发现页的公开音色，商用/公开传播前请按该平台条款确认授权；如要完全规避，可换自录参考音或自建合成音色重跑 `scripts/tts.py`。
- 插画与人物均为虚构再创作，不对应真实画像；引文以中华书局点校本《史记》为准。
