---
name: blender-programmatic-studio
description: >-
  Universal, agent-agnostic workflow for ultra-detailed photorealistic 3D modeling,
  PBR look-dev, real-time game-ready asset production (UE5/Unity/Godot/glTF), and
  cinema rendering driven entirely through headless Blender CLI Python scripts
  (Blender 4.2 LTS through 5.2+ with Cycles GPU OptiX/CUDA/HIP/OneAPI/Metal). Enforces
  spec-first real-world scale, Macro-Meso-Micro 3-tier geometry, anti-plastic PBR
  materials, automated .blend & --game-ready auditing, 3-second 4-view Workbench clay QC,
  1:1 native pixel crop look-dev verification, metallic-safe PBR-to-ORM texture baking,
  automatic LODs & UE5 UCX collision hulls, glTF/FBX/USD export, resumable GPU sequence
  rendering, and final delivery auditing. Use whenever the user asks to model, shade,
  light, bake, export game assets/environments, build clay-to-final breakdowns, or
  render photorealistic architecture, interiors, products, terrain dioramas, or 3D short
  films in Blender via Python scripts.
---

# Blender Programmatic Studio

Produce **ultra-detailed, photorealistic 3D models, game-ready assets/environments (UE5 / Unity / Godot / WebGL), hero stills, and cinema sequences** by driving **Blender 4.2 LTS – 5.2+ + Cycles GPU** entirely via reproducible Python scripts — powered by a mandatory **Build -> Automated Audit -> 4-View Clay QC -> Look-Dev / Bake -> Final Verification** closed loop.

Works identically with **any AI agent** that has shell access (Antigravity, Claude Code, Codex, Cursor, Windsurf, Gemini CLI, OpenCode, or ChatGPT + local terminal) via headless `blender -b --factory-startup --python-exit-code 1 --python ...` — **no Blender MCP required**.

## Reference Map (Load As Needed)

- **Photoreal Modeling & 3-Tier Detailing**: Read [references/photoreal-modeling-architecture.md](./references/photoreal-modeling-architecture.md) *before* writing geometry scripts (spec-first sizing, Macro->Meso->Micro geometry, bevels, behind-glass interiors, hybrid modeling boundary).
- **Physical PBR Materials & Anti-Plastic Cookbook**: Read [references/pbr-materials-and-realism.md](./references/pbr-materials-and-realism.md) *before* creating shaders (multi-scale roughness breakup, AO cavity dirt, physical IOR/albedo ranges).
- **Real-Time Game-Asset & Environment Pipeline**: Read [references/game-asset-and-realtime-pipeline.md](./references/game-asset-and-realtime-pipeline.md) whenever targeting **Unreal Engine 5, Unity, Godot, or Three.js / WebGL** (UV0/Lightmap UV1, metallic-safe PBR->ORM baking, LODs, `UCX_` collision, glTF/FBX/USD export).
- **Cinematography, Lighting & 5 Scene Presets**: Read [references/cinematography-and-lighting-guide.md](./references/cinematography-and-lighting-guide.md) when designing cameras, world splits, blue-hour architecture, or Workbench clay breakdown intros.
- **Blender 4.2–5.2 + Cycles + FFmpeg 8+ Pitfalls**: Read [references/blender-version-pitfalls.md](./references/blender-version-pitfalls.md) before writing compositor, sky, animation, GPU, or FFmpeg code.
- **Aesthetic Direction & 5-Axis Self-Critique Rubric**: Read [references/aesthetic-direction-and-habits.md](./references/aesthetic-direction-and-habits.md) before inspecting QC renders or proposing revisions.
- **Gold-Standard Runnable Examples**:
  - [examples/01_photoreal_architectural_bay.py](./examples/01_photoreal_architectural_bay.py) — Spec-first 3-tier architectural curtain wall + behind-glass interior + blue-hour look-dev.
  - [examples/02_game_hero_prop.py](./examples/02_game_hero_prop.py) — Hard-surface game hero prop (armored industrial crate) using `material_library.py`, ready for ORM baking, LODs, `UCX_` collision & `.glb`/`.fbx` export.
- **Universal Non-Skill Agent Adapter**: Share [adapters/UNIVERSAL_PROMPT.md](./adapters/UNIVERSAL_PROMPT.md) for agents without native `SKILL.md` discovery.

## Tooling Scripts (Zero External Dependencies Inside Blender)

