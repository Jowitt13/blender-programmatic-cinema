"""Zero-dependency visual QC sheet generator: 3-second Workbench 4-view clay sheet & Cycles 1:1 crop diagnostic."""

import argparse
import math
import os
import sys
import tempfile
from typing import List, Tuple

import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from optix_render_utils import activate_optix_gpu


def _load_rgba_array(path: str) -> np.ndarray:
    """Load an image via Blender's native image loader into float32 (H, W, 4) top-down array."""
    img = bpy.data.images.load(path, check_existing=False)
    try:
        w, h = img.size[0], img.size[1]
        arr = np.empty(w * h * 4, dtype=np.float32)
        img.pixels.foreach_get(arr)
        arr = arr.reshape((h, w, 4))
        # Flip vertically from Blender bottom-up to standard top-down
        return arr[::-1].copy()
    finally:
        bpy.data.images.remove(img)


def _save_rgba_array(arr_top_down: np.ndarray, out_path: str) -> None:
    """Save a float32 (H, W, 4) top-down RGBA array to PNG via Blender's native saver (zero Pillow needed)."""
    h, w, _ = arr_top_down.shape
    flipped = np.clip(arr_top_down[::-1], 0.0, 1.0).astype(np.float32)
    img = bpy.data.images.new("_QC_Composite", width=w, height=h, alpha=True)
    try:
        img.pixels.foreach_set(flipped.ravel())
        out_abs = os.path.abspath(out_path)
        os.makedirs(os.path.dirname(out_abs), exist_ok=True)
        img.filepath_raw = out_abs
        img.file_format = "PNG"
        img.save()
    finally:
        bpy.data.images.remove(img)


def _hero_bounds(scene) -> Tuple[Vector, float]:
    """Compute world bounding center and bounding sphere radius of hero meshes (excluding Env_*)."""
    meshes = [
        obj
        for obj in scene.objects
        if obj.type == "MESH" and not obj.hide_render and not obj.name.startswith("Env_")
    ]
    if not meshes:
        meshes = [obj for obj in scene.objects if obj.type == "MESH" and not obj.hide_render]
    if not meshes:
        return Vector((0.0, 0.0, 0.0)), 1.0

    mn = Vector((1e18, 1e18, 1e18))
    mx = Vector((-1e18, -1e18, -1e18))
    for obj in meshes:
        for corner in obj.bound_box:
            wc = obj.matrix_world @ Vector(corner)
            mn.x, mn.y, mn.z = min(mn.x, wc.x), min(mn.y, wc.y), min(mn.z, wc.z)
            mx.x, mx.y, mx.z = max(mx.x, wc.x), max(mx.y, wc.y), max(mx.z, wc.z)

    center = (mn + mx) * 0.5
    radius = max(0.1, (mx - mn).length * 0.5)
    return center, radius


def _look_at(obj, target: Vector) -> None:
    direction = target - obj.location
    rot_quat = direction.to_track_quat("-Z", "Y")
    obj.rotation_euler = rot_quat.to_euler()


