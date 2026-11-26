# Agent Instructions — Blender Programmatic Studio

When working with Blender modeling, PBR look-dev, game-ready asset creation (UE5/Unity/Godot/glTF), or programmatic Cycles rendering in this repository, **read and follow [SKILL.md](./SKILL.md) first**.

- All Blender CLI scripts MUST run with `blender -b --factory-startup --python-exit-code 1 --python ...`.
- Always pass the mandatory closed-loop gates: `scripts/scene_auditor.py` -> `scripts/visual_qc_kit.py` (`clay_4view` and `cycles_crop`) before final GPU renders or game-engine exports.
- Run `python tests/run_smoke_test.py` after modifying any script or reference document.
