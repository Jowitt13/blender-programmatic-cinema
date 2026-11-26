"""Blender 4.2–5.2+ photorealistic scene preset builder, aspect framing, compositor setup, and macro optical solver."""

import argparse
import math
import os
import sys
from typing import Optional, Tuple

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from blender_compat import (
    configure_color_balance_lgg,
    configure_glare_node,
    configure_physical_sky,
    create_compositor_tree,
    ensure_material_node_tree,
    ensure_world_node_tree,
    set_action_interpolation,
    set_agx_view_transform,
    set_object_ray_visibility,
    set_principled_input,
)
from optix_render_utils import activate_optix_gpu


PRESET_CHOICES = (
    "studio_product",
    "arch_exterior",
    "arch_interior",
    "diorama_terrain",
    "cinema_macro",
)


def hex_to_linear_rgb(hex_str: str) -> Tuple[float, float, float, float]:
    """Convert an #RRGGBB sRGB hex color to linear RGBA for Blender shader sockets."""
    h = hex_str.lstrip("#")
    if len(h) != 6:
        raise ValueError(f"Expected 6-digit hex color (e.g. '#050506'), got: {hex_str!r}")
    srgb = [int(h[i : i + 2], 16) / 255.0 for i in (0, 2, 4)]

    def _s2l(c: float) -> float:
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    return (_s2l(srgb[0]), _s2l(srgb[1]), _s2l(srgb[2]), 1.0)


def set_action_linear(action) -> int:
    """Backward-compatible wrapper setting LINEAR keyframe interpolation across Blender 4.x/5.x."""
    return set_action_interpolation(action, "LINEAR")


def configure_aspect_framing(
    cam,
    res_x: int,
    res_y: int,
    mode: str = "horizontal_expand",
    base_sensor_width: float = 36.0,
    source_aspect: float = 16.0 / 9.0,
) -> None:
    """Configure camera sensor fit cleanly for aspect-ratio conversions (e.g. 16:9 -> 1:1).

    Modes:
      - 'horizontal_expand': Locks horizontal FOV (`sensor_fit='HORIZONTAL'`) so changing
        16:9 -> 1:1 expands top & bottom sky/foreground while preserving 100% horizontal
        width. Pair with full horizontal resolution (e.g. 1920x1920, NOT 1080x1080) to
        preserve native pixel density.
      - 'vertical_crop': Locks vertical FOV (`sensor_fit='VERTICAL'`) with exact
        `sensor_height = base_sensor_width / source_aspect` (20.25mm for 16:9) so side
        cropping keeps identical vertical framing without Blender's default 24mm 1.185x
        zoom-out trap.
    """
    cd = cam.data
    cd.sensor_width = float(base_sensor_width)

    if mode == "horizontal_expand":
        cd.sensor_fit = "HORIZONTAL"
    elif mode == "vertical_crop":
        cd.sensor_fit = "VERTICAL"
        cd.sensor_height = float(base_sensor_width) / float(source_aspect)
    else:
        raise ValueError(f"Unsupported framing mode {mode!r}; expected 'horizontal_expand' or 'vertical_crop'.")

    print(
        f"[ASPECT_FRAMING] {cam.name}: mode={mode} target={res_x}x{res_y} "
        f"sensor_fit={cd.sensor_fit} width={cd.sensor_width:.2f}mm height={cd.sensor_height:.2f}mm",
        flush=True,
    )


