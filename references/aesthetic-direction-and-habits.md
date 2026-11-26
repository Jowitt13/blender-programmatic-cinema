# Aesthetic Direction, 5-Axis Self-Critique Rubric & Collaboration Workflow

This guide distills **director-level visual judgment**, a mandatory **5-Axis Self-Critique Rubric** that keeps any AI agent from settling for mediocre first-pass renders, and clean collaboration habits.

---

## 1. Core Cinematic Aesthetic Philosophy (Director's Eye)

- **Scale Creates Emotion**: Push close enough for **material honesty** — beveled chamfers, glass mullions, glaze crackles, chisel marks, damp stone sheen, brushed metal grain, and behind-glass room depth. Give hero subjects commanding presence (`~45%–60%` frame weight) unless deliberate emptiness is the core statement.
- **Light as Sculptor, Shadow as Architecture**: Cinema lives on the shadow side. Use grazing raking key lights (`30°–55°`) to carve relief, cool/warm rim strips to separate dark silhouettes, and rich velvety shadows rather than flat frontal floodlights.
- **Tactile Contrast Across Surfaces & Cuts**: Pair physically opposing textures — wet clearcoat granite against matte concrete, warm behind-glass tungsten against cool blue-hour sky, specular hammered metal against dry wood or paper.
- **Restraint Over Spectacle**: Museum and cinema quality come from knowing what to remove. Avoid candy-neon saturation, excessive bloom, gratuitous floating smoke, fake lens flares, or cluttered watermarks.
- **Typography as Spatial Architecture**: Couple titles spatially to horizon lines or architectural grids; verify every Latin/CJK glyph visually; keep endcards quiet and uncluttered.

---

## 2. Mandatory 5-Axis Visual Self-Critique Rubric

After running [scripts/visual_qc_kit.py](../scripts/visual_qc_kit.py) (`clay_4view` and `cycles_crop`), grade the render honestly from `1–5` on every axis **before** committing final GPU render time. Any axis `< 4` requires a targeted code revision:

| Axis | What to Inspect Visually | Instant Red Flags (Must Fix!) |
| :--- | :--- | :--- |
| **1. Proportion & Silhouette** | `clay_4view` Hero + Front + Side + 3/4 Iso | Floating objects, wrong real-world scale, blocky primitive silhouette, empty skyline/background void |
| **2. Macro-Meso-Micro Detail** | `clay_4view` + `cycles_crop` 1:1 native crops | Razor-sharp 90° edges with no bevels, paper-thin walls, missing mullions/seams/hardware, Z-fighting |
| **3. Material Believability** | `cycles_crop` 1:1 crops + `scene_auditor.py` | Uniform CG plastic sheen, impossible white (`>0.85`) or pure black (`<0.015`) albedo, flat un-broken concrete/stone |
| **4. Lighting & AgX Contrast** | `cycles_crop` full frame + luma telemetry | Flat frontal lighting, `clipped_white > 3%`, muddy lifted shadows, wide-`SUN` white-disc reflection on water |
| **5. Composition & Lens Optics** | Hero camera frame | Hero `< 20%` of frame, converging tilted building verticals (forgot `shift_y`), noisy/smeared denoised mullions |

---

## 3. Anti-"AI Slop" Editorial & Breakdown Motion Graphics

When assembling breakdown reels, case studies, or tutorials alongside 3D footage, strictly reject generic blue-cyan neon gradients, glowing rounded video frames, rainbow pill badges, and top progress bars. Favor a **documentary matte-obsidian aesthetic**:
- Matte warm-charcoal film-grain backdrop (`#0a0a0c`) and full-bleed edge-to-edge footage.
- Restrained 3-tone palette: charcoal ground + brushed metallic silver vertical gradient + muted champagne gold accents.
- Crisp `1–2 px` silver comparison hairlines, thin silver outer + `1 px` dotted inner border cards with active/dimmed focus switching, and clean dedicated subtitle-safe bands.

---

## 4. Director–Agent Collaboration Workflow

- **Diagnose -> Visual Options + Cost Tiers -> Wait for Approval**: When fixing major aesthetic flaws or proposing creative pivots, explain the root cause crisply, render a quick comparison frame, lay out `2–3` concrete options with honest time/quality cost tiers, and wait for user approval before heavy renders.
- **Fast QC Gates Over Throwaway Full Renders**: Validate geometry in 3 seconds (`clay_4view`) and look-dev in ~15 seconds (`cycles_crop`). Once approved, jump straight to target delivery resolution/fps.
- **Non-Disruptive Live Edits**: Keep post-assembly decoupled from 3D rendering so copy, typography, or wipe timing can be revised while GPU renders run.
- **Clean Pause & Resume**: On pause requests, terminate cleanly, confirm zero orphaned `blender` processes hold VRAM, report exact banked frame counts, and resume seamlessly on cue.
- **Evidence-Driven Updates**: Report progress concisely with contact sheets, `1:1` pixel crops, `scene_auditor.py` summaries, and `delivery_audit.py` metrics.
