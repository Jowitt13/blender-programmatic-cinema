---
name: blender-programmatic-cinema
description: >-
  End-to-end programmatic 3D short-film production workflow driving Blender 5.2 LTS
  and Cycles OptiX/CUDA GPU entirely via Python scripts. Covers rhythm/audio-driven
  timelines, parametric master rigs, hybrid 3D physics and high-res relief craftsmanship,
  cinematic framing and AgX lighting principles, fast visual QC gates, resumable GPU
  sequence rendering, and decoupled typography/post-assembly. Use whenever the user wants
  to create, direct, or iterate on a script-driven Blender Cycles 3D film, visual essay,
  match-cut montage, product/craft showcase, or macro cinematography piece.
---

# Blender Programmatic Cinema Workflow

Direct and render cinema-grade 3D short films by driving **Blender 5.2 LTS + Cycles GPU** entirely through clean, reproducible Python scripts — paired with visual director judgment and fast decoupled post-assembly.

This workflow is **theme-agnostic and format-agnostic** (`9:16`, `16:9`, `2.39:1`, `1:1`; match-cut montage, slow macro study, product/craft hero reel, architectural light essay, or kinetic visual poetry). Treat every parameter as a creative choice serving the story, not a rigid template.

## Reference Map (Load As Needed)

- **Aesthetic Philosophy & Collaboration Habits**: Read [references/aesthetic-direction-and-habits.md](./references/aesthetic-direction-and-habits.md) before designing visuals, critiquing renders, or proposing revisions.
- **Cinematography, Framing & AgX Lighting Guide**: Read [references/cinematography-and-lighting-guide.md](./references/cinematography-and-lighting-guide.md) when designing camera language, lighting splits, or applying the Horizon-Arch Macro preset.
- **Blender 5.2 + Cycles + FFmpeg Pitfalls**: Read [references/blender52-cycles-pitfalls.md](./references/blender52-cycles-pitfalls.md) before writing geometry, compositor, animation, or FFmpeg scripts.
- **Reusable Scripts**:
  - [scripts/optix_render_utils.py](./scripts/optix_render_utils.py) — Mandatory Cycles OptiX/CUDA GPU activator under `--factory-startup`.
  - [scripts/cinema_rig_kit.py](./scripts/cinema_rig_kit.py) — Configurable master rig builder + optional non-destructive Horizon-Arch Macro optical solver.
  - [scripts/resumable_seq_renderer.py](./scripts/resumable_seq_renderer.py) — Resumable GPU sequence renderer (`native` camera or optional framing preset).

---

## Reusable Production Pipeline (7 Modular Phases)

### Phase 1: Concept, Rhythm & Timeline Blueprint
1. Clarify the film's core visual thesis, target aspect ratio/resolution/fps (e.g., `1440×2560 @ 60fps` or `3840×2160 @ 24/60fps`), and pacing arc.
2. If cutting to music or a reference edit, extract lossless audio first (`ffmpeg -vn -c:a copy`) and lock exact cut boundaries into a canonical `timeline.json` (integer frame ranges, act structure, shot themes, optional titles).
3. Every render, QC sheet, and assembly script reads from `timeline.json` as the single source of truth.

### Phase 2: Parametric Master Rig & World Architecture
1. Generate a reusable `master_rig.blend` (see [scripts/cinema_rig_kit.py](./scripts/cinema_rig_kit.py)) defining shared color management (`AgX`), realistic ray-bounces, physical shutter motion blur, baseline studio lights, and alignment guides.
2. **Decouple camera backdrop from environment reflections** via `ShaderNodeLightPath -> Is Camera Ray` so dark, colored, or minimalist backdrops stay pure while objects still catch realistic studio reflections.
3. Keep scene assets cleanly normalized around world origin so camera language, framing, or aspect ratio can be upgraded globally without rebuilding geometry.