- [scripts/blender_compat.py](./scripts/blender_compat.py) — Cross-version compatibility shim for Blender `4.2 LTS` – `5.2+` (physical sky, compositor, actions, BSDF, EEVEE).
- [scripts/optix_render_utils.py](./scripts/optix_render_utils.py) — Multi-backend Cycles GPU activator (`OPTIX -> CUDA -> HIP -> ONEAPI -> METAL -> CPU`) + Blackman-Harris `1.25px` filter + GPU OIDN (`ACCURATE`).
- [scripts/material_library.py](./scripts/material_library.py) — One-line physical PBR material factory (16 anti-plastic, ORM-bake-safe materials + optional linear tint & top-facing snow dusting).
- [scripts/environment_kit.py](./scripts/environment_kit.py) — 5 weather presets (`blue_hour`, `rainy_night`, `golden_haze`, `snow_dusting`, `overcast_nordic`), bounded volumetric fog, procedural terrain/island mesh generator, and slope/altitude-filtered instanced scatterer.
- [scripts/cinema_rig_kit.py](./scripts/cinema_rig_kit.py) — 5 reusable `--preset` master scenes (`studio_product`, `arch_exterior`, `arch_interior`, `diorama_terrain`, `cinema_macro`), exact aspect framing, and compositor builder.
- [scripts/scene_auditor.py](./scripts/scene_auditor.py) — Deterministic pre-render & `--game-ready` `.blend` auditor (real-world scale, sharp unbeveled boxes, albedo physicality, triangle budget, unit scale, UV maps, unbaked procedural shaders, frustum coverage).
- [scripts/visual_qc_kit.py](./scripts/visual_qc_kit.py) — Zero-dependency (`bpy` + `numpy`) 3-second Workbench 4-view clay contact sheet (`clay_4view`) & Cycles full + `1:1` native pixel crop diagnostic (`cycles_crop`).
- [scripts/game_asset_pipeline.py](./scripts/game_asset_pipeline.py) — Game-asset prep (unit scale, bottom-center pivot, UV0 + Lightmap UV1, Weighted Normals), metallic-safe Cycles PBR->ORM (`R=AO, G=Roughness, B=Metallic`) baker, automatic LOD1/LOD2, UE5 `UCX_` collision hulls, and `.glb`/`.fbx`/`.usdc` exporter.
- [scripts/cleanup_imported_mesh.py](./scripts/cleanup_imported_mesh.py) — Cleanup & game-engine optimizer for external AI-generated or scanned `.glb`/`.fbx`/`.obj` meshes (Tripo3D, `camera-to-blender`, Meshy, photogrammetry): weld/fix normals, height normalization, bottom pivot, target-tri decimation, UVs, LODs, `UCX_`, and re-export.
- [scripts/resumable_seq_renderer.py](./scripts/resumable_seq_renderer.py) — Resumable GPU sequence renderer with PNG `IEND` integrity checks, live ETA, and `--overwrite`.
- [scripts/delivery_audit.py](./scripts/delivery_audit.py) — Final still & MP4 auditor (`ffprobe`, adjacent-frame MAD continuity scan, MP4 storyboard extraction).

---

## Mandatory Dual-Track Closed-Loop Pipeline

### Stage 1: Spec-First Blueprint & Scene Archetype
1. Lock a `SPEC` dictionary in **real-world meters (`1 BU = 1.0 m`)** before writing geometry: overall dimensions, modular grid pitch (for game kits), structural rhythm, camera lens, aspect ratio, and target track (**Cinema/Still** or **Game-Ready Engine Asset**).
2. Scaffold from the matching archetype in [scripts/cinema_rig_kit.py](./scripts/cinema_rig_kit.py) (`studio_product`, `arch_exterior`, `arch_interior`, `diorama_terrain`, or `cinema_macro`).
3. For beat-synced films, extract lossless audio (`ffmpeg -vn -c:a copy`) and lock frame boundaries in `timeline.json`.

### Stage 2: 3-Tier Procedural Geometry (`Macro -> Meso -> Micro`)
1. Organize cleanly into collections (`00_CAMERAS_AND_RIG`, `01_LIGHTING`, `02_ENVIRONMENT`, `03_HERO_ASSET`) using `Env_*` for environment dressing and `Hero_*` for primary assets.
2. **Never ship raw primitives.** Every hero form stacks all 3 tiers:
   - **Macro**: Real-world silhouette, modular grid alignment, grounded plinth/seams (zero floating parts).
   - **Meso**: Real wall/panel thickness, recessed apertures, beveled chamfers (`bmesh.ops.bevel` + `WeightedNormal` for game assets), mullions/frames, behind-glass interior cavities.
   - **Micro**: Panel reveals, hardware/fasteners, surface relief, and instanced environment scatter.
