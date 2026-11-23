# Aesthetic Direction, Director's Eye & Collaboration Habits

This reference combines **universal cinematic craft aesthetics** (how an experienced CG director sees light, scale, material, and rhythm) with **observed user preferences and collaboration habits**. Treat aesthetic ideas as guiding judgment, not rigid dogma — always adapt them to each new film's story and mood.

---

## 1. Core Cinematic Aesthetic Philosophy (Director's Eye)

### Scale Creates Emotion (Treat Small Things Like Architecture)
- A small craft object shot from far away reads like a catalog thumbnail; the exact same object shot in tight macro with sculpted light reads like a monument or a landscape.
- Give the hero subject commanding presence in the frame (~45–60% visual weight in macro showcases) unless deliberate emptiness is the core emotional statement.
- Push close enough that **material honesty** shines: microscopic glaze crackles, chisel marks, woven fibers, meniscus curvature on water, brushed metal grain, natural patina oxidation.

### Light as Sculptor, Shadow as Architecture
- Cinema lives in the **shadow side**, not flat uniform brightness. Avoid frontal floodlights that erase depth.
- Use directional raking key lights (`30°–55°` grazing angles) to carve relief and micro-bump, paired with a crisp cool/warm rim strip to separate silhouette from dark backdrops.
- Keep shadows rich and velvety rather than lifting them into muddy gray. Negative space should feel intentional and weighty, not empty by accident.

### Tactile Contrast Across Cuts
- Visual rhythm comes from **physical contrast**, not just color variety. Sequence opposing tactile worlds side-by-side:
  - Wet translucent fluid ↔ dry fibrous paper
  - Hammered specular gold ↔ matte carved wood or stone
  - Rigid geometric symmetry ↔ organic turbulent motion
  - Cool restrained celadon/ink ↔ sudden warm molten sparks
- Break up every shader with multi-scale micro-roughness and subtle color variation — never ship a sterile, uniform "CG plastic" material.

### Restraint Over Spectacle
- Luxury and museum quality come from **knowing what to remove**. Avoid cheap CG crutches: excessive bloom, neon candy saturation, gratuitous floating dust/smoke, fake lens flares, or decorative badges.
- When a frame already has one powerful focal element (a single emerald stone eye on wet dark inkstone, or pure white calligraphy on obsidian black), stop adding decoration.

### Typography as Spatial Architecture
- Treat text as part of the composition, never a disconnected subtitle sticker. Couple type to the frame's geometry (hugging an architectural horizon, aligned cleanly to an axis, breathing gently with lens motion).
- Choose letterforms with cultural and historical weight that resonate with the subject rather than generic default sans-serifs. Always check every character visually on a font specimen sheet before final assembly.
- Let final endcards land in quiet, uncluttered authority — pure backdrop, strong letterform, zero visual noise.

---

## 2. Observed User Taste Inclinations (Flexible Signals)

From past creative reviews, the user consistently gravitates toward:
- **Strong Subject Dominance**: Prefers bold, close-up, high-presence framing over timid centered "coin/icon" framing surrounded by excessive void.
- **Warm, Restrained Craft Authenticity**: Favors tactile, understated museum warmth (silk, aged wood, jade translucency, hand-painted porcelain, delicate lacquer, realistic water/ink optics) over garish saturation or toy-like procedural geometry.
- **Minimalist Purity**: Values clean unified backgrounds and distraction-free endings (explicitly prefers stripping away extraneous smoke wisps or extra stamps/seals on endcards).
- **Hidden Craft & Cultural Easter Eggs**: Enjoys subtle, high-craft storytelling layers (e.g., matching calligraphy dynasties to artifacts, rapid script evolution at the finale, exact beat-locked match-cuts) that reward viewers who pause and rewatch.

**Anti-Patterns to Watch Out For**:
- Stiff, toy-like procedural buildings, figurines, or complex carvings built from basic primitives (switch to museum-grade 2K/4K relief/alpha-cutout textures mounted on real 3D geometry, or pick subjects where 3D physics genuinely excels).
- Blown-out AgX highlights or oversaturated gemstone/ceramic colors.
- Visually disconnected titles floating far away from the subject in empty space.

---

## 3. Collaboration & Execution Habits

- **Diagnose → Visual Options + Cost Tiers → Wait for Approval**: When addressing aesthetic weaknesses or major direction pivots, explain the root cause crisply, render a quick real-frame comparison image, present 2–3 clear options with honest time/quality cost tiers, and **wait for the user's pick** before launching heavy work.
- **Fast QC Sheets Over Throwaway Full Renders**: Validate lookdev, exposure, and framing with fast midpoint contact sheets (1/3 res, `24–32 spp`). Once approved, jump straight to the target master resolution/fps (e.g., native 2K/60fps) instead of wasting hours on a full low-res intermediate.
- **Non-Disruptive Live Edits**: Keep post-assembly decoupled from 3D rendering. When the user requests copy, font, or endcard tweaks while a GPU render is running, update the post-assembly script on disk without stopping the render and show a 1-second static preview frame.
- **Clean Pause & Resume Discipline**: If asked to pause mid-render, stop the task cleanly, verify zero lingering `blender.exe` processes holding VRAM, report exact banked frame counts on disk, and resume seamlessly from the next missing frame on cue.
- **Direct, Visual Communication**: Keep updates concise, show contact sheets and exact `ffprobe` metrics rather than walls of text, and provide publication-ready titles/captions/tags when asked.