def setup_cinema_compositor(
    scene,
    glare_type: str = "Fog Glow",
    glare_quality: str = "High",
    glare_threshold: float = 1.2,
    glare_strength: float = 0.35,
    glare_size: float = 0.7,
    add_streaks: bool = False,
    streaks_threshold: float = 3.6,
    streaks_strength: float = 0.22,
    streaks_count: int = 4,
    streaks_angle_deg: float = 15.0,
    streaks_fade: float = 0.84,
    color_balance_fac: float = 0.0,
    lift: Tuple[float, float, float, float] = (1.0, 1.0, 1.0, 1.0),
    gamma: Tuple[float, float, float, float] = (1.0, 1.0, 1.0, 1.0),
    gain: Tuple[float, float, float, float] = (1.0, 1.0, 1.0, 1.0),
    group_name: str = "StudioCompositor",
):
    """Build a Blender 4.2–5.2+ compositor tree (Glare + optional Streaks + ColorBalance)."""
    ng, out_node = create_compositor_tree(scene, group_name=group_name)
    rl = ng.nodes.new("CompositorNodeRLayers")
    rl.location = (-400, 0)
    prev_socket = rl.outputs["Image"]
    x_pos = -100

    if glare_strength > 0.0:
        g1 = ng.nodes.new("CompositorNodeGlare")
        g1.name = "Glare_Primary"
        g1.location = (x_pos, 0)
        configure_glare_node(
            g1,
            glare_type=glare_type,
            quality=glare_quality,
            threshold=glare_threshold,
            strength=glare_strength,
            size=glare_size,
        )
        ng.links.new(prev_socket, g1.inputs["Image"])
        prev_socket = g1.outputs["Image"]
        x_pos += 260

    if add_streaks and streaks_strength > 0.0:
        g2 = ng.nodes.new("CompositorNodeGlare")
        g2.name = "Glare_Streaks"
        g2.location = (x_pos, 0)
        configure_glare_node(
            g2,
            glare_type="Streaks",
            quality=glare_quality,
            threshold=streaks_threshold,
            strength=streaks_strength,
            streaks=streaks_count,
            streaks_angle_deg=streaks_angle_deg,
            fade=streaks_fade,
        )
        ng.links.new(prev_socket, g2.inputs["Image"])
        prev_socket = g2.outputs["Image"]
        x_pos += 260

    if color_balance_fac > 0.0:
        cb = ng.nodes.new("CompositorNodeColorBalance")
        cb.name = "ColorBalance_Grade"
        cb.location = (x_pos, 0)
        configure_color_balance_lgg(cb, factor=color_balance_fac, lift=lift, gamma=gamma, gain=gain)
        ng.links.new(prev_socket, cb.inputs[0])
        prev_socket = cb.outputs[0]
        x_pos += 260

    out_node.location = (x_pos, 0)
    ng.links.new(prev_socket, out_node.inputs[0])
    print(
        f"[COMPOSITOR_READY] group={ng.name} glare={glare_type}({glare_strength:.2f}) "
        f"streaks={add_streaks} grade_fac={color_balance_fac:.2f}",
        flush=True,
    )
    return ng


def _setup_split_world(scene, bg_hex: str, env_color=(0.04, 0.045, 0.055, 1.0), env_strength=0.35):
    world = bpy.data.worlds.new("StudioSplitWorld")
    scene.world = world
    nt = ensure_world_node_tree(world)
    nt.nodes.clear()

    n_out = nt.nodes.new("ShaderNodeOutputWorld")
    n_bg_cam = nt.nodes.new("ShaderNodeBackground")
    n_bg_cam.name = "BG_Camera"
    n_bg_cam.inputs["Color"].default_value = hex_to_linear_rgb(bg_hex)
    n_bg_cam.inputs["Strength"].default_value = 1.0

    n_bg_env = nt.nodes.new("ShaderNodeBackground")
    n_bg_env.name = "BG_Lighting"
    n_bg_env.inputs["Color"].default_value = env_color
    n_bg_env.inputs["Strength"].default_value = env_strength

    n_lp = nt.nodes.new("ShaderNodeLightPath")
    n_mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(n_lp.outputs["Is Camera Ray"], n_mix.inputs["Fac"])
    nt.links.new(n_bg_env.outputs["Background"], n_mix.inputs[1])
    nt.links.new(n_bg_cam.outputs["Background"], n_mix.inputs[2])
    nt.links.new(n_mix.outputs["Shader"], n_out.inputs["Surface"])
    return world


