# 像刘邦一样用 AI：第一堂 Agent 管理课

这是一套可以直接开课的课程包，包含教学设计、讲师手册、学员手册、幻灯片，以及三个可运行的实验站点。

## 5 分钟快速开始

```bash
cd course/agent-management-01
python3 lab/facilitator/hidden_tests.py lab/facilitator/answer_keys/granary_solution.py
python3 lab/team/verify.py --solution lab/facilitator/answer_keys/team_solution
python3 lab/game/referee.py --help
```

三条命令分别验证：萧何粮道的答案、汉营的答案、白登裁判是否可用。

## 发什么给学员

只发 `lab/`。`lab/facilitator/` 是讲师用的隐藏验收、记分板和答案，留在讲师机器上。

```text
lab/
├── solo/          # 实验 A：萧何的粮道（个人）
├── team/          # 实验 B：汉营（4 人）
├── game/          # 实验 C：白登（2–6 人）
└── facilitator/   # 讲师专用：隐藏测试、记分板、答案
```

## 目录

| 文件 | 用途 |
|---|---|
| `课程设计.md` | 课程定位、五幕讲古、三个工具、90 分钟流程、实验设计 |
| `讲师手册.md` | 开课前检查、逐分钟 run-of-show、讲稿要点、应急预案 |
| `学员手册.md` | 一页纸：三个工具、实验规则、复盘问题、作业 |
| `slides.md` | Marp 幻灯片，约 20 页 |
| `lab/` | 三个实验站点 |

## 环境要求

- Python 3.9+，只用标准库，不需要 `pip install`
- 实验 A/B 完全离线
- 实验 C 需要局域网：讲师跑 `referee.py`，学员跑 `client.py`
- 学员的 agent 可以是 Claude Code、Codex CLI、Cursor、或任何能执行 shell 命令的 agent；没有 agent 的学员可以手动玩

## 三条实验路线

| 站点 | 任务 | 时长 | 核心教训 |
|---|---|---|---|
| A 萧何的粮道 | 修好粮草分配器，通过监军验收 | 15 min | 你给 agent 的验收标准，就是它眼里的全部世界 |
| B 汉营 | 4 人各写一个模块，按军令集成 | 20–25 min | 局部绿 ≠ 系统绿；军令是可执行验收 |
| C 白登 | 2–6 人，每人一个 agent，5 轮突围 | 15–20 min | 自信 ≠ 正确；复探有成本；异议通道 |

90 分钟课推荐 A + C；120 分钟课推荐 A + B + C。

## 设计边界

- 这是课堂演示，不是教育实验；现场数据只用于复盘，不宣称因果。
- 史料中的"管理读法"是课程解释，不是史料本身的结论。出处见 `课程设计.md` §11。
- 隐藏测试和答案不要随学员工作区分发；否则实验失去意义。
