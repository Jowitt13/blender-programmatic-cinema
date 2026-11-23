"""Resumable Cycles OptiX/CUDA GPU sequence renderer (native camera or optional framing preset)."""

import os
import sys
import time
import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from optix_render_utils import activate_optix_gpu
from cinema_rig_kit import apply_horizon_macro_framing


def render_sequence(
    blend_path,
    frame_start,
    frame_end,
    out_dir,
    samples=72,
    res_x=0,
    res_y=0,
    tile_size=1024,
    framing="native",
    radius_comp=1.0,
    exposure_delta=0.0,
):
    """Render [frame_start..frame_end] skipping valid existing PNGs (>10KB) for seamless pause/resume."""
    bpy.ops.wm.open_mainfile(filepath=blend_path)
    scene = bpy.context.scene
    if res_x > 0 and res_y > 0:
        scene.render.resolution_x = res_x
        scene.render.resolution_y = res_y

    activate_optix_gpu(scene, tile_size=tile_size, samples=samples, res_percent=100)

    if framing == "horizon_macro":
        apply_horizon_macro_framing(
            scene,
            frame_start=frame_start,
            frame_end=frame_end,
            radius_comp=radius_comp,
            exposure_delta=exposure_delta,
        )
    elif exposure_delta != 0.0:
        scene.view_settings.exposure += exposure_delta

    os.makedirs(out_dir, exist_ok=True)
    # Pre-step physics cleanly if starting mid-timeline
    if frame_start > 1:
        for f in range(1, frame_start):
            scene.frame_set(f)

    t_all = time.time()
    rendered = 0
    skipped = 0
    for f in range(frame_start, frame_end + 1):
        out_png = os.path.join(out_dir, f"frame_{f:04d}.png")
        if os.path.exists(out_png) and os.path.getsize(out_png) > 10240:
            skipped += 1
            scene.frame_set(f)
            continue
        scene.frame_set(f)
        scene.render.filepath = out_png
        t0 = time.time()
        bpy.ops.render.render(write_still=True)
        rendered += 1
        print(f"[FRAME {f}/{frame_end}] saved in {time.time() - t0:.1f}s -> {out_png}", flush=True)

    print(f"[SEQ_COMPLETE] rendered={rendered}, skipped={skipped}, total={time.time() - t_all:.1f}s", flush=True)


if __name__ == "__main__":
    # CLI: blender -b --factory-startup --python resumable_seq_renderer.py --
    #      <blend> <f_start> <f_end> <out_dir> [samples] [res_x] [res_y] [framing] [radius_comp] [exposure_delta]
    argv = sys.argv
    if "--" in argv:
        args = argv[argv.index("--") + 1 :]
        render_sequence(
            blend_path=args[0],
            frame_start=int(args[1]),
            frame_end=int(args[2]),
            out_dir=args[3],
            samples=int(args[4]) if len(args) > 4 else 72,
            res_x=int(args[5]) if len(args) > 5 else 0,
            res_y=int(args[6]) if len(args) > 6 else 0,
            framing=args[7] if len(args) > 7 else "native",
            radius_comp=float(args[8]) if len(args) > 8 else 1.0,
            exposure_delta=float(args[9]) if len(args) > 9 else 0.0,
        )
