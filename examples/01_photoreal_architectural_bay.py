"""Gold-Standard Example 01: Spec-First Photorealistic Architectural Curtain-Wall Bay (Blue Hour).

Demonstrates the complete blender-programmatic-studio craft principles in ~220 lines:
  1. Spec-first real-world dimensions (1 BU = 1m) locked in a canonical SPEC dictionary.
  2. Macro -> Meso -> Micro 3-tier geometry (structural concrete piers with bevels, recessed
     anodized aluminum mullions, horizontal transoms, behind-glass interior floor slabs +
     warm ceiling light strips, and a damp granite entry plinth).
  3. Anti-plastic physical PBR materials (multi-scale roughness breakup, AO cavity darkening,
     damp clearcoat plaza, and half-mirror architectural glass with true interior depth).
  4. Blender 4.2–5.2+ compatible lighting, AgX color management, and compositor glare.

Usage:
  blender -b --factory-startup --python examples/01_photoreal_architectural_bay.py -- \
    --out ./build/arch_bay.blend [--render ./build/arch_bay.png --samples 48]
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

from blender_compat import (
    configure_physical_sky,
    ensure_material_node_tree,
    ensure_world_node_tree,
    set_agx_view_transform,
    set_object_ray_visibility,
    set_principled_input,
)
from cinema_rig_kit import setup_cinema_compositor
from optix_render_utils import activate_optix_gpu


# ---------------------------------------------------------------------------
# 1. SPEC-FIRST ARCHITECTURAL BLUEPRINT (Real-World Meters: 1 BU = 1.0 m)
# ---------------------------------------------------------------------------
SPEC = {
    "bay_width": 9.6,
    "bay_depth": 5.4,
    "floors": 3,
    "floor_height": 3.8,
    "plinth_height": 0.45,
    "pier_width": 0.72,
    "pier_depth": 0.85,
    "mullion_count": 5,
    "mullion_w": 0.085,
    "mullion_d": 0.16,
    "transom_h": 0.12,
    "glass_recess": 0.22,
    "bevel_width": 0.014,
}


def _make_pbr_concrete(name="Mat_ArchConcrete"):
    mat = bpy.data.materials.new(name)
    nt = ensure_material_node_tree(mat)
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")

    tc = nt.nodes.new("ShaderNodeTexCoord")
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 6.5
    noise.inputs["Detail"].default_value = 10.0
    noise.inputs["Roughness"].default_value = 0.65

    ao = nt.nodes.new("ShaderNodeAmbientOcclusion")
    ao.inputs["Distance"].default_value = 0.65

    mix_col = nt.nodes.new("ShaderNodeMix")
    mix_col.data_type = "RGBA"
    mix_col.inputs["Factor"].default_value = 0.45
    mix_col.inputs["A"].default_value = (0.16, 0.17, 0.185, 1.0)
    mix_col.inputs["B"].default_value = (0.28, 0.29, 0.31, 1.0)

    ao_mul = nt.nodes.new("ShaderNodeMix")
    ao_mul.data_type = "RGBA"
    ao_mul.blend_type = "MULTIPLY"
    ao_mul.inputs["Factor"].default_value = 0.42

    rough_map = nt.nodes.new("ShaderNodeMapRange")
    rough_map.inputs["From Min"].default_value = 0.25
    rough_map.inputs["From Max"].default_value = 0.75
    rough_map.inputs["To Min"].default_value = 0.48
    rough_map.inputs["To Max"].default_value = 0.78

    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.12
    bump.inputs["Distance"].default_value = 0.008

    nt.links.new(tc.outputs["Object"], noise.inputs["Vector"])
    nt.links.new(noise.outputs["Fac"], mix_col.inputs["Factor"])
    nt.links.new(mix_col.outputs["Result"], ao_mul.inputs["A"])
    nt.links.new(ao.outputs["Color"], ao_mul.inputs["B"])
    nt.links.new(ao_mul.outputs["Result"], bsdf.inputs["Base Color"])
    nt.links.new(noise.outputs["Fac"], rough_map.inputs["Value"])
    nt.links.new(rough_map.outputs["Result"], bsdf.inputs["Roughness"])
    nt.links.new(noise.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat


def _make_anodized_metal(name="Mat_DarkAnodizedMullion"):
    mat = bpy.data.materials.new(name)
    nt = ensure_material_node_tree(mat)
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = (0.045, 0.052, 0.062, 1.0)
    bsdf.inputs["Metallic"].default_value = 0.92

    tc = nt.nodes.new("ShaderNodeTexCoord")
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 28.0
    noise.inputs["Detail"].default_value = 6.0
    rm = nt.nodes.new("ShaderNodeMapRange")
    rm.inputs["To Min"].default_value = 0.22
    rm.inputs["To Max"].default_value = 0.36

    nt.links.new(tc.outputs["Object"], noise.inputs["Vector"])
    nt.links.new(noise.outputs["Fac"], rm.inputs["Value"])
    nt.links.new(rm.outputs["Result"], bsdf.inputs["Roughness"])
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat


def _make_architectural_glass(name="Mat_CurtainWallGlass"):
    mat = bpy.data.materials.new(name)
    nt = ensure_material_node_tree(mat)
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = (0.68, 0.78, 0.84, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.025
    bsdf.inputs["IOR"].default_value = 1.52
    set_principled_input(bsdf, ("Transmission Weight", "Transmission"), 0.82)
    set_principled_input(bsdf, ("Coat Weight", "Clearcoat"), 0.35)
    set_principled_input(bsdf, ("Coat Roughness", "Clearcoat Roughness"), 0.02)
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat


def _make_warm_emitter(name="Mat_InteriorWarmLED", color=(1.0, 0.72, 0.38, 1.0), strength=14.0):
    mat = bpy.data.materials.new(name)
    nt = ensure_material_node_tree(mat)
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = color
    set_principled_input(bsdf, ("Emission Color", "Emission"), color)
    set_principled_input(bsdf, ("Emission Strength",), strength)
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat


def _make_damp_plaza(name="Mat_DampPlaza"):
    mat = bpy.data.materials.new(name)
    nt = ensure_material_node_tree(mat)
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = (0.055, 0.062, 0.072, 1.0)
    set_principled_input(bsdf, ("Coat Roughness", "Clearcoat Roughness"), 0.06)

    tc = nt.nodes.new("ShaderNodeTexCoord")
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 2.8
    noise.inputs["Detail"].default_value = 8.0
    rm_rough = nt.nodes.new("ShaderNodeMapRange")
    rm_rough.inputs["To Min"].default_value = 0.14
    rm_rough.inputs["To Max"].default_value = 0.40
    rm_coat = nt.nodes.new("ShaderNodeMapRange")
    rm_coat.inputs["To Min"].default_value = 0.10
    rm_coat.inputs["To Max"].default_value = 0.45

    nt.links.new(tc.outputs["Object"], noise.inputs["Vector"])
    nt.links.new(noise.outputs["Fac"], rm_rough.inputs["Value"])
    nt.links.new(noise.outputs["Fac"], rm_coat.inputs["Value"])
    nt.links.new(rm_rough.outputs["Result"], bsdf.inputs["Roughness"])
    coat = bsdf.inputs.get("Coat Weight") or bsdf.inputs.get("Clearcoat")
    if coat is not None:
        nt.links.new(rm_coat.outputs["Result"], coat)
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat


def _create_beveled_box(name, size_xyz, center_xyz, mat, collection, bevel_w=0.014, segments=2):
    """Create a real-world beveled solid mesh (never a razor-sharp raw primitive)."""
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


def build_example_scene(out_blend: str, render_png: str = "", samples: int = 48) -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.name = "Example01_ArchBay"
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 1280
    scene.render.image_settings.file_format = "PNG"
    set_agx_view_transform(scene, look="AgX - Medium High Contrast", exposure=-0.15)

    col_hero = bpy.data.collections.new("03_HERO_ARCH_BAY")
    col_env = bpy.data.collections.new("02_ENVIRONMENT")
    col_rig = bpy.data.collections.new("00_CAMERAS_LIGHTS")
    for c in (col_rig, col_env, col_hero):
        scene.collection.children.link(c)

    m_conc = _make_pbr_concrete()
    m_metal = _make_anodized_metal()
    m_glass = _make_architectural_glass()
    m_led = _make_warm_emitter()
    m_plaza = _make_damp_plaza()

    bw = SPEC["bay_width"]
    bd = SPEC["bay_depth"]
    fh = SPEC["floor_height"]
    nf = SPEC["floors"]
    ph = SPEC["plinth_height"]
    pw = SPEC["pier_width"]
    pd = SPEC["pier_depth"]
    total_h = ph + nf * fh
    bev = SPEC["bevel_width"]

    # Ground plaza apron
    _create_beveled_box("Env_DampPlaza", (44.0, 44.0, 0.2), (0.0, 0.0, -0.1), m_plaza, col_env, bevel_w=0.0)

    # Tier 1 (Macro): Entry granite plinth + structural side piers + roof parapet
    _create_beveled_box("Hero_GranitePlinth", (bw + 1.4, bd + 1.4, ph), (0.0, 0.0, ph * 0.5), m_conc, col_hero, bevel_w=0.025)
    for side, sx in (("L", -(bw * 0.5 - pw * 0.5)), ("R", bw * 0.5 - pw * 0.5)):
        _create_beveled_box(
            f"Hero_StructuralPier_{side}",
            (pw, pd, nf * fh + 0.6),
            (sx, -(bd * 0.5 - pd * 0.5), ph + (nf * fh + 0.6) * 0.5),
            m_conc,
            col_hero,
            bevel_w=bev,
        )
    # Rear enclosure walls + roof slab for true behind-glass interior depth
    _create_beveled_box("Hero_BackWall", (bw, 0.35, nf * fh), (0.0, bd * 0.5 - 0.175, ph + nf * fh * 0.5), m_conc, col_hero, bevel_w=bev)
    for side, sx in (("L", -(bw * 0.5 - 0.18)), ("R", bw * 0.5 - 0.18)):
        _create_beveled_box(f"Hero_SideWall_{side}", (0.36, bd, nf * fh), (sx, 0.0, ph + nf * fh * 0.5), m_conc, col_hero, bevel_w=bev)
    _create_beveled_box("Hero_RoofParapet", (bw + 0.3, bd + 0.3, 0.55), (0.0, 0.0, total_h + 0.275), m_conc, col_hero, bevel_w=0.02)

    # Tier 2 (Meso): Floor slabs, recessed curtain-wall mullions, transoms & architectural glass
    inner_w = bw - 2.0 * pw
    glass_y = -(bd * 0.5 - SPEC["glass_recess"])
    for fl in range(nf):
        z_base = ph + fl * fh
        _create_beveled_box(f"Hero_FloorSlab_{fl}", (bw - 0.1, bd - 0.2, 0.28), (0.0, 0.05, z_base + 0.14), m_conc, col_hero, bevel_w=0.01)
        _create_beveled_box(
            f"Hero_Transom_{fl}",
            (inner_w, SPEC["mullion_d"], SPEC["transom_h"]),
            (0.0, glass_y - 0.04, z_base + fh - SPEC["transom_h"] * 0.5),
            m_metal,
            col_hero,
            bevel_w=0.008,
        )
        # Warm interior architectural ceiling light Cove (true behind-glass luminance)
        _create_beveled_box(
            f"Hero_InteriorLightBar_{fl}",
            (inner_w - 0.9, 0.26, 0.07),
            (0.0, glass_y + 1.25, z_base + fh - 0.36),
            m_led,
            col_hero,
            bevel_w=0.005,
        )
        # Interior architectural interior column/desk silhouette
        _create_beveled_box(
            f"Hero_InteriorDesk_{fl}",
            (inner_w * 0.58, 0.85, 0.76),
            (0.0, glass_y + 1.55, z_base + 0.28 + 0.38),
            m_conc,
            col_hero,
            bevel_w=0.012,
        )

    # Tier 3 (Micro): Vertical anodized mullions + thin double-pane glass sheet
    mc = SPEC["mullion_count"]
    for i in range(mc + 1):
        mx = -inner_w * 0.5 + (inner_w * i / mc)
        _create_beveled_box(
            f"Hero_Mullion_{i}",
            (SPEC["mullion_w"], SPEC["mullion_d"], nf * fh),
            (mx, glass_y - 0.04, ph + nf * fh * 0.5),
            m_metal,
            col_hero,
            bevel_w=0.006,
        )
    _create_beveled_box(
        "Hero_CurtainWallGlass",
        (inner_w - 0.04, 0.03, nf * fh - 0.08),
        (0.0, glass_y + 0.02, ph + nf * fh * 0.5),
        m_glass,
        col_hero,
        bevel_w=0.002,
    )

    # Blue-hour Nishita physical sky + glossy-safe warm grazing sun
    world = bpy.data.worlds.new("BlueHourWorld")
    scene.world = world
    wnt = ensure_world_node_tree(world)
    wnt.nodes.clear()
    w_out = wnt.nodes.new("ShaderNodeOutputWorld")
    w_bg = wnt.nodes.new("ShaderNodeBackground")
    w_bg.inputs["Strength"].default_value = 0.28
    w_sky = wnt.nodes.new("ShaderNodeTexSky")
    configure_physical_sky(w_sky, sun_elevation_deg=2.8, sun_rotation_deg=52.0, sun_disc=False)
    wnt.links.new(w_sky.outputs["Color"], w_bg.inputs["Color"])
    wnt.links.new(w_bg.outputs["Background"], w_out.inputs["Surface"])

    sun_data = bpy.data.lights.new("Sun_BlueHour", type="SUN")
    sun_data.energy = 1.6
    sun_data.angle = math.radians(6.5)
    sun_data.color = (1.0, 0.72, 0.48)
    sun_obj = bpy.data.objects.new("Sun_BlueHour", sun_data)
    sun_obj.rotation_euler = (math.radians(82), 0.0, math.radians(52))
    set_object_ray_visibility(sun_obj, camera=False, glossy=False, diffuse=True)
    col_rig.objects.link(sun_obj)

    # Hero 35mm architectural camera aimed cleanly at bay center
    target = bpy.data.objects.new("Target_Bay", None)
    target.location = (0.0, 0.0, total_h * 0.48)
    col_rig.objects.link(target)

    cam_data = bpy.data.cameras.new("Cam_ArchHero_35mm")
    cam_data.lens = 35.0
    cam_data.sensor_fit = "HORIZONTAL"
    cam_data.sensor_width = 36.0
    cam_data.clip_start = 0.1
    cam_data.clip_end = 500.0
    cam_data.dof.use_dof = True
    cam_data.dof.focus_object = target
    cam_data.dof.aperture_fstop = 5.6
    cam_obj = bpy.data.objects.new("Cam_ArchHero_35mm", cam_data)
    cam_obj.location = (7.8, -16.5, 4.2)
    con = cam_obj.constraints.new("TRACK_TO")
    con.target = target
    con.track_axis = "TRACK_NEGATIVE_Z"
    con.up_axis = "UP_Y"
    col_rig.objects.link(cam_obj)
    scene.camera = cam_obj

    activate_optix_gpu(scene, tile_size=1024, samples=samples, res_percent=100)
    setup_cinema_compositor(
        scene,
        glare_type="Bloom",
        glare_strength=0.22,
        add_streaks=True,
        streaks_threshold=3.5,
        streaks_strength=0.18,
        color_balance_fac=0.22,
        lift=(0.985, 0.995, 1.015, 1.0),
        gamma=(1.0, 1.0, 1.0, 1.0),
        gain=(1.02, 1.0, 0.975, 1.0),
    )

    out_abs = os.path.abspath(out_blend)
    os.makedirs(os.path.dirname(out_abs), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=out_abs)
    print(f"[EXAMPLE_SAVED] {out_abs}", flush=True)

    if render_png:
        png_abs = os.path.abspath(render_png)
        os.makedirs(os.path.dirname(png_abs), exist_ok=True)
        scene.render.filepath = png_abs
        bpy.ops.render.render(write_still=True)
        print(f"[EXAMPLE_RENDERED] {png_abs}", flush=True)


if __name__ == "__main__":
    argv = sys.argv
    if "--" in argv:
        parser = argparse.ArgumentParser(prog="01_photoreal_architectural_bay.py")
        parser.add_argument("--out", required=True, help="Output .blend path.")
        parser.add_argument("--render", default="", help="Optional PNG render path.")
        parser.add_argument("--samples", type=int, default=48, help="Cycles samples (default: 48).")
        opts = parser.parse_args(argv[argv.index("--") + 1 :])
        build_example_scene(opts.out, render_png=opts.render, samples=opts.samples)
