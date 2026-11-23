# Blender 5.2 LTS + Cycles OptiX + FFmpeg 8 Production Pitfalls

Verified engineering fixes for script-driven Blender 5.2 + Cycles GPU rendering and FFmpeg video assembly. Check these before writing batch scripts.

---

## 1. `--factory-startup` Silently Resets Cycles to CPU
- Running `blender -b --factory-startup` clears saved Cycles device preferences and falls back to CPU silently.
- **Fix**: Explicitly call `activate_optix_gpu(scene)` (see `scripts/optix_render_utils.py`) in every batch session: set `compute_device_type = 'OPTIX'`, call `prefs.get_devices()`, enable ONLY `OPTIX` devices (fallback `CUDA`), and set `scene.cycles.device = 'GPU'`.
- Always print `[GPU_ACTIVE] devs=[...]` at startup and confirm the GPU appears in logs.

## 2. Blender 5.2 Compositor `Glare` Node API Change
- `glare.glare_type = 'FOG_GLOW'` raises `AttributeError` in Blender 5.2.
- **Fix**: Set the node socket default value instead:
  ```python
  glare.inputs["Type"].default_value = "Fog Glow"
  ```

## 3. Blender 5.2 `bmesh.ops.create_icosphere` Matrix Type
- Passing a plain Python tuple to `matrix=` fails in Blender 5.2.
- **Fix**: Wrap translations with `mathutils.Matrix.Translation((x, y, z))`.

## 4. Blender 5.0+ Slotted Actions for Keyframe Interpolation
- `action.fcurves` may be `None` or absent on slotted actions in Blender 5.x.
- **Fix**: Traverse both modern slotted actions and legacy `fcurves`:
  ```python
  fcurves = getattr(act, "fcurves", None)
  if fcurves is None and hasattr(act, "layers"):
      for layer in act.layers:
          for strip in layer.strips:
              for bag in getattr(strip, "channelbags", []):
                  for fc in bag.fcurves:
                      for kp in fc.keyframe_points:
                          kp.interpolation = "LINEAR"
  elif fcurves is not None:
      for fc in fcurves:
          for kp in fc.keyframe_points:
              kp.interpolation = "LINEAR"
  ```

## 5. NumPy Fractional-Power `NaN` Blackout in Procedural Maps
- Floating-point boundary values such as `np.sin(np.pi)` produce `-1e-16`; raising negative numbers to fractional exponents (`** 0.85`) yields `NaN` and renders pitch black in Cycles.
- **Fix**: Always `np.clip(arr, 0.0, 1.0)` before applying fractional powers.

## 6. Shared Mesh Data-Block Material Overwrite
- Duplicating an object via `obj.copy()` shares `obj.data`; changing a material slot on one copy silently overwrites all copies.
- **Fix**: Assign `new_obj.data = src_obj.data.copy()` whenever instances require independent materials.

## 7. VRAM Safety on 4GB–8GB GPUs at Native 2K / 4K
- Enable `scene.cycles.use_auto_tile = True` (`tile_size = 1024` at 2K, `512` at 4K), `use_adaptive_sampling = True`, `adaptive_threshold = 0.015`, and GPU `OPTIX` denoising (`denoising_use_gpu = True`).

## 8. FFmpeg 8.x Removed `-vsync`
- `-vsync 0` fails in FFmpeg 8.x with `Unrecognized option 'vsync'`.
- **Fix**: Use `-fps_mode vfr` when extracting selected frames with `-vf "select='...'"`.

## 9. Windows Sandbox & Orphaned Blender Processes
- On Windows, restricted terminal sandboxes can block `blender.exe` GPU/OptiX driver access (exit code 1 with empty stdout). Run Blender CLI invocations with host GPU access while keeping FFmpeg and image-processing steps sandboxed.
- After cancelling a background render shell script, check running `blender` processes (`Get-Process blender` / `pgrep blender`) to confirm no orphaned child process continues holding VRAM.
