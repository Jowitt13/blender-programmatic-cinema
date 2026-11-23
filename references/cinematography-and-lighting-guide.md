# Cinematography, Framing & AgX Lighting Guide

Practical lighting and camera principles for programmatic Blender 5.2 + Cycles films. Use the principles freely across any aspect ratio (`9:16`, `16:9`, `2.39:1`, `1:1`) and genre; treat the presets at the bottom as optional starting points, not mandatory rules.

---

## 1. World Lighting & Backdrop Separation

Never let a dark or solid-colored background flatten your object's reflections — and never let bright HDRI studio lighting pollute a clean backdrop.

**Light-Path Split World Pattern**:
- Route `ShaderNodeLightPath -> Is Camera Ray` into a `ShaderNodeMixShader`:
  - **Camera Ray branch**: Pure controllable backdrop color (`#050506` obsidian black, warm charcoal, ivory cyclorama, or deep indigo) at `Strength = 1.0`.
  - **Lighting Ray branch**: Subtle studio ambient fill or soft HDRI environment (`Strength = 0.25–0.6`) so metallic, ceramic, glass, and wet surfaces reflect realistic soft gradients.

---

## 2. Studio Lighting Principles

- **Grazing Key Light (Relief Sculptor)**: Position a soft rectangular `AREA` light off-axis (`30°–55°`) so bumps, carvings, brushstrokes, and weave textures cast micro-shadows across the surface.
- **Edge-Defining Rim Strip**: Use a narrow, elongated `AREA` strip light opposite the key with slight color-temperature contrast (e.g., warm `3800K–4500K` key vs cool `6500K–7500K` rim) to carve a razor-clean silhouette against dark backdrops.
- **Controlled Soft Fill**: Keep fill energy at `15%–25%` of key energy so darks remain dimensional rather than muddy.
- **AgX Exposure Discipline** (`AgX - Medium High Contrast`):
  - Bright white/cream materials (porcelain, paper, silk, jade): pull `scene.view_settings.exposure` down (`-0.35` to `-0.95`) to preserve highlight roll-off and micro-texture.
  - Rich saturated materials (red lacquer, gold leaf, enamel): moderate exposure (`-0.10` to `-0.60`).
  - Dark absorptive materials (patinated bronze, wet slate/inkstone, dark timber, black lacquer): lift exposure (`+0.15` to `+0.40`) or boost rim/specular highlights so fine engraving pops cleanly.

---

## 3. Camera Language: Optical Zoom + Shift vs Physical Dolly

Choose the camera mechanism that matches your cinematic goal:

| Need | Best Technique | Why |
| :--- | :--- | :--- |
| **Tightening framing across pre-lit studio scenes** | Keep camera distance fixed; increase `lens` (telephoto macro `135mm–200mm`) + adjust `shift_x / shift_y` | Avoids moving the camera behind or into studio area lights; keeps flat-field museum geometry and exact cross-cut alignment |
| **Spatial depth & foreground parallax** | Physically dolly/orbit the camera (`location` + `Track To` constraint) with wider-to-normal lens (`35mm–85mm`) | Reveals 3D volume, architectural layers, and dramatic perspective shifts |
| **Subtle living energy on static cuts** | Linearly keyframe `1.00× → 1.03×` focal length breathing across `[frame_start, frame_end]` | Gives every cut quiet forward momentum and triggers native Cycles shutter motion blur (`shutter = 0.50`) |

**DOF Rule of Thumb**: When switching from `85mm` to telephoto macro (`160mm–200mm`), depth of field narrows dramatically — stop `aperture_fstop` down from `f/4.0` to `f/8.0–f/11.0` unless shallow bokeh blur is intentionally desired.

---

## 4. Worked Camera Presets (Optional Starting Points)

### Preset A: Horizon-Arch Macro (`9:16` Match-Cut Monumentality)
Ideal for rapid beat-synced match-cuts of circular, domed, or radially symmetric subjects where tactile presence and zero-jitter continuity matter most:
- Normalize hero radius to `R = 1.0m` at origin; keep base camera at `D = 7.083m` (`sensor_width = 36mm`, `sensor_fit = 'HORIZONTAL'`).
- Use `apply_horizon_macro_framing()` in `scripts/cinema_rig_kit.py`:
  - Telephoto push-in: `2.08× → 2.15×` (`176.8mm → 182.8mm`), `f/8.0`.
  - Solve `shift_y` dynamically via `world_to_camera_view()` so every shot's top rim locks onto `v_apex = 0.518 → 0.528` (`~48%` from top) across both top-down and front cameras.
  - Result: 100% width coverage, ~49% screen area, while the object's core center (`~87%` down) stays visible inside the lower frame.
  - Perch titles tightly above the dome apex (`~115px` breathing gap at 2K) with `+3%` breathing zoom.

### Preset B: Full-Bleed Macro Detail (`16:9` / `2.39:1` / `9:16`)
- Fill 100% of frame edges with textured surface, fluid, or relief; use slow lateral pan or gentle `3°–6°` camera tilt with shallow `f/2.8–f/4.0` DOF to guide the eye across a single hero focal point.

### Preset C: Centered Hero Turntable / Showcase
- Frame hero object at `75%–92%` of short screen dimension (avoid `<70%` unless minimalist isolation is intended), slow `8°–15°` orbital drift or gentle turntable rotation, subtle rim-light sweep.

### Preset D: Architectural / Volumetric Light Study
- Wider cinema focal length (`28mm–50mm`), motivated sun/gobo shafts or subtle volumetric haze (`Principled Volume`, low density `0.005–0.02`, anisotropy `0.6`), slow linear dolly reveal.