def render_clay_4view(scene, out_path: str, cell_res: int = 512) -> None:
    """Render a 2x2 Workbench clay QC sheet (Hero Cam, 3/4 Elevated, Front, Side) in seconds."""
    orig_engine = scene.render.engine
    orig_cam = scene.camera
    orig_rx, orig_ry = scene.render.resolution_x, scene.render.resolution_y
    orig_pct = scene.render.resolution_percentage

    center, radius = _hero_bounds(scene)
    dist = radius * 3.1

    # Configure Workbench high-legibility clay mode
    scene.render.engine = "BLENDER_WORKBENCH"
    shading = scene.display.shading
    shading.light = "STUDIO"
    shading.color_type = "RANDOM"
    shading.show_object_outline = True
    shading.show_cavity = True
    if hasattr(shading, "cavity_type"):
        shading.cavity_type = "BOTH"

    scene.render.resolution_x = cell_res
    scene.render.resolution_y = cell_res
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"

    temp_cams: List[bpy.types.Object] = []

    def _spawn_cam(name: str, loc: Vector, lens: float = 50.0):
        cdata = bpy.data.cameras.new(name)
        cdata.lens = lens
        cdata.clip_start = max(0.01, radius * 0.005)
        cdata.clip_end = max(500.0, radius * 30.0)
        cobj = bpy.data.objects.new(name, cdata)
        cobj.location = loc
        _look_at(cobj, center)
        scene.collection.objects.link(cobj)
        temp_cams.append(cobj)
        return cobj

    c_iso = _spawn_cam("_QC_Iso", center + Vector((dist * 0.72, -dist * 0.72, dist * 0.55)), lens=50.0)
    c_front = _spawn_cam("_QC_Front", center + Vector((0.0, -dist, 0.0)), lens=65.0)
    c_side = _spawn_cam("_QC_Side", center + Vector((dist, 0.0, 0.0)), lens=65.0)
    views = [orig_cam if orig_cam is not None else c_iso, c_iso, c_front, c_side]

    panels = []
    with tempfile.TemporaryDirectory(prefix="bpc_clay_qc_") as tmpdir:
        for idx, cam in enumerate(views):
            scene.camera = cam
            p = os.path.join(tmpdir, f"view_{idx}.png")
            scene.render.filepath = p
            bpy.ops.render.render(write_still=True)
            panels.append(_load_rgba_array(p))

    for cobj in temp_cams:
        cdata = cobj.data
        bpy.data.objects.remove(cobj, do_unlink=True)
        bpy.data.cameras.remove(cdata)

    # Stitch 2x2 grid with clean 6px dark divider
    pad = 6
    grid_h = cell_res * 2 + pad * 3
    grid_w = cell_res * 2 + pad * 3
    canvas = np.zeros((grid_h, grid_w, 4), dtype=np.float32)
    canvas[:, :, :3] = 0.04
    canvas[:, :, 3] = 1.0

    coords = [
        (pad, pad),
        (pad, pad * 2 + cell_res),
        (pad * 2 + cell_res, pad),
        (pad * 2 + cell_res, pad * 2 + cell_res),
    ]
    for (y0, x0), panel in zip(coords, panels):
        canvas[y0 : y0 + cell_res, x0 : x0 + cell_res] = panel

    _save_rgba_array(canvas, out_path)

    # Restore original settings
    scene.render.engine = orig_engine
    scene.camera = orig_cam
    scene.render.resolution_x = orig_rx
    scene.render.resolution_y = orig_ry
    scene.render.resolution_percentage = orig_pct
    print(f"[CLAY_QC_SAVED] {os.path.abspath(out_path)} ({grid_w}x{grid_h}, 4 views: Hero/Iso/Front/Side)", flush=True)


