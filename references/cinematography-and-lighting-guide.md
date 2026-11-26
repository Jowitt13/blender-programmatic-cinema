# Cinematography, Framing & AgX Lighting Guide

Practical lighting, optics, look-dev, and breakdown principles for programmatic Blender `4.2–5.2+` + Cycles scenes. Works across any aspect ratio (`9:16`, `16:9`, `2.39:1`, `1:1`) and across both photorealistic hero stills and animated cinema sequences.

---

## 1. Five Reusable Scene Lighting Archetypes (`cinema_rig_kit.py --preset`)

Choose the preset matching your subject (implemented in [scripts/cinema_rig_kit.py](../scripts/cinema_rig_kit.py)):

| Preset | Best For | Lighting & World Architecture | Default Optics |
| :--- | :--- | :--- | :--- |
| **`studio_product`** | Watches, gadgets, ceramics, jewelry, industrial craft | `LightPath -> Is Camera Ray` split world (pure `#050506` or warm-charcoal camera backdrop + `0.40` studio env reflection); off-axis grazing key softbox (`3800–4500K`), cool rim strip (`6500–7500K`), `15–25%` soft fill | `85mm` 3/4 hero (`f/5.6`), `Cam_Front`, `Cam_TopDown` |
| **`arch_exterior`** | Skyscrapers, villas, bridges, blue-hour & golden-hour cities | Physical `NISHITA` sky (`sun_elevation = 2.5°–6°`, `sun_disc = False`) + warm grazing `SUN` with `visible_glossy = False` (no artificial white disc on water!) + damp clearcoat granite plaza | `35mm` perspective (`shift_y = +0.06`, `f/8.0`) + `135mm` telephoto detail (`f/2.8`) |
| **`arch_interior`** | Rooms, galleries, cafes, sunlit architectural spaces | Physical `NISHITA` sky + directional raking window `SUN` (`1.5°` soft shadow angle) + rectangular window `AREA` portal light | `28mm` architectural eye-level (`rot_x = 90°`, vertical lines strictly parallel) |
| **`diorama_terrain`** | Aerial island maps, urban masterplans, miniature landscapes | Crisp directional `NISHITA` sky (`24°–32°` elevation) + warm key `SUN` (`visible_glossy = False`) for sharp topographic relief shadows | `85mm` elevated 3/4 telephoto (`f/5.6`, subtle miniature DOF) |
| **`cinema_macro`** | Beat-synced match-cut reels & radial craft macro studies | Calibrated `R = 1.0m` origin rig with split world & non-rendering XY/XZ alignment circles; pairs with `apply_horizon_macro_framing()` | `85mm` base (`D = 7.083m`), `176–183mm` telephoto macro (`f/8.0`) |

---

## 2. AgX Exposure Discipline (`AgX - Medium High Contrast`)

Never compensate for dark shadows by flooding the whole scene with flat light; adjust `scene.view_settings.exposure` per dominant material luminance:
- **Bright white / porcelain / paper / silk**: `-0.35` to `-0.95 EV` to preserve highlight roll-off and micro-texture.
- **Rich saturated lacquer / gold / blue-hour twilight**: `-0.10` to `-0.50 EV`.
- **Dark absorptive bronze / wet slate / charcoal timber**: `+0.15` to `+0.40 EV` or increase cool rim strip specular energy.

---

## 3. Camera Language & Aspect-Ratio Conversion

| Storytelling Need | Best Technique | Why |
| :--- | :--- | :--- |
| **Tightening framing inside pre-lit studio rigs** | Keep camera fixed; increase `lens` (`135–200mm`) + adjust `shift_x / shift_y` | Avoids pushing camera into studio softboxes; preserves museum flat-field alignment |
| **Architectural vertical perfection** | Keep camera pitch horizontal (`rot_x = 90°`) and frame tall facades via `shift_y` (`+0.05` to `+0.18`) | Prevents converging "falling backward" vertical lines on buildings and interiors |
| **Spatial depth & parallax** | Physically dolly/orbit (`location` + `Track To`) with `28–50mm` lenses | Reveals true 3D volume, foreground/midground/background parallax |
| **Subtle living energy on animated cuts** | Linearly keyframe `1.00x -> 1.03x` focal-length breathing across `[frame_start, frame_end]` | Gives every cut quiet forward momentum and native Cycles shutter motion blur (`0.35–0.50`) |
| **Converting `16:9` -> `1:1` safely** | Call `configure_aspect_framing()` in [scripts/cinema_rig_kit.py](../scripts/cinema_rig_kit.py) | Keeps `1920x1920` density on `horizontal_expand`, or exact `20.25mm` `sensor_height` on `vertical_crop` |

**DOF Rule of Thumb**: Moving from `50mm` to telephoto (`135–200mm`) dramatically compresses depth of field — stop down to `f/8.0–f/11.0` for sharp technical/macro subjects, or open to `f/2.8` (7 blades) when intentionally melting a distant `1+ km` city skyline into creamy circular bokeh.

---

## 4. Blue-Hour Architectural & Twilight Cinema Look-Dev

- **Behind-Glass True Interior ("真内透")**: Place LED strips, rooms, and warm interior desks slightly inside curtain-wall glass (`normal_offset = -0.10 to -0.24 m`) so mullions, reflection Fresnel, and room depth read physically.
- **Coastal Evening Dampness Clearcoat**: Modulate `Coat Weight` (`0.08–0.45`) with multi-scale object-space `Noise` + low `Coat Roughness` (`0.05–0.09`) on granite plazas and wet roads so Cycles casts rich facade reflections without turning stone into flat mirrors.
- **Dual-Stage Optical Glare + Cool/Warm Film Split**: Call `setup_cinema_compositor()` in [scripts/cinema_rig_kit.py](../scripts/cinema_rig_kit.py) to pair `High` photographic `Bloom` / `Fog Glow` with a high-threshold (`3.5–4.0`), restrained `Streaks` pass (`Strength 0.18–0.25`, `4` streaks at `15°`, `Fade 0.84`) plus subtle cool-shadow / warm-highlight `ColorBalance`.

---

## 5. Dual-Engine Breakdown Intros (Workbench Clay -> Cycles / EEVEE)

- **Orbital Pop-In -> 1-Frame Hard Cut**: Run `0.00–2.50 s` in Workbench (`STUDIO + RANDOM + Outline + BOTH Cavity`), splitting large batched meshes (city skylines, trees, props) into multi-color buckets and swapping transparent glass shells or alpha-card foliage for solid clay proxies; hard-cut to Cycles on the exact same `C¹/C²` camera curve.
- **Multi-Pass Purely Vertical Borderless Seamless Wipe (`0.00–1.30 s`)**: Hold `0.00–0.15 s` on a non-empty clay base, then sweep staggered monotonic smoothstep right-to-left vertical 1-px anti-aliased masks across cumulative Workbench layer passes (`p0_base -> ... -> pN_full_clay -> final_Cycles/EEVEE`). Because Workbench `RANDOM` hashes colors deterministically by object name, shared objects match pixel-for-pixel across passes. Match reveal order to sweep direction to eliminate dead frames.
