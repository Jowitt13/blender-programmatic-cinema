"""Resumable Cycles GPU sequence renderer with PNG IEND integrity checks, ETA logging, and optional framing presets."""

import argparse
import os
import sys
import time

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from optix_render_utils import activate_optix_gpu
from cinema_rig_kit import apply_horizon_macro_framing


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def is_valid_png(path: str, min_bytes: int = 4096) -> bool:
    """Verify a PNG exists, exceeds min_bytes, starts with PNG magic bytes, and ends with an IEND chunk."""
    if not os.path.isfile(path):
        return False
    size = os.path.getsize(path)
    if size < min_bytes:
        return False
    try:
        with open(path, "rb") as fh:
            if fh.read(8) != PNG_SIGNATURE:
                return False
            fh.seek(max(0, size - 32))
            return b"IEND" in fh.read(32)
    except OSError:
        return False


def _format_eta(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.0f}s"
    if seconds < 3600:
        return f"{seconds / 60.0:.1f}m"
    return f"{seconds / 3600.0:.2f}h"


def render_sequence(
    blend_path: str,
    frame_start: int,
    frame_end: int,
    out_dir: str,
    samples: int = 72,
    res_x: int = 0,
    res_y: int = 0,
    tile_size: int = 1024,
    adaptive_threshold: float = 0.015,
    denoiser: str = "OPENIMAGEDENOISE",
    denoising_prefilter: str = "ACCURATE",
    filter_width: float = 1.25,
    framing: str = "native",
    radius_comp: float = 1.0,
    exposure_delta: float = 0.0,
    overwrite: bool = False,
    prestep_physics: bool = True,
    min_bytes: int = 4096,
) -> None:
    """Render [frame_start..frame_end] on GPU, skipping valid existing PNGs unless overwrite=True."""
    bpy.ops.wm.open_mainfile(filepath=os.path.abspath(blend_path))
    scene = bpy.context.scene
    if res_x > 0 and res_y > 0:
        scene.render.resolution_x = int(res_x)
        scene.render.resolution_y = int(res_y)

    activate_optix_gpu(
        scene,
        tile_size=tile_size,
        samples=samples,
        res_percent=100,
        adaptive_threshold=adaptive_threshold,
        denoiser=denoiser,
        denoising_prefilter=denoising_prefilter,
        filter_width=filter_width,
    )

    if framing == "horizon_macro":
        apply_horizon_macro_framing(
            scene,
            frame_start=frame_start,
            frame_end=frame_end,
            radius_comp=radius_comp,
            exposure_delta=exposure_delta,
        )
    elif exposure_delta != 0.0:
        scene.view_settings.exposure += float(exposure_delta)

    out_dir_abs = os.path.abspath(out_dir)
    os.makedirs(out_dir_abs, exist_ok=True)

    if prestep_physics and frame_start > 1:
        for f in range(1, frame_start):
            scene.frame_set(f)

    t_all = time.time()
    rendered = 0
    skipped = 0
    render_time_sum = 0.0
    total_frames = max(1, frame_end - frame_start + 1)

    for idx, f in enumerate(range(frame_start, frame_end + 1), start=1):
        out_png = os.path.join(out_dir_abs, f"frame_{f:04d}.png")
        if (not overwrite) and is_valid_png(out_png, min_bytes=min_bytes):
            skipped += 1
            if prestep_physics:
                scene.frame_set(f)
            continue

        scene.frame_set(f)
        scene.render.filepath = out_png
        t0 = time.time()
        bpy.ops.render.render(write_still=True)
        dt = time.time() - t0
        rendered += 1
        render_time_sum += dt
        avg = render_time_sum / rendered
        eta = _format_eta(avg * (total_frames - idx))
        print(
            f"[FRAME {f}/{frame_end}] {dt:.1f}s | avg={avg:.1f}s | ETA={eta} -> {out_png}",
            flush=True,
        )

    print(
        f"[SEQ_COMPLETE] rendered={rendered}, skipped={skipped}, "
        f"overwrite={overwrite}, total={time.time() - t_all:.1f}s",
        flush=True,
    )