3. For complex organic props/scans, follow the hybrid boundary in [references/game-asset-and-realtime-pipeline.md](./references/game-asset-and-realtime-pipeline.md).

### Stage 3: Automated Audit + 3-Second 4-View Clay QC Gate (Mandatory)
**Never render Cycles or export game assets blind.** Run both checks right after saving `./build/scene.blend`:
```bash
blender -b --factory-startup --python-exit-code 1 --python scripts/scene_auditor.py -- \
  --blend ./build/scene.blend --fail-on-error

blender -b --factory-startup --python-exit-code 1 --python scripts/visual_qc_kit.py -- \
  --blend ./build/scene.blend --mode clay_4view --out ./qc/clay_4view.png
```
Visually inspect `clay_4view.png`. Fix any scale drift, floating geometry, Z-fighting, empty silhouettes, or framing flaws **before** shading or baking.

### Stage 4: Physical PBR Shading, AgX Lighting & Look-Dev QC
1. Build anti-plastic physical PBR materials ([references/pbr-materials-and-realism.md](./references/pbr-materials-and-realism.md)): linear diffuse albedo in `[0.015, 0.85]`, multi-scale `Noise` roughness, `Bump`, `Ambient Occlusion` cavity grime, and realistic `Coat`/`IOR`.
2. Configure `AgX`, directional sculpted lighting (grazing key + rim separation or cross-version `configure_physical_sky()` with `sun.visible_glossy = False` over water), and restrained glare via `setup_cinema_compositor()`.
3. Run the fast Cycles look-dev + `1:1` native pixel crop check:
```bash
blender -b --factory-startup --python-exit-code 1 --python scripts/visual_qc_kit.py -- \
  --blend ./build/scene.blend --mode cycles_crop --out ./qc/cycles_qc.png --res 1024 --samples 32
```
4. Grade `cycles_qc.png` against the 5-Axis Rubric in [references/aesthetic-direction-and-habits.md](./references/aesthetic-direction-and-habits.md). Complete at least **1 targeted refinement pass** if any axis `< 4/5`.

### Stage 5A (Track A — Cinema / Hero Stills): Final GPU Render & Delivery Audit
- Verify `[GPU_ACTIVE] ... device=GPU` in stdout. Render sequences via [scripts/resumable_seq_renderer.py](./scripts/resumable_seq_renderer.py) (always pass `--overwrite` after geometry/shader edits).
- Keep raw renders text-free; composite titles, clay-to-final wipes, and audio separately.
- Encode master MP4 (`-level 5.1` for `1920sq@60`, `-level 5.2` for `2160sq@60`, `CRF 13–14`, `-vf "noise=alls=2:allf=t"` on dark twilight skies) and audit via [scripts/delivery_audit.py](./scripts/delivery_audit.py) (`--mad --storyboard`).

### Stage 5B (Track B — Real-Time Game Assets: UE5 / Unity / Godot / WebGL)
Run [scripts/game_asset_pipeline.py](./scripts/game_asset_pipeline.py) to convert procedural Blender scenes into engine-ready assets with metallic-safe baked PBR + ORM maps, LODs, and UE5 collision hulls, then verify with `scene_auditor.py --game-ready`:
```bash
# Bake procedural PBR -> BaseColor + ORM (R=AO, G=Rough, B=Metal) + Normal, generate LODs & UCX collision, export GLB/FBX
blender -b --factory-startup --python-exit-code 1 --python scripts/game_asset_pipeline.py -- \
  --blend ./build/scene.blend --out-blend ./build/scene_game.blend \
  --asset-name ArchBay --merge-hero --lightmap-uv --weighted-normals \
  --bake --tex-dir ./export/textures --tex-size 2048 --normal-format opengl \
  --lods 0.5,0.2 --collision \
  --export-glb ./export/ArchBay.glb --export-fbx ./export/ArchBay.fbx

# Final automated game-asset QA check (zero FAIL issues allowed)
blender -b --factory-startup --python-exit-code 1 --python scripts/scene_auditor.py -- \
  --blend ./build/scene_game.blend --game-ready --fail-on-error
```
*(Pass `--normal-format directx` when targeting Unreal Engine 5 FBX directly.)*
