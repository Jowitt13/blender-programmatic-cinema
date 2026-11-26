"""Gold-Standard Example 02: Hard-Surface Game-Ready Hero Prop (Armored Industrial Supply Crate).

Demonstrates the complete game-asset & material_library.py workflow:
  1. Spec-first real-world dimensions (1.20m x 0.72m x 0.64m, grounded at z = 0).
  2. Macro -> Meso -> Micro 3-tier hard-surface geometry:
     - Macro: Chamfered lower hull + stepped armored lid + recessed rubber gasket channel.
     - Meso: 8 corner shock-bumper guards, structural vertical ribs, dual side carry handles,
       twin front locking latches, and a recessed front status bezel.
     - Micro: 16 recessed hex bolt heads + glowing amber status LED bar.
  3. One-line physical PBR materials from scripts/material_library.py (painted industrial metal,
     anodized aluminum, brushed steel, aged brass, warm emissive LED) — 100% ORM-bake ready.
  4. Dramatic studio 3-point lighting with Light-Path split obsidian backdrop & AgX grading.

Usage:
  blender -b --factory-startup --python-exit-code 1 --python examples/02_game_hero_prop.py -- \
    --out ./build/game_crate.blend [--render ./build/game_crate.png --samples 64]
"""

import argparse
import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

SCRIPT_DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
sys.path.insert(0, SCRIPT_DIR)

from blender_compat import ensure_world_node_tree, set_agx_view_transform
from cinema_rig_kit import hex_to_linear_rgb, setup_cinema_compositor
from material_library import make_material
from optix_render_utils import activate_optix_gpu


SPEC = {
    "width": 1.20,
    "depth": 0.72,
    "body_h": 0.44,
    "lid_h": 0.16,
    "foot_h": 0.04,
    "bevel_main": 0.018,
    "bevel_detail": 0.005,
}


def _add_beveled_box(name, size_xyz, center_xyz, mat, collection, bevel_w=0.01, segments=2):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=Vector(size_xyz), verts=bm.verts)
    if bevel_w > 0.0:
        bmesh.ops.bevel(
            bm,
            geom=list(bm.edges),
            offset=bevel_w,
            segments=segments,
            affect="EDGES",
            clamp_overlap=True,
        )
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    obj.location = center_xyz
    obj.data.materials.append(mat)
    collection.objects.link(obj)
    return obj


def _add_hex_bolt(name, center_xyz, rot_deg, radius, depth, mat, collection):
    bm = bmesh.new()
    bmesh.ops.create_cone(
        bm,
        cap_ends=True,
        cap_tris=False,
        segments=6,
        radius1=radius,
        radius2=radius * 0.92,
        depth=depth,
    )
    bmesh.ops.bevel(bm, geom=list(bm.edges), offset=radius * 0.14, segments=1, affect="EDGES", clamp_overlap=True)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    obj.location = center_xyz
    obj.rotation_euler = tuple(math.radians(a) for a in rot_deg)
    obj.data.materials.append(mat)
    collection.objects.link(obj)
    return obj


