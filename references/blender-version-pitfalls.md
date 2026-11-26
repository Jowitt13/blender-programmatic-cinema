# Blender 4.2–5.2+ Cycles GPU & FFmpeg 8+ Production Pitfalls

Verified engineering fixes for headless programmatic Blender (`4.2 LTS` through `5.2+`), Cycles GPU rendering, and FFmpeg 8+ post-assembly. Most fixes are already encapsulated in [scripts/blender_compat.py](../scripts/blender_compat.py), [scripts/optix_render_utils.py](../scripts/optix_render_utils.py), and [scripts/cinema_rig_kit.py](../scripts/cinema_rig_kit.py).

---

## 1. `--factory-startup` Silently Resets Cycles to CPU
- Running `blender -b --factory-startup` clears saved GPU preferences and falls back to CPU silently.
- **Fix**: Call `activate_optix_gpu(scene)` from [scripts/optix_render_utils.py](../scripts/optix_render_utils.py). It probes `OPTIX -> CUDA -> HIP -> ONEAPI -> METAL -> CPU`, enables ONLY devices matching the active backend, sets `scene.cycles.device = "GPU"`, and logs `[GPU_ACTIVE]`.

## 2. Blender 5.2 Compositor Tree, `Glare`, `ColorBalance` & `use_nodes` Breaking Changes
- In Blender 5.2, `scene.node_tree` was removed and assigning `scene.use_nodes` or `world.use_nodes` triggers `DeprecationWarning` (removal in 6.0).
- `glare.glare_type = 'FOG_GLOW'` raises `AttributeError`; Blender 5.2 uses Title-Case socket values (`"Fog Glow"`, `"Bloom"`, `"Streaks"`, `"High"`).
- `CompositorNodeColorBalance` removed `.correction_method` and has duplicate socket names (`"Lift"`, `"Gamma"`, `"Gain"` exist as both float and RGBA inputs -> index via `[1]`, `[2]`, `[4]`, `[6]`, `[8]`).
- **Fix**: Always call `create_compositor_tree()`, `configure_glare_node()`, `configure_color_balance_lgg()`, and `ensure_world_node_tree()` in [scripts/blender_compat.py](../scripts/blender_compat.py) (or `setup_cinema_compositor()` in [scripts/cinema_rig_kit.py](../scripts/cinema_rig_kit.py)), which automatically branch cleanly between Blender 4.x and 5.x.

## 3. Blender 5.2 `ShaderNodeTexSky` (`NISHITA` Removed) & EEVEE Engine Drift
- In Blender 5.2, `sky.sky_type = "NISHITA"` raises `TypeError` — physical Nishita sky was split into `"MULTIPLE_SCATTERING"` and `"SINGLE_SCATTERING"`.
- Blender `4.2–4.5` uses `BLENDER_EEVEE_NEXT`, whereas Blender `5.0+` renamed it back to `BLENDER_EEVEE`.
- Also note: headless Blender exits with code `0` even when a `--python` script raises an unhandled exception unless you pass `--python-exit-code 1`.
- **Fix**: Call `configure_physical_sky()` and `get_eevee_engine_id()` from [scripts/blender_compat.py](../scripts/blender_compat.py), and always pass `--python-exit-code 1` in automated tests or CI pipelines.

## 4. Blender 5.0+ Slotted Actions for Keyframe Interpolation
- `action.fcurves` may be `None` or absent on slotted actions in Blender 5.x.
- **Fix**: Call `set_action_interpolation(action, "LINEAR")` in [scripts/blender_compat.py](../scripts/blender_compat.py), which traverses Blender 5.x `layers -> strips -> channelbags` + `strip.channelbag(slot)` AND legacy `action.fcurves`.

## 5. Blender 5.2 `bmesh.ops.create_icosphere` Matrix Type
- Passing a plain Python tuple to `matrix=` raises `TypeError` in Blender 5.2.
- **Fix**: Wrap translations in `mathutils.Matrix.Translation((x, y, z))`.

## 6. NumPy Fractional-Power `NaN` Blackout in Procedural Maps
- Floating-point rounding like `np.sin(np.pi)` yields `-1e-16`; raising negative floats to fractional powers (`** 0.85`) creates `NaN` and renders pitch black in Cycles.
- **Fix**: Always `np.clip(arr, 0.0, 1.0)` before fractional exponentiation.

## 7. Shared Mesh Data-Block Material Overwrite
- Duplicating via `obj.copy()` shares `obj.data`; changing a material slot on one copy silently overwrites all copies.
- **Fix**: Use `new_obj.data = src_obj.data.copy()` when copies need distinct materials, or drive per-instance variation via `ShaderNodeObjectInfo -> Random`.

## 8. VRAM Safety on 4 GB–8 GB GPUs at Native 2K / 4K
- Enable `use_auto_tile = True` (`tile_size = 1024` at 2K, `512` at 4K), `use_adaptive_sampling = True`, `adaptive_threshold = 0.015`, `adaptive_min_samples = 16`, and GPU denoising (`denoising_use_gpu = True`) — all pre-configured in [scripts/optix_render_utils.py](../scripts/optix_render_utils.py).

