"""Configurable Blender 5.2+ cinema master rig builder and optional Horizon-Arch Macro optical solver."""

import math
import os
import sys
import bpy
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from optix_render_utils import activate_optix_gpu


def hex_to_linear_rgb(hex_str):
    h = hex_str.lstrip("#")
    srgb = [int(h[i : i + 2], 16) / 255.0 for i in (0, 2, 4)]

    def s2l(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    return (s2l(srgb[0]), s2l(srgb[1]), s2l(srgb[2]), 1.0)


def set_action_linear(action):
    """Set LINEAR keyframe interpolation across both Blender 5.0+ slotted actions and legacy fcurves."""
    if not action:
        return
    fcurves = getattr(action, "fcurves", None)
    if fcurves is None and hasattr(action, "layers"):
        for layer in action.layers:
            for strip in layer.strips:
                for bag in getattr(strip, "channelbags", []):
                    for fc in bag.fcurves:
                        for kp in fc.keyframe_points:
                            kp.interpolation = "LINEAR"
    elif fcurves is not None:
        for fc in fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = "LINEAR"


def build_master_rig(
    out_blend,
    res_x=1440,
    res_y=2560,
    fps=60,
    bg_hex="#050506",
    base_lens=85.0,
    samples=80,
):
    """Create a configurable master_rig.blend with dual cameras, R=1.0m guides, AgX, and split world lighting."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.name = "Master_Cinema_Rig"
    scene.render.resolution_x = res_x
    scene.render.resolution_y = res_y
    scene.render.fps = fps
    scene.render.fps_base = 1.0
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.color_depth = "8"
    scene.render.image_settings.compression = 15
    scene.render.use_motion_blur = True
    scene.render.motion_blur_shutter = 0.50

    activate_optix_gpu(scene, tile_size=1024, samples=samples, res_percent=100)

    # Realistic optical light bounces
    scene.cycles.max_bounces = 10
    scene.cycles.diffuse_bounces = 4
    scene.cycles.glossy_bounces = 6
    scene.cycles.transmission_bounces = 10
    scene.cycles.volume_bounces = 3
    scene.cycles.transparent_max_bounces = 8
    scene.cycles.caustics_reflective = True
    scene.cycles.caustics_refractive = True
    scene.cycles.sample_clamp_indirect = 10.0

    # AgX color management
    scene.view_settings.view_transform = "AgX"
    try:
        scene.view_settings.look = "AgX - Medium High Contrast"
    except Exception:
        pass
    scene.view_settings.exposure = 0.0
    scene.view_settings.gamma = 1.0

    col_rig = bpy.data.collections.new("00_MASTER_RIG")
    col_lights = bpy.data.collections.new("01_STUDIO_LIGHTS")
    col_guides = bpy.data.collections.new("02_ANCHOR_GUIDES")
    col_hero = bpy.data.collections.new("03_HERO_ASSET")
    for c in (col_rig, col_lights, col_guides, col_hero):
        scene.collection.children.link(c)

    # Calibrated baseline camera distance mapping R=1.0m circle cleanly at origin
    D = 3.0 * (base_lens / 36.0)

    def make_cam(name, loc, rot_deg):
        cam_data = bpy.data.cameras.new(name)
        cam_data.lens = base_lens
        cam_data.sensor_fit = "HORIZONTAL"
        cam_data.sensor_width = 36.0
        cam_data.clip_start = 0.05
        cam_data.clip_end = 100.0
        cam_data.dof.use_dof = True
        cam_data.dof.focus_distance = D
        cam_data.dof.aperture_fstop = 4.0
        cam_obj = bpy.data.objects.new(name, cam_data)
        cam_obj.location = loc
        cam_obj.rotation_euler = tuple(math.radians(a) for a in rot_deg)
        col_rig.objects.link(cam_obj)
        return cam_obj

    cam_top = make_cam("Cam_TopDown", (0.0, 0.0, D), (0.0, 0.0, 0.0))
    make_cam("Cam_Front", (0.0, -D, 0.0), (90.0, 0.0, 0.0))
    scene.camera = cam_top

    # Non-rendering R = 1.000m alignment guides
    def make_guide_circle(name, rot_deg):
        bpy.ops.mesh.primitive_circle_add(vertices=128, radius=1.0, location=(0, 0, 0))
        obj = bpy.context.active_object
        obj.name = name
        obj.rotation_euler = tuple(math.radians(a) for a in rot_deg)
        obj.hide_render = True
        for c in list(obj.users_collection):
            c.objects.unlink(obj)
        col_guides.objects.link(obj)

    make_guide_circle("Guide_Circle_XY_R1m", (0, 0, 0))
    make_guide_circle("Guide_Circle_XZ_R1m", (90, 0, 0))

    # Light-Path Split World Shader: clean backdrop for camera + soft reflections for objects
    world = bpy.data.worlds.new("MasterWorld")
    scene.world = world
    world.use_nodes = True
    nt = world.node_tree
    nt.nodes.clear()
    n_out = nt.nodes.new("ShaderNodeOutputWorld")
    n_bg_cam = nt.nodes.new("ShaderNodeBackground")
    n_bg_cam.name = "BG_Camera"
    n_bg_cam.inputs["Color"].default_value = hex_to_linear_rgb(bg_hex)
    n_bg_cam.inputs["Strength"].default_value = 1.0

    n_bg_env = nt.nodes.new("ShaderNodeBackground")
    n_bg_env.name = "BG_Lighting"
    n_bg_env.inputs["Color"].default_value = (0.04, 0.045, 0.055, 1.0)
    n_bg_env.inputs["Strength"].default_value = 0.35

    n_lp = nt.nodes.new("ShaderNodeLightPath")
    n_mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(n_lp.outputs["Is Camera Ray"], n_mix.inputs["Fac"])
    nt.links.new(n_bg_env.outputs["Background"], n_mix.inputs[1])
    nt.links.new(n_bg_cam.outputs["Background"], n_mix.inputs[2])
    nt.links.new(n_mix.outputs["Shader"], n_out.inputs["Surface"])

    # Baseline 3-point studio lighting (freely customize per shot)
    def add_area_light(name, loc, rot_deg, energy, size, size_y, color=(1.0, 0.97, 0.93)):
        ldata = bpy.data.lights.new(name, type="AREA")
        ldata.energy = energy
        ldata.shape = "RECTANGLE"
        ldata.size = size
        ldata.size_y = size_y
        ldata.color = color
        lobj = bpy.data.objects.new(name, ldata)
        lobj.location = loc
        lobj.rotation_euler = tuple(math.radians(a) for a in rot_deg)
        col_lights.objects.link(lobj)

    add_area_light("Key_Softbox", (-2.6, 2.2, 3.6), (34, -36, -15), energy=260, size=2.4, size_y=1.6, color=(1.0, 0.96, 0.90))
    add_area_light("Rim_Strip", (2.8, -1.8, 1.8), (62, 48, 25), energy=180, size=0.6, size_y=3.2, color=(0.86, 0.93, 1.0))
    add_area_light("Fill_Soft", (0.2, -3.2, 3.0), (42, 0, 0), energy=45, size=3.5, size_y=2.5, color=(0.95, 0.96, 1.0))

    os.makedirs(os.path.dirname(os.path.abspath(out_blend)), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=out_blend)
    print(f"[MASTER_RIG_SAVED] {out_blend} (D={D:.6f}m, {res_x}x{res_y}@{fps}fps, bg={bg_hex})", flush=True)


def solve_shift_y_for_apex(scene, cam, lens_mm, target_v_apex, radius_m=1.0):
    """Exact linear solve for camera.data.shift_y so the R=radius_m top apex lands at normalized v=target_v_apex."""
    cd = cam.data
    cd.lens = lens_mm
    top_pt = cam.matrix_world.to_3x3() @ Vector((0.0, radius_m, 0.0))

    cd.shift_y = 0.0
    bpy.context.view_layer.update()
    v0 = world_to_camera_view(scene, cam, top_pt).y

    cd.shift_y = 0.1
    bpy.context.view_layer.update()
    v1 = world_to_camera_view(scene, cam, top_pt).y

    shift_exact = 0.1 * (target_v_apex - v0) / (v1 - v0)
    cd.shift_y = shift_exact
    bpy.context.view_layer.update()
    v_check = world_to_camera_view(scene, cam, top_pt).y
    return shift_exact, v_check


def apply_horizon_macro_framing(
    scene,
    frame_start,
    frame_end,
    zoom_start=2.08,
    zoom_end=2.15,
    apex_v_start=0.518,
    apex_v_end=0.528,
    radius_comp=1.0,
    exposure_delta=0.0,
    fstop_min=8.0,
    base_lens=None,
):
    """Optional non-destructive Preset A: Horizon-Arch Macro framing + linear breathing push-in."""
    cam = scene.camera
    if not cam or not cam.data:
        return
    cd = cam.data
    ref_lens = base_lens if base_lens is not None else cd.lens

    if cd.dof.use_dof:
        cd.dof.aperture_fstop = max(cd.dof.aperture_fstop, fstop_min)
    if exposure_delta != 0.0:
        scene.view_settings.exposure += exposure_delta

    lens_start = ref_lens * zoom_start * radius_comp
    lens_end = ref_lens * zoom_end * radius_comp
    r_eff = 1.0 / radius_comp

    sh_start, v_chk0 = solve_shift_y_for_apex(scene, cam, lens_start, apex_v_start, radius_m=r_eff)
    sh_end, v_chk1 = solve_shift_y_for_apex(scene, cam, lens_end, apex_v_end, radius_m=r_eff)

    cd.lens = lens_start
    cd.shift_y = sh_start
    cd.keyframe_insert(data_path="lens", frame=frame_start)
    cd.keyframe_insert(data_path="shift_y", frame=frame_start)

    if frame_end > frame_start:
        cd.lens = lens_end
        cd.shift_y = sh_end
        cd.keyframe_insert(data_path="lens", frame=frame_end)
        cd.keyframe_insert(data_path="shift_y", frame=frame_end)

    if cd.animation_data and cd.animation_data.action:
        set_action_linear(cd.animation_data.action)

    print(
        f"[HORIZON_MACRO] {cam.name}: lens {lens_start:.1f}->{lens_end:.1f}mm | "
        f"shift_y {sh_start:+.4f}->{sh_end:+.4f} | apex_v={v_chk0:.4f}->{v_chk1:.4f} | "
        f"exp={scene.view_settings.exposure:+.2f} (delta={exposure_delta:+.2f})",
        flush=True,
    )


if __name__ == "__main__":
    # CLI: blender -b --factory-startup --python cinema_rig_kit.py -- <out.blend> [res_x] [res_y] [fps] [bg_hex]
    argv = sys.argv
    if "--" in argv:
        args = argv[argv.index("--") + 1 :]
        build_master_rig(
            out_blend=args[0],
            res_x=int(args[1]) if len(args) > 1 else 1440,
            res_y=int(args[2]) if len(args) > 2 else 2560,
            fps=int(args[3]) if len(args) > 3 else 60,
            bg_hex=args[4] if len(args) > 4 else "#050506",
        )