def build_game_crate(out_blend: str, render_png: str = "", samples: int = 64) -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.name = "Example02_GameHeroProp"
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 1280
    scene.render.image_settings.file_format = "PNG"
    set_agx_view_transform(scene, look="AgX - Medium High Contrast", exposure=0.05)

    col_rig = bpy.data.collections.new("00_CAMERAS_LIGHTS")
    col_env = bpy.data.collections.new("02_ENVIRONMENT")
    col_hero = bpy.data.collections.new("03_HERO_PROP")
    for c in (col_rig, col_env, col_hero):
        scene.collection.children.link(c)

    # One-line anti-plastic PBR materials from material_library.py (all ORM-bake ready)
    m_olive = make_material("painted_industrial_metal", name="Mat_CrateOliveHull", noise_scale_mult=2.2)
    m_dark_alu = make_material("anodized_aluminum", name="Mat_CrateDarkBumper", noise_scale_mult=1.8)
    m_steel = make_material("brushed_steel", name="Mat_CrateSteelLatch", noise_scale_mult=2.5)
    m_brass = make_material("aged_brass", name="Mat_CrateBrassBolts", noise_scale_mult=3.0)
    m_led = make_material("warm_emissive", name="Mat_CrateStatusLED", tint=(1.0, 0.52, 0.14), emission_strength=16.0)
    m_floor = make_material("damp_granite", name="Mat_StudioFloor", noise_scale_mult=1.2)

    w = SPEC["width"]
    d = SPEC["depth"]
    bh = SPEC["body_h"]
    lh = SPEC["lid_h"]
    fh = SPEC["foot_h"]
    total_h = fh + bh + lh

    # Ground studio floor (Env_* prefix excluded from game hero export/bounds)
    _add_beveled_box("Env_StudioPlinth", (12.0, 12.0, 0.08), (0.0, 0.0, -0.04), m_floor, col_env, bevel_w=0.0)

    # Tier 1 (Macro): Skid rails, lower armored body, recessed gasket collar, upper stepped lid
    for sx in (-w * 0.36, w * 0.36):
        _add_beveled_box(f"Hero_SkidRail_{sx:+.2f}", (0.14, d - 0.06, fh), (sx, 0.0, fh * 0.5), m_dark_alu, col_hero, bevel_w=0.008)

    _add_beveled_box("Hero_LowerHull", (w, d, bh), (0.0, 0.0, fh + bh * 0.5), m_olive, col_hero, bevel_w=SPEC["bevel_main"], segments=3)
    _add_beveled_box("Hero_GasketChannel", (w - 0.03, d - 0.03, 0.035), (0.0, 0.0, fh + bh + 0.012), m_dark_alu, col_hero, bevel_w=0.004)
    _add_beveled_box("Hero_UpperLid", (w + 0.02, d + 0.02, lh), (0.0, 0.0, fh + bh + 0.02 + lh * 0.5), m_olive, col_hero, bevel_w=SPEC["bevel_main"], segments=3)
    _add_beveled_box("Hero_LidTopArmor", (w * 0.72, d * 0.68, 0.028), (0.0, 0.0, total_h + 0.022), m_dark_alu, col_hero, bevel_w=0.007)

    # Tier 2 (Meso): 8 corner bumper guards, reinforcing ribs, side carry handles, front latches, status bezel
    for sx in (-1, 1):
        for sy in (-1, 1):
            cx = sx * (w * 0.5 - 0.045)
            cy = sy * (d * 0.5 - 0.045)
            _add_beveled_box(
                f"Hero_CornerGuard_B_{sx}_{sy}",
                (0.13, 0.13, 0.14),
                (cx, cy, fh + 0.075),
                m_dark_alu,
                col_hero,
                bevel_w=0.010,
            )
            _add_beveled_box(
                f"Hero_CornerGuard_T_{sx}_{sy}",
                (0.14, 0.14, 0.12),
                (cx * 1.01, cy * 1.01, fh + bh + lh - 0.03),
                m_dark_alu,
                col_hero,
                bevel_w=0.010,
            )

    # Front & rear vertical reinforcement ribs
    for rx in (-0.34, 0.0, 0.34):
        for sy, tag in ((-1, "F"), (1, "B")):
            _add_beveled_box(
                f"Hero_Rib_{tag}_{rx:+.2f}",
                (0.055, 0.04, bh * 0.82),
                (rx, sy * (d * 0.5 + 0.005), fh + bh * 0.5),
                m_dark_alu,
                col_hero,
                bevel_w=0.006,
            )

    # Side heavy steel carry handles
    for sx, tag in ((-1, "L"), (1, "R")):
        hx = sx * (w * 0.5 + 0.028)
        _add_beveled_box(f"Hero_HandleBar_{tag}", (0.026, 0.26, 0.028), (hx, 0.0, fh + bh * 0.62), m_steel, col_hero, bevel_w=0.006)
        for hy in (-0.115, 0.115):
            _add_beveled_box(f"Hero_HandleMount_{tag}_{hy:+.2f}", (0.045, 0.036, 0.065), (hx - sx * 0.012, hy, fh + bh * 0.62), m_dark_alu, col_hero, bevel_w=0.004)

    # Twin front clamp latches bridging hull & lid
    for lx in (-0.21, 0.21):
        _add_beveled_box(f"Hero_LatchPlate_{lx:+.2f}", (0.085, 0.032, 0.20), (lx, -(d * 0.5 + 0.015), fh + bh + 0.01), m_steel, col_hero, bevel_w=0.005)
        _add_beveled_box(f"Hero_LatchClasp_{lx:+.2f}", (0.055, 0.048, 0.06), (lx, -(d * 0.5 + 0.024), fh + bh - 0.04), m_brass, col_hero, bevel_w=0.004)

    # Front recessed telemetry/status bezel + glowing amber LED strip
    _add_beveled_box("Hero_StatusBezel", (0.24, 0.028, 0.075), (0.0, -(d * 0.5 + 0.008), fh + bh + lh * 0.52), m_dark_alu, col_hero, bevel_w=0.005)
    _add_beveled_box("Hero_StatusLED", (0.16, 0.014, 0.020), (0.0, -(d * 0.5 + 0.020), fh + bh + lh * 0.52), m_led, col_hero, bevel_w=0.002)

    # Tier 3 (Micro): 16 recessed brass hex bolts across front/top armored trims
    bolt_idx = 0
    for bx in (-0.42, -0.14, 0.14, 0.42):
        for bz in (fh + 0.08, fh + bh - 0.07):
            _add_hex_bolt(f"Hero_Bolt_F_{bolt_idx:02d}", (bx, -(d * 0.5 + 0.008), bz), (90, 0, 0), 0.011, 0.012, m_brass, col_hero)
            bolt_idx += 1
        for by in (-0.20, 0.20):
            _add_hex_bolt(f"Hero_Bolt_T_{bolt_idx:02d}", (bx, by, total_h + 0.036), (0, 0, 0), 0.011, 0.012, m_brass, col_hero)
            bolt_idx += 1

    # Light-Path split obsidian studio world
    world = bpy.data.worlds.new("PropStudioWorld")
    scene.world = world
    wnt = ensure_world_node_tree(world)
    wnt.nodes.clear()
    w_out = wnt.nodes.new("ShaderNodeOutputWorld")
    bg_cam = wnt.nodes.new("ShaderNodeBackground")
    bg_cam.inputs["Color"].default_value = hex_to_linear_rgb("#07080a")
    bg_cam.inputs["Strength"].default_value = 1.0
    bg_env = wnt.nodes.new("ShaderNodeBackground")
    bg_env.inputs["Color"].default_value = (0.06, 0.07, 0.085, 1.0)
    bg_env.inputs["Strength"].default_value = 0.45
    lp = wnt.nodes.new("ShaderNodeLightPath")
    mix = wnt.nodes.new("ShaderNodeMixShader")
    wnt.links.new(lp.outputs["Is Camera Ray"], mix.inputs["Fac"])
    wnt.links.new(bg_env.outputs["Background"], mix.inputs[1])
    wnt.links.new(bg_cam.outputs["Background"], mix.inputs[2])
    wnt.links.new(mix.outputs["Shader"], w_out.inputs["Surface"])

    # Sculpted 3-point product studio lighting
    def _light(name, loc, rot_deg, energy, sx, sy, col):
        ld = bpy.data.lights.new(name, type="AREA")
        ld.energy = energy
        ld.shape = "RECTANGLE"
        ld.size = sx
        ld.size_y = sy
        ld.color = col
        lo = bpy.data.objects.new(name, ld)
        lo.location = loc
        lo.rotation_euler = tuple(math.radians(a) for a in rot_deg)
        col_rig.objects.link(lo)

    _light("Key_GrazingSoftbox", (-2.2, -1.5, 2.4), (48, -34, -32), 210, 1.8, 1.2, (1.0, 0.95, 0.88))
    _light("Rim_CoolEdgeStrip", (2.3, 1.7, 1.6), (62, 42, 142), 185, 0.45, 2.4, (0.78, 0.90, 1.0))
    _light("Fill_SubtleFront", (0.4, -2.8, 1.8), (62, 0, 0), 32, 2.6, 1.8, (0.94, 0.96, 1.0))

    # 85mm 3/4 Hero Camera aimed cleanly at crate center
    target = bpy.data.objects.new("Target_Crate", None)
    target.location = (0.0, 0.0, total_h * 0.46)
    col_rig.objects.link(target)

    cdata = bpy.data.cameras.new("Cam_PropHero_85mm")
    cdata.lens = 85.0
    cdata.sensor_fit = "HORIZONTAL"
    cdata.sensor_width = 36.0
    cdata.clip_start = 0.05
    cdata.clip_end = 100.0
    cdata.dof.use_dof = True
    cdata.dof.focus_object = target
    cdata.dof.aperture_fstop = 5.6
    cobj = bpy.data.objects.new("Cam_PropHero_85mm", cdata)
    cobj.location = (2.15, -2.55, 1.38)
    con = cobj.constraints.new("TRACK_TO")
    con.target = target
    con.track_axis = "TRACK_NEGATIVE_Z"
    con.up_axis = "UP_Y"
    col_rig.objects.link(cobj)
    scene.camera = cobj

    activate_optix_gpu(scene, tile_size=1024, samples=samples, res_percent=100)
    setup_cinema_compositor(scene, glare_type="Fog Glow", glare_threshold=2.2, glare_strength=0.22)

    out_abs = os.path.abspath(out_blend)
    os.makedirs(os.path.dirname(out_abs), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=out_abs)
    print(f"[EXAMPLE02_SAVED] {out_abs}", flush=True)

    if render_png:
        png_abs = os.path.abspath(render_png)
        os.makedirs(os.path.dirname(png_abs), exist_ok=True)
        scene.render.filepath = png_abs
        bpy.ops.render.render(write_still=True)
        print(f"[EXAMPLE02_RENDERED] {png_abs}", flush=True)


if __name__ == "__main__":
    argv = sys.argv
    if "--" in argv:
        parser = argparse.ArgumentParser(prog="02_game_hero_prop.py")
        parser.add_argument("--out", required=True, help="Output .blend path.")
        parser.add_argument("--render", default="", help="Optional Cycles PNG render path.")
        parser.add_argument("--samples", type=int, default=64, help="Cycles samples (default: 64).")
        opts = parser.parse_args(argv[argv.index("--") + 1 :])
        build_game_crate(opts.out, render_png=opts.render, samples=opts.samples)