## 9. Preserving Fine Architectural Sharpness Under Cycles Denoising
- Default `filter_width = 1.5` and fast denoisers blur fine glass mullions, micro-relief, and pinpoint LEDs.
- **Fix**: Use `pixel_filter_type = "BLACKMAN_HARRIS"`, `filter_width = 1.20–1.25`, and GPU `OPENIMAGEDENOISE` with `denoising_prefilter = "ACCURATE"` (default in [scripts/optix_render_utils.py](../scripts/optix_render_utils.py)).

## 10. Wide `SUN` Light `visible_glossy` White-Disc Reflection on Water
- A grazing sunset `SUN` with a wide `angle` (`10°–20°`) reflects as an artificial sharp white semi-circle on smooth water even when `visible_camera = False` and `sky.sun_disc = False`.
- **Fix**: Set `sun_obj.visible_glossy = False` and `sun_obj.visible_camera = False` while keeping `visible_diffuse = True` (automated via `set_object_ray_visibility()` in [scripts/blender_compat.py](../scripts/blender_compat.py) and checked by [scripts/scene_auditor.py](../scripts/scene_auditor.py)).

## 11. Aspect-Ratio Expansion vs Zoom Pixel-Density Trap (`16:9` -> `1:1`)
- Expanding `1920x1080` vertically into `1:1` (`sensor_fit = 'HORIZONTAL'`) at `1080x1080` shrinks the original `1920`-wide hero into `1080 px` (**only `31.6%` of original pixel density!**), smearing fine details.
- **Fix**: Call `configure_aspect_framing()` in [scripts/cinema_rig_kit.py](../scripts/cinema_rig_kit.py):
  - For vertical expansion (`horizontal_expand`), keep full horizontal resolution (**`1920x1920`**).
  - For side-cropping (`vertical_crop`), set `sensor_fit = 'VERTICAL'` **and** `sensor_height = 36.0 * (9/16) = 20.25 mm` (leaving Blender's default `24.0 mm` silently zooms out `1.185x`).

## 12. Stale Frame Cache & Partial Re-Render Discontinuity
- Re-rendering a sub-range while skipping existing frames after mesh/shader edits leaves stale old-version PNGs that cause mid-shot pops.
- **Fix**: Write to a fresh versioned folder or pass `--overwrite` to [scripts/resumable_seq_renderer.py](../scripts/resumable_seq_renderer.py), then verify the encoded MP4 with `--mad` in [scripts/delivery_audit.py](../scripts/delivery_audit.py).

## 13. FFmpeg 8+ Removed `-vsync`
- `-vsync 0` fails in FFmpeg 8+ (including FFmpeg 9.x) with `Unrecognized option 'vsync'`.
- **Fix**: Use `-fps_mode vfr` when extracting frames with `-vf "select='...'"`.

## 14. H.264 Level Compliance, Night-Sky Banding & Lossless-Source 4K Upscaling
- `1920x1920 @ 60 fps` requires **`-level 5.1`**; `2160x2160 @ 60 fps` requires **`-level 5.2`**.
- Prevent 8-bit `yuv420p` banding on deep twilight gradients with subtle temporal dither (`-vf "noise=alls=2:allf=t"`) at `CRF 13–14`.
- For slight platform-4K upscales (`1920sq -> 2160sq`), encode directly from lossless PNGs (`scale=2160:2160:flags=lanczos+accurate_rnd+full_chroma_int,unsharp=3:3:0.25:3:3:0.0`), never from an already-compressed MP4.

## 15. Windows Sandbox, PowerShell 5.1 & Orphaned Blender Processes
- Restricted sandboxes on Windows can block GPU/OptiX driver initialization (`blender.exe` exits with code `1` and empty stdout). Run Blender CLI with host GPU access while keeping FFmpeg/Python post-processing sandboxed.
- PowerShell 5.1 does not support `&&`; chain dependent steps with `; if ($LASTEXITCODE -eq 0) { ... }`.
- After stopping a background render, check `Get-Process blender` (Windows) or `pgrep blender` (macOS/Linux) so no orphaned process holds GPU VRAM.

## 16. Workbench Clay Mesh Hygiene & CJK Typography Safety
- In Workbench `RANDOM` mode, `smooth=True` on large triangulated flat caps causes diagonal Gouraud streaks, and curved overlapping 2D/NPR profile layers (`dome_factor > 0`) cause Z-fighting. Keep flat caps `smooth=False`, `dome_factor = 0.0`, enforce monotonic depth ordering, and hide EEVEE-only shadow/alpha decals during Workbench passes.
- Never pass CJK text to ASCII-only monospace fonts (`consolab.ttf` renders `□□`), avoid rare Dingbat arrows (`➔` -> use `→` or vector shapes), and inspect a storyboard extracted from the final MP4.