def _parse_cli(args):
    """Support both modern --flags and legacy positional CLI arguments."""
    if args and not args[0].startswith("-"):
        return argparse.Namespace(
            blend=args[0],
            start=int(args[1]),
            end=int(args[2]),
            out_dir=args[3],
            samples=int(args[4]) if len(args) > 4 else 72,
            res_x=int(args[5]) if len(args) > 5 else 0,
            res_y=int(args[6]) if len(args) > 6 else 0,
            framing=args[7] if len(args) > 7 else "native",
            radius_comp=float(args[8]) if len(args) > 8 else 1.0,
            exposure_delta=float(args[9]) if len(args) > 9 else 0.0,
            tile_size=1024,
            adaptive_threshold=0.015,
            denoiser="OPENIMAGEDENOISE",
            prefilter="ACCURATE",
            filter_width=1.25,
            overwrite=False,
            no_prestep=False,
            min_bytes=4096,
        )

    parser = argparse.ArgumentParser(
        prog="resumable_seq_renderer.py",
        description="Resumable Cycles GPU sequence renderer for Blender 4.2–5.2+.",
    )
    parser.add_argument("--blend", required=True, help="Input .blend file path.")
    parser.add_argument("--start", type=int, required=True, help="First frame to render (inclusive).")
    parser.add_argument("--end", type=int, required=True, help="Last frame to render (inclusive).")
    parser.add_argument("--out-dir", required=True, help="Directory for output frame_XXXX.png files.")
    parser.add_argument("--samples", type=int, default=72, help="Cycles max samples (default: 72).")
    parser.add_argument("--res-x", type=int, default=0, help="Optional render width override.")
    parser.add_argument("--res-y", type=int, default=0, help="Optional render height override.")
    parser.add_argument("--tile-size", type=int, default=1024, help="Cycles auto-tile size (default: 1024; 512 at 4K).")
    parser.add_argument("--adaptive-threshold", type=float, default=0.015, help="Adaptive sampling noise threshold.")
    parser.add_argument("--denoiser", default="OPENIMAGEDENOISE", choices=("OPENIMAGEDENOISE", "OPTIX", "AUTO"))
    parser.add_argument("--prefilter", default="ACCURATE", choices=("ACCURATE", "FAST", "NONE"))
    parser.add_argument("--filter-width", type=float, default=1.25, help="Blackman-Harris filter width (default: 1.25).")
    parser.add_argument("--framing", default="native", choices=("native", "horizon_macro"))
    parser.add_argument("--radius-comp", type=float, default=1.0, help="Radius compensation for horizon_macro framing.")
    parser.add_argument("--exposure-delta", type=float, default=0.0, help="Optional AgX exposure offset in EV.")
    parser.add_argument("--overwrite", action="store_true", help="Re-render and overwrite existing PNG frames.")
    parser.add_argument("--no-prestep", action="store_true", help="Skip stepping frames 1..start-1 (non-physics scenes).")
    parser.add_argument("--min-bytes", type=int, default=4096, help="Minimum byte size to treat an existing PNG as valid.")
    return parser.parse_args(args)


if __name__ == "__main__":
    argv = sys.argv
    if "--" in argv:
        opts = _parse_cli(argv[argv.index("--") + 1 :])
        render_sequence(
            blend_path=opts.blend,
            frame_start=opts.start,
            frame_end=opts.end,
            out_dir=opts.out_dir,
            samples=opts.samples,
            res_x=opts.res_x,
            res_y=opts.res_y,
            tile_size=opts.tile_size,
            adaptive_threshold=opts.adaptive_threshold,
            denoiser=opts.denoiser,
            denoising_prefilter=opts.prefilter,
            filter_width=opts.filter_width,
            framing=opts.framing,
            radius_comp=opts.radius_comp,
            exposure_delta=opts.exposure_delta,
            overwrite=opts.overwrite,
            prestep_physics=not opts.no_prestep,
            min_bytes=opts.min_bytes,
        )