def render_cycles_qc_crop(scene, out_path: str, res: int = 1024, samples: int = 32) -> None:
    """Render a Cycles GPU look-dev preview + 2 stacked 1:1 native pixel crops + exposure telemetry."""
    aspect = scene.render.resolution_x / max(1, scene.render.resolution_y)
    if aspect >= 1.0:
        rx = int(res)
        ry = max(64, int(round(res / aspect)))
    else:
        ry = int(res)
        rx = max(64, int(round(res * aspect)))

    scene.render.resolution_x = rx
    scene.render.resolution_y = ry
    activate_optix_gpu(scene, tile_size=1024, samples=samples, res_percent=100)

    with tempfile.TemporaryDirectory(prefix="bpc_cyc_qc_") as tmpdir:
        raw_png = os.path.join(tmpdir, "cycles_raw.png")
        scene.render.filepath = raw_png
        bpy.ops.render.render(write_still=True)
        full = _load_rgba_array(raw_png)

    h, w, _ = full.shape
    luma = 0.2126 * full[:, :, 0] + 0.7152 * full[:, :, 1] + 0.0722 * full[:, :, 2]
    clipped_white = float(np.mean(luma >= 0.99) * 100.0)
    crushed_black = float(np.mean(luma <= 0.01) * 100.0)
    p01, p50, p99 = [float(x) for x in np.percentile(luma, (1, 50, 99))]

    # Two 1:1 native crops: center crop + highest-contrast detail window
    pad = 6
    crop_sz = max(64, (h - pad) // 2)
    cy0 = max(0, (h - crop_sz) // 2)
    cx0 = max(0, (w - crop_sz) // 2)
    crop_center = full[cy0 : cy0 + crop_sz, cx0 : cx0 + crop_sz]

    # Find highest local gradient energy region for secondary 1:1 crop
    gy = np.abs(np.diff(luma, axis=0, prepend=luma[:1, :]))
    gx = np.abs(np.diff(luma, axis=1, prepend=luma[:, :1]))
    grad = gx + gy
    best_score = -1.0
    by0, bx0 = 0, 0
    step = max(32, crop_sz // 3)
    for y in range(0, max(1, h - crop_sz + 1), step):
        for x in range(0, max(1, w - crop_sz + 1), step):
            if abs(y - cy0) < crop_sz // 3 and abs(x - cx0) < crop_sz // 3:
                continue
            sc = float(grad[y : y + crop_sz, x : x + crop_sz].mean())
            if sc > best_score:
                best_score = sc
                by0, bx0 = y, x
    crop_detail = full[by0 : by0 + crop_sz, bx0 : bx0 + crop_sz]

    out_w = w + pad + crop_sz
    out_h = max(h, crop_sz * 2 + pad)
    canvas = np.zeros((out_h, out_w, 4), dtype=np.float32)
    canvas[:, :, :3] = 0.04
    canvas[:, :, 3] = 1.0
    canvas[:h, :w] = full
    canvas[:crop_sz, w + pad : w + pad + crop_sz] = crop_center
    canvas[crop_sz + pad : crop_sz * 2 + pad, w + pad : w + pad + crop_sz] = crop_detail

    _save_rgba_array(canvas, out_path)
    print(
        f"[CYCLES_QC_SAVED] {os.path.abspath(out_path)} ({out_w}x{out_h}) | "
        f"luma_mean={luma.mean():.3f} p01={p01:.3f} p50={p50:.3f} p99={p99:.3f} | "
        f"clipped_white={clipped_white:.2f}% crushed_black={crushed_black:.2f}%",
        flush=True,
    )


def _parse_cli(args):
    parser = argparse.ArgumentParser(prog="visual_qc_kit.py", description="Fast Workbench 4-view clay & Cycles 1:1 crop QC generator.")
    parser.add_argument("--blend", required=True, help="Input .blend file.")
    parser.add_argument("--mode", required=True, choices=("clay_4view", "cycles_crop"), help="QC capture mode.")
    parser.add_argument("--out", required=True, help="Output PNG path.")
    parser.add_argument("--cell-res", type=int, default=512, help="Per-cell resolution for clay_4view (default: 512).")
    parser.add_argument("--res", type=int, default=1024, help="Long-edge resolution for cycles_crop (default: 1024).")
    parser.add_argument("--samples", type=int, default=32, help="Cycles samples for cycles_crop (default: 32).")
    parser.add_argument("--frame", type=int, default=0, help="Optional frame number to set before capture.")
    return parser.parse_args(args)


if __name__ == "__main__":
    argv = sys.argv
    if "--" in argv:
        opts = _parse_cli(argv[argv.index("--") + 1 :])
        bpy.ops.wm.open_mainfile(filepath=os.path.abspath(opts.blend))
        scene = bpy.context.scene
        if opts.frame > 0:
            scene.frame_set(opts.frame)
        if opts.mode == "clay_4view":
            render_clay_4view(scene, out_path=opts.out, cell_res=opts.cell_res)
        else:
            render_cycles_qc_crop(scene, out_path=opts.out, res=opts.res, samples=opts.samples)