### Phase 3: Hybrid Craftsmanship (Match Technique to Physical Truth)
Choose the modeling approach that gives the highest tactile believability per shot rather than forcing one method everywhere:
- **Pure 3D Simulation & Procedural Shaders**: Best where real optical/physical computation shines — fluids and ink dispersion, thin-film iridescence, liquid ripples, refractive droplets with caustics, volumetric light/fire/embers (with Cycles Compositor `Fog Glow`), mechanical gears, woven lattices, and geometric arrays.
- **High-Res Relief/Cutout Textures + Real 3D Silhouette & Motion**: Best for intricate organic, painterly, woven, engraved, or filigree subjects where raw procedural meshes look toy-like. Combine orthographic 2K/4K textures (albedo + bump/height + alpha cutout) with real 3D beveled geometry, physical relief displacement, roughness variation, and animated 3D hero elements (rotating rings, moving tools/threads, parallax layers).

### Phase 4: Intentional Camera Language & Non-Destructive Framing
Design camera movement and framing to maximize subject authority and emotional rhythm:
- Pick the framing that serves the film: **Horizon-Arch Macro** (edge-to-edge monumental curvature for tactile match-cuts), **Close-Up Turntable/Orbital**, **Slow Push-In Dolly**, or **Architectural Light Study**.
- Prefer **non-destructive framing overrides** at render time (or separate rig presets) when experimenting with framing changes so original `.blend` scenes stay clean and reversible.
- When tightening framing inside an already-lit studio rig, prefer **telephoto focal length + lens shift (`shift_x/y`)** over physically moving the camera into the lighting zone; linearly keyframe subtle breathing zoom (`1.00× → 1.03×`) for organic life and native Cycles motion blur.

### Phase 5: Fast Visual QC Gates (Never Render Blind)
1. Before rendering full sequences, render fast midpoint frames (e.g., 1/3 resolution, `24–32 spp`) across all shots and assemble a contact sheet.
2. Visually inspect EVERY shot and review with the user before committing multi-hour GPU compute. Audit:
   - Subject presence and silhouette clarity.
   - AgX highlight control (no blown whites, no flat plastic midtones, no dark subjects lost into dark backgrounds).
   - Continuity across cuts (alignment, brightness rhythm, color harmony).
3. When diagnosing a visual weakness or proposing major direction changes, generate a real-frame side-by-side comparison sheet, lay out **2–3 concrete options with honest time/quality cost tiers**, and wait for user approval.

### Phase 6: Resumable High-Resolution GPU Sequence Rendering
1. Once lookdev and framing pass fast visual QC, skip throwaway full low-res intermediates and render directly at target delivery resolution/fps.
2. Always render via [scripts/resumable_seq_renderer.py](./scripts/resumable_seq_renderer.py):
   - Explicitly activates Cycles `OPTIX` (or `CUDA` fallback) inside every `--factory-startup` process.
   - Skips existing valid PNGs (`> 10KB`) so pauses, crashes, or partial re-renders lose zero completed frames.
   - Pre-steps physics cleanly when starting mid-timeline.
3. **Clean Pause / Resume**: On user pause request, terminate the render cleanly, verify zero orphaned `blender.exe` processes holding VRAM, report exact banked frame counts, and resume seamlessly on command.

### Phase 7: Decoupled Post-Assembly, Typography & Delivery Audit
1. **Never bake titles or endcards into 3D renders.** Keep raw PNG sequences text-free and composite titles, subtle fades, and audio in a fast (~15–30s) assembly script. This allows live copy, font, and endcard revisions *even while a 3D GPU render is running*, without interrupting it.
2. **Typography Discipline**: Couple text spatially and stylistically to the imagery (matched to era, material, or graphic grid); verify every glyph on a visual specimen sheet before assembly; keep endcards clean and uncluttered.
3. **Mandatory Final Audit**:
   - Encode master MP4 (`libx264`, `yuv420p`, `CRF 14`, `-preset slow`, lossless `-c:a copy`).
   - Run `ffprobe` to verify exact resolution, frame rate, frame count, bitrate, and audio sync.
   - Extract a full-film midpoint contact sheet *directly from the final MP4* (`-fps_mode vfr`), inspect both the contact sheet and final video playback, and deliver with clickable paths.