def _setup_nishita_sky(scene, sun_elevation_deg=6.0, sun_rotation_deg=42.0, strength=0.45, sun_disc=False):
    world = bpy.data.worlds.new("PhysicalSkyWorld")
    scene.world = world
    nt = ensure_world_node_tree(world)
    nt.nodes.clear()

    n_out = nt.nodes.new("ShaderNodeOutputWorld")
    n_bg = nt.nodes.new("ShaderNodeBackground")
    n_bg.inputs["Strength"].default_value = float(strength)

    n_sky = nt.nodes.new("ShaderNodeTexSky")
    configure_physical_sky(
        n_sky,
        sun_elevation_deg=sun_elevation_deg,
        sun_rotation_deg=sun_rotation_deg,
        sun_disc=sun_disc,
        air_density=1.2,
        dust_density=1.4,
        ozone_density=2.0,
    )

    nt.links.new(n_sky.outputs["Color"], n_bg.inputs["Color"])
    nt.links.new(n_bg.outputs["Background"], n_out.inputs["Surface"])
    return world


def _add_area_light(collection, name, loc, rot_deg, energy, size, size_y, color=(1.0, 0.97, 0.93)):
    ldata = bpy.data.lights.new(name, type="AREA")
    ldata.energy = float(energy)
    ldata.shape = "RECTANGLE"
    ldata.size = float(size)
    ldata.size_y = float(size_y)
    ldata.color = color
    lobj = bpy.data.objects.new(name, ldata)
    lobj.location = loc
    lobj.rotation_euler = tuple(math.radians(a) for a in rot_deg)
    collection.objects.link(lobj)
    return lobj


def _add_sun_light(
    collection,
    name,
    rot_deg,
    energy=2.5,
    angle_deg=2.5,
    color=(1.0, 0.86, 0.68),
    visible_glossy=False,
):
    ldata = bpy.data.lights.new(name, type="SUN")
    ldata.energy = float(energy)
    ldata.angle = math.radians(angle_deg)
    ldata.color = color
    lobj = bpy.data.objects.new(name, ldata)
    lobj.rotation_euler = tuple(math.radians(a) for a in rot_deg)
    set_object_ray_visibility(lobj, camera=False, glossy=visible_glossy, diffuse=True)
    collection.objects.link(lobj)
    return lobj


def _make_camera(
    collection,
    name: str,
    loc: Tuple[float, float, float],
    rot_deg: Optional[Tuple[float, float, float]] = None,
    lens: float = 50.0,
    fstop: float = 4.0,
    focus_dist: float = 5.0,
    use_dof: bool = True,
    clip_end: float = 1000.0,
    shift_y: float = 0.0,
    track_target=None,
):
    cam_data = bpy.data.cameras.new(name)
    cam_data.lens = float(lens)
    cam_data.sensor_fit = "HORIZONTAL"
    cam_data.sensor_width = 36.0
    cam_data.clip_start = 0.05
    cam_data.clip_end = float(clip_end)
    cam_data.shift_y = float(shift_y)
    cam_data.dof.use_dof = bool(use_dof)
    cam_data.dof.focus_distance = float(focus_dist)
    cam_data.dof.aperture_fstop = float(fstop)
    cam_obj = bpy.data.objects.new(name, cam_data)
    cam_obj.location = loc
    if rot_deg is not None:
        cam_obj.rotation_euler = tuple(math.radians(a) for a in rot_deg)
    if track_target is not None:
        con = cam_obj.constraints.new("TRACK_TO")
        con.target = track_target
        con.track_axis = "TRACK_NEGATIVE_Z"
        con.up_axis = "UP_Y"
        cam_data.dof.focus_object = track_target
    collection.objects.link(cam_obj)
    return cam_obj


