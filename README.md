# Blender Programmatic Cinema (`blender-programmatic-cinema`)

A cross-agent [AgentSkills](https://agentskills.io) package for directing and rendering cinema-grade 3D short films by driving **Blender 5.2 LTS + Cycles OptiX/CUDA GPU** entirely through reproducible Python scripts.

一套可跨 Agent 复用的 **Blender 5.2 + Cycles 全脚本物理光追短片制作 Skill**，沉淀了完整工作流、电影级摄影与导演审美原则、协作习惯、Blender 5.2 工程避坑指南及开箱即用的 GPU 渲染脚手架。

---

## What's Inside / 目录结构

```text
blender-programmatic-cinema/
├── SKILL.md                                       # Modular 7-phase programmatic Blender cinema workflow
├── references/
│   ├── aesthetic-direction-and-habits.md          # Director aesthetic philosophy + user taste & collaboration habits
│   ├── cinematography-and-lighting-guide.md       # Lighting splits, optical framing principles, AgX exposure, presets
│   └── blender52-cycles-pitfalls.md               # Verified Blender 5.2 LTS + Cycles OptiX + FFmpeg 8 gotchas
└── scripts/
    ├── optix_render_utils.py                      # Mandatory GPU OptiX/CUDA activator under --factory-startup
    ├── cinema_rig_kit.py                          # Configurable master_rig builder + Horizon-Arch Macro optical solver
    └── resumable_seq_renderer.py                  # Resumable 60fps Cycles GPU sequence renderer
```

---

## Install Into Your Agent / 安装方式

Clone this repository directly into your agent's `skills/` directory:

- **Antigravity (Global)**:
  ```bash
  git clone https://github.com/Jowitt13/blender-programmatic-cinema.git ~/.gemini/config/skills/blender-programmatic-cinema
  ```
- **Claude Code (Global)**:
  ```bash
  git clone https://github.com/Jowitt13/blender-programmatic-cinema.git ~/.claude/skills/blender-programmatic-cinema
  ```
- **Codex (Global)**:
  ```bash
  git clone https://github.com/Jowitt13/blender-programmatic-cinema.git ~/.codex/skills/blender-programmatic-cinema
  ```
- **Project-Level / Cursor / Universal `.agents`**:
  ```bash
  git clone https://github.com/Jowitt13/blender-programmatic-cinema.git .agents/skills/blender-programmatic-cinema
  ```

---

## Highlights / 核心亮点

- **Theme & Format Agnostic**: Works for `9:16` vertical shorts, `16:9` / `2.39:1` widescreen films, match-cut montages, macro craft essays, product hero films, or architectural light studies.
- **Director-Grade Aesthetic Principles**: Encodes both cinematic craft judgment (macro monumentality, raking light & shadow sculpting, tactile contrast, typographic tension, restraint) and clean iterative collaboration habits.
- **Battle-Tested Blender 5.2 LTS Engineering**: Solves `--factory-startup` silent CPU fallback, Blender 5.2 `Glare` socket API, 5.x slotted action interpolation, `bmesh` matrix types, AgX exposure calibration, and resumable GPU frame rendering.
- **Decoupled Fast Iteration**: 3D PNG rendering is cleanly separated from post-assembly typography, allowing 20-second copy/font/endcard updates even while GPU rendering runs.