def _make_damp_plaza_material(name="Mat_DampGranitePlaza"):
    mat = bpy.data.materials.new(name)
    nt = ensure_material_node_tree(mat)
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = (0.065, 0.072, 0.082, 1.0)
    set_principled_input(bsdf, ("Roughness",), 0.32)
    set_principled_input(bsdf, ("Coat Roughness", "Clearcoat Roughness"), 0.07)

    tc = nt.nodes.new("ShaderNodeTexCoord")
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 3.5
    noise.inputs["Detail"].default_value = 8.0
    noise.inputs["Roughness"].default_value = 0.62

    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.35
    ramp.color_ramp.elements[0].color = (0.08, 0.08, 0.08, 1.0)
    ramp.color_ramp.elements[1].position = 0.70
    ramp.color_ramp.elements[1].color = (0.38, 0.38, 0.38, 1.0)

    rough_map = nt.nodes.new("ShaderNodeMapRange")
    rough_map.inputs["From Min"].default_value = 0.2
    rough_map.inputs["From Max"].default_value = 0.8
    rough_map.inputs["To Min"].default_value = 0.16
    rough_map.inputs["To Max"].default_value = 0.42

    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.08
    bump.inputs["Distance"].default_value = 0.01

    nt.links.new(tc.outputs["Object"], noise.inputs["Vector"])
    nt.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(noise.outputs["Fac"], rough_map.inputs["Value"])
    nt.links.new(noise.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(rough_map.outputs["Result"], bsdf.inputs["Roughness"])
    coat_sock = bsdf.inputs.get("Coat Weight") or bsdf.inputs.get("Clearcoat")
    if coat_sock is not None:
        nt.links.new(ramp.outputs["Color"], coat_sock)
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat


def build_master_rig(
    out_blend: str,
    res_x: int = 1920,
    res_y: int = 1920,
    fps: int = 60,
    bg_hex: str = "#050506",
    base_lens: float = 85.0,
    samples: int = 80,
    enable_compositor: bool = False,
    preset: str = "studio_product",
) -> None:
    """Build a photorealistic Cycles master scene from one of 5 reusable presets.

    Presets:
      - 'studio_product': Product/craft hero rig (split obsidian world, 3-point softboxes, 3/4 + front + top cameras)
      - 'arch_exterior': Blue-hour/golden-hour exterior rig (Nishita sky, glossy-safe grazing sun, damp granite plaza, 35mm + 135mm cameras)
      - 'arch_interior': Architectural interior room shell with window bay, raking sunlight + window portal light, 28mm camera
      - 'diorama_terrain': Isometric/aerial miniature world rig (85mm elevated telephoto, directional sky + warm sun)
      - 'cinema_macro': Calibrated R=1.0m macro match-cut rig compatible with apply_horizon_macro_framing()
    """
    if preset not in PRESET_CHOICES:
        raise ValueError(f"Unknown preset {preset!r}; choose from {PRESET_CHOICES}")

    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.name = f"Studio_{preset}"
    scene.render.resolution_x = int(res_x)
    scene.render.resolution_y = int(res_y)
    scene.render.fps = int(fps)
    scene.render.fps_base = 1.0
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.color_depth = "8"
    scene.render.image_settings.compression = 15
    scene.render.use_motion_blur = preset in ("cinema_macro", "arch_exterior")
    scene.render.motion_blur_shutter = 0.35 if preset == "arch_exterior" else 0.50

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

    set_agx_view_transform(scene, look="AgX - Medium High Contrast", exposure=0.0)

    col_rig = bpy.data.collections.new("00_CAMERAS_AND_RIG")
    col_lights = bpy.data.collections.new("01_LIGHTING")
    col_env = bpy.data.collections.new("02_ENVIRONMENT_AND_GUIDES")
    col_hero = bpy.data.collections.new("03_HERO_ASSET")
    for col in (col_rig, col_lights, col_env, col_hero):
        scene.collection.children.link(col)

    target = bpy.data.objects.new("Target_Hero", None)
    target.empty_display_type = "PLAIN_AXES"
    target.location = (0.0, 0.0, 0.0)
    col_rig.objects.link(target)

    if preset == "studio_product":
        _setup_split_world(scene, bg_hex=bg_hex, env_color=(0.05, 0.055, 0.065, 1.0), env_strength=0.40)
        target.location = (0.0, 0.0, 0.35)
        cam_hero = _make_camera(
            col_rig, "Cam_Hero_3Q", loc=(2.4, -3.2, 1.55), lens=base_lens, fstop=5.6, focus_dist=4.1, track_target=target
        )
        _make_camera(col_rig, "Cam_Front", loc=(0.0, -4.0, 0.45), lens=base_lens, fstop=8.0, focus_dist=4.0, track_target=target)
        _make_camera(col_rig, "Cam_TopDown", loc=(0.0, 0.0, 4.2), rot_deg=(0.0, 0.0, 0.0), lens=base_lens, fstop=8.0, focus_dist=4.2)
        scene.camera = cam_hero

        _add_area_light(col_lights, "Key_Softbox", (-2.6, -1.8, 3.2), (48, -32, -30), energy=280, size=2.2, size_y=1.4, color=(1.0, 0.96, 0.90))
        _add_area_light(col_lights, "Rim_Strip", (2.8, 2.0, 2.0), (60, 45, 145), energy=200, size=0.5, size_y=3.0, color=(0.84, 0.92, 1.0))
        _add_area_light(col_lights, "Fill_Soft", (0.4, -3.4, 2.4), (55, 0, 0), energy=45, size=3.4, size_y=2.2, color=(0.95, 0.97, 1.0))

    elif preset == "arch_exterior":
        _setup_nishita_sky(scene, sun_elevation_deg=3.5, sun_rotation_deg=48.0, strength=0.35, sun_disc=False)
        target.location = (0.0, 0.0, 8.0)
        cam_hero = _make_camera(
            col_rig, "Cam_Arch_35mm", loc=(18.0, -26.0, 3.2), lens=35.0, fstop=8.0, focus_dist=32.0, clip_end=5000.0, shift_y=0.06, track_target=target
        )
        _make_camera(
            col_rig, "Cam_Tele_135mm", loc=(28.0, -42.0, 12.0), lens=135.0, fstop=2.8, focus_dist=50.0, clip_end=5000.0, track_target=target
        )
        scene.camera = cam_hero

        _add_sun_light(col_lights, "Sun_BlueHour_Rim", rot_deg=(82.0, 0.0, 48.0), energy=1.8, angle_deg=8.0, color=(1.0, 0.72, 0.45), visible_glossy=False)

        bpy.ops.mesh.primitive_plane_add(size=120.0, location=(0.0, 0.0, 0.0))
        plaza = bpy.context.active_object
        plaza.name = "Env_DampGranitePlaza"
        plaza.data.materials.append(_make_damp_plaza_material())
        for c in list(plaza.users_collection):
            c.objects.unlink(plaza)
        col_env.objects.link(plaza)

    elif preset == "arch_interior":
        _setup_nishita_sky(scene, sun_elevation_deg=18.0, sun_rotation_deg=70.0, strength=0.65, sun_disc=False)
        target.location = (0.0, 1.5, 1.3)
        cam_hero = _make_camera(
            col_rig, "Cam_Interior_28mm", loc=(0.0, -2.6, 1.45), rot_deg=(90.0, 0.0, 0.0), lens=28.0, fstop=5.6, focus_dist=4.2, use_dof=True, shift_y=0.02
        )
        scene.camera = cam_hero

        _add_sun_light(col_lights, "Sun_WindowShaft", rot_deg=(62.0, 0.0, -72.0), energy=4.5, angle_deg=1.5, color=(1.0, 0.91, 0.78), visible_glossy=True)
        _add_area_light(col_lights, "Light_WindowPortal", (-3.95, 0.5, 1.8), (90.0, 0.0, -90.0), energy=220, size=2.6, size_y=2.0, color=(0.88, 0.94, 1.0))

        # Subtle reference floor slab
        bpy.ops.mesh.primitive_plane_add(size=10.0, location=(0.0, 0.0, 0.0))
        floor = bpy.context.active_object
        floor.name = "Env_InteriorFloor"
        floor.data.materials.append(_make_damp_plaza_material("Mat_InteriorFloorBase"))
        for c in list(floor.users_collection):
            c.objects.unlink(floor)
        col_env.objects.link(floor)

    elif preset == "diorama_terrain":
        _setup_nishita_sky(scene, sun_elevation_deg=26.0, sun_rotation_deg=35.0, strength=0.65, sun_disc=False)
        target.location = (0.0, 0.0, 0.5)
        cam_hero = _make_camera(
            col_rig, "Cam_Aerial_85mm", loc=(28.0, -34.0, 26.0), lens=85.0, fstop=5.6, focus_dist=51.0, clip_end=5000.0, track_target=target
        )
        scene.camera = cam_hero
        _add_sun_light(col_lights, "Sun_DioramaKey", rot_deg=(58.0, 0.0, 35.0), energy=3.8, angle_deg=2.2, color=(1.0, 0.95, 0.86), visible_glossy=False)

    elif preset == "cinema_macro":
        _setup_split_world(scene, bg_hex=bg_hex, env_color=(0.04, 0.045, 0.055, 1.0), env_strength=0.35)
        cam_dist = 3.0 * (float(base_lens) / 36.0)
        cam_top = _make_camera(col_rig, "Cam_TopDown", loc=(0.0, 0.0, cam_dist), rot_deg=(0.0, 0.0, 0.0), lens=base_lens, fstop=4.0, focus_dist=cam_dist)
        _make_camera(col_rig, "Cam_Front", loc=(0.0, -cam_dist, 0.0), rot_deg=(90.0, 0.0, 0.0), lens=base_lens, fstop=4.0, focus_dist=cam_dist)
        scene.camera = cam_top

        def _make_guide_circle(name: str, rot_deg: Tuple[float, float, float]):
            bpy.ops.mesh.primitive_circle_add(vertices=128, radius=1.0, location=(0.0, 0.0, 0.0))
            obj = bpy.context.active_object
            obj.name = name
            obj.rotation_euler = tuple(math.radians(a) for a in rot_deg)
            obj.hide_render = True
            for c in list(obj.users_collection):
                c.objects.unlink(obj)
            col_env.objects.link(obj)

        _make_guide_circle("Guide_Circle_XY_R1m", (0.0, 0.0, 0.0))
        _make_guide_circle("Guide_Circle_XZ_R1m", (90.0, 0.0, 0.0))

        _add_area_light(col_lights, "Key_Softbox", (-2.6, 2.2, 3.6), (34, -36, -15), energy=260, size=2.4, size_y=1.6, color=(1.0, 0.96, 0.90))
        _add_area_light(col_lights, "Rim_Strip", (2.8, -1.8, 1.8), (62, 48, 25), energy=180, size=0.6, size_y=3.2, color=(0.86, 0.93, 1.0))
        _add_area_light(col_lights, "Fill_Soft", (0.2, -3.2, 3.0), (42, 0, 0), energy=45, size=3.5, size_y=2.5, color=(0.95, 0.96, 1.0))

    if enable_compositor:
        setup_cinema_compositor(
            scene,
            glare_type="Bloom" if preset == "arch_exterior" else "Fog Glow",
            add_streaks=(preset == "arch_exterior"),
            color_balance_fac=0.25 if preset == "arch_exterior" else 0.0,
            lift=(0.985, 0.995, 1.015, 1.0),
            gamma=(1.0, 1.0, 1.0, 1.0),
            gain=(1.02, 1.00, 0.975, 1.0),
        )

    out_abs = os.path.abspath(out_blend)
    os.makedirs(os.path.dirname(out_abs), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=out_abs)
    print(
        f"[MASTER_RIG_SAVED] preset={preset} path={out_abs} "
        f"({res_x}x{res_y}@{fps}fps, lens={base_lens}mm, compositor={enable_compositor})",
        flush=True,
    )


def solve_shift_y_for_apex(
    scene,
    cam,
    lens_mm: float,
    target_v_apex: float,
    radius_m: float = 1.0,
) -> Tuple[float, float]:
    """Exact linear solve for camera.data.shift_y so the R=radius_m top apex lands at normalized v=target_v_apex."""
    cd = cam.data
    cd.lens = float(lens_mm)
    top_pt = cam.matrix_world.to_3x3() @ Vector((0.0, float(radius_m), 0.0))

    cd.shift_y = 0.0
    bpy.context.view_layer.update()
    v0 = world_to_camera_view(scene, cam, top_pt).y

    cd.shift_y = 0.1
    bpy.context.view_layer.update()
    v1 = world_to_camera_view(scene, cam, top_pt).y

    shift_exact = 0.1 * (float(target_v_apex) - v0) / (v1 - v0)
    cd.shift_y = shift_exact
    bpy.context.view_layer.update()
    v_check = world_to_camera_view(scene, cam, top_pt).y
    return shift_exact, v_check


def apply_horizon_macro_framing(
    scene,
    frame_start: int,
    frame_end: int,
    zoom_start: float = 2.08,
    zoom_end: float = 2.15,
    apex_v_start: float = 0.518,
    apex_v_end: float = 0.528,
    radius_comp: float = 1.0,
    exposure_delta: float = 0.0,
    fstop_min: float = 8.0,
    base_lens: Optional[float] = None,
) -> None:
    """Optional non-destructive Preset: Horizon-Arch Macro framing + linear breathing push-in."""
    cam = scene.camera
    if not cam or not cam.data:
        return
    cd = cam.data
    ref_lens = float(base_lens) if base_lens is not None else float(cd.lens)

    if cd.dof.use_dof:
        cd.dof.aperture_fstop = max(cd.dof.aperture_fstop, float(fstop_min))
    if exposure_delta != 0.0:
        scene.view_settings.exposure += float(exposure_delta)

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


def _parse_cli(args):
    """Support both modern --flags and legacy positional CLI arguments."""
    if args and not args[0].startswith("-"):
        return argparse.Namespace(
            out=args[0],
            res_x=int(args[1]) if len(args) > 1 else 1920,
            res_y=int(args[2]) if len(args) > 2 else 1920,
            fps=int(args[3]) if len(args) > 3 else 60,
            bg=args[4] if len(args) > 4 else "#050506",
            lens=float(args[5]) if len(args) > 5 else 85.0,
            samples=int(args[6]) if len(args) > 6 else 80,
            compositor=False,
            preset="cinema_macro",
        )

    parser = argparse.ArgumentParser(
        prog="cinema_rig_kit.py",
        description="Generate a Blender 4.2–5.2+ photorealistic scene master .blend from reusable presets.",
    )
    parser.add_argument("--out", required=True, help="Output .blend file path.")
    parser.add_argument("--preset", default="studio_product", choices=PRESET_CHOICES, help="Scene archetype preset.")
    parser.add_argument("--res-x", type=int, default=1920, help="Render width in pixels (default: 1920).")
    parser.add_argument("--res-y", type=int, default=1920, help="Render height in pixels (default: 1920).")
    parser.add_argument("--fps", type=int, default=60, help="Timeline frame rate (default: 60).")
    parser.add_argument("--bg", default="#050506", help="Camera backdrop hex color for split-world presets.")
    parser.add_argument("--lens", type=float, default=85.0, help="Baseline focal length in mm (studio/macro presets).")
    parser.add_argument("--samples", type=int, default=80, help="Default Cycles sample count (default: 80).")
    parser.add_argument("--compositor", action="store_true", help="Attach preset-tuned glare & color balance compositor.")
    return parser.parse_args(args)


if __name__ == "__main__":
    argv = sys.argv
    if "--" in argv:
        opts = _parse_cli(argv[argv.index("--") + 1 :])
        build_master_rig(
            out_blend=opts.out,
            res_x=opts.res_x,
            res_y=opts.res_y,
            fps=opts.fps,
            bg_hex=opts.bg,
            base_lens=opts.lens,
            samples=opts.samples,
            enable_compositor=opts.compositor,
            preset=opts.preset,
        )
