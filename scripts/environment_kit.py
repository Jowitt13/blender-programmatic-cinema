"""Game-environment & atmospheric look-dev toolkit for Blender 4.2 LTS – 5.2+.

Provides zero-dependency procedural environment builders:
  - 5 Weather & Time-of-Day atmosphere presets (blue_hour, rainy_night, golden_haze,
    snow_dusting, overcast_nordic)
  - Bounded Principled Volume fog box (fast Cycles rendering without infinite-void noise)
  - Procedural multi-octave Terrain / Island heightfield generator
  - Slope- and altitude-filtered instanced asset scatterer (Env_* collections)
"""

import math
import os
import random
import sys
from typing import List, Optional, Sequence, Tuple

import bmesh
import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from blender_compat import (
    configure_physical_sky,
    ensure_material_node_tree,
    ensure_world_node_tree,
    set_agx_view_transform,
    set_object_ray_visibility,
)


WEATHER_PRESETS = (
    "blue_hour",
    "rainy_night",
    "golden_haze",
    "snow_dusting",
    "overcast_nordic",
)


def _get_or_create_collection(scene, name: str) -> bpy.types.Collection:
    col = bpy.data.collections.get(name)
    if col is None:
        col = bpy.data.collections.new(name)
        scene.collection.children.link(col)
    return col


def add_bounded_volumetric_fog(
    scene,
    bounds_xyz: Tuple[float, float, float] = (80.0, 80.0, 28.0),
    center_xyz: Tuple[float, float, float] = (0.0, 0.0, 14.0),
    density: float = 0.008,
    anisotropy: float = 0.62,
    color: Tuple[float, float, float, float] = (0.72, 0.80, 0.92, 1.0),
    name: str = "Env_VolumetricFogBox",
) -> bpy.types.Object:
    """Create a bounded Principled Volume fog domain so Cycles renders clean god-rays without infinite-world noise."""
    col = _get_or_create_collection(scene, "02_ENVIRONMENT")

    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=Vector(bounds_xyz), verts=bm.verts)
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    bm.to_mesh(mesh)
    bm.free()

    obj = bpy.data.objects.new(name, mesh)
    obj.location = center_xyz
    obj.display_type = "WIRE"
    col.objects.link(obj)

    mat = bpy.data.materials.new(f"Mat_{name}")
    nt = ensure_material_node_tree(mat)
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    vol = nt.nodes.new("ShaderNodeVolumePrincipled")
    vol.inputs["Color"].default_value = color
    vol.inputs["Density"].default_value = float(density)
    vol.inputs["Anisotropy"].default_value = float(anisotropy)
    nt.links.new(vol.outputs["Volume"], out.inputs["Volume"])
    obj.data.materials.append(mat)

    print(
        f"[VOLUMETRIC_FOG] {name} bounds={bounds_xyz}m density={density:.4f} anisotropy={anisotropy:.2f}",
        flush=True,
    )
    return obj


def apply_weather_preset(
    scene,
    preset: str = "blue_hour",
    add_fog: bool = True,
    fog_bounds: Tuple[float, float, float] = (90.0, 90.0, 32.0),
) -> None:
    """Configure cross-version physical sky, directional sun, AgX exposure, and optional bounded fog."""
    if preset not in WEATHER_PRESETS:
        raise ValueError(f"Unknown weather preset {preset!r}; choose from {WEATHER_PRESETS}")

    col_lights = _get_or_create_collection(scene, "01_LIGHTING")

    cfg = {
        "blue_hour": {
            "elev": 2.8,
            "rot": 48.0,
            "world_str": 0.30,
            "sun_energy": 1.6,
            "sun_angle": 6.5,
            "sun_col": (1.0, 0.72, 0.48),
            "exp": -0.15,
            "fog_density": 0.005,
            "fog_col": (0.48, 0.62, 0.85, 1.0),
        },
        "rainy_night": {
            "elev": -3.0,
            "rot": 35.0,
            "world_str": 0.14,
            "sun_energy": 0.35,
            "sun_angle": 12.0,
            "sun_col": (0.58, 0.72, 0.95),
            "exp": 0.15,
            "fog_density": 0.011,
            "fog_col": (0.35, 0.45, 0.62, 1.0),
        },
        "golden_haze": {
            "elev": 8.5,
            "rot": 62.0,
            "world_str": 0.55,
            "sun_energy": 3.8,
            "sun_angle": 2.0,
            "sun_col": (1.0, 0.82, 0.58),
            "exp": -0.25,
            "fog_density": 0.008,
            "fog_col": (0.95, 0.80, 0.60, 1.0),
        },
        "snow_dusting": {
            "elev": 14.0,
            "rot": 30.0,
            "world_str": 0.62,
            "sun_energy": 2.2,
            "sun_angle": 8.0,
            "sun_col": (0.86, 0.92, 1.0),
            "exp": -0.35,
            "fog_density": 0.010,
            "fog_col": (0.78, 0.84, 0.92, 1.0),
        },
        "overcast_nordic": {
            "elev": 22.0,
            "rot": 15.0,
            "world_str": 0.50,
            "sun_energy": 0.9,
            "sun_angle": 18.0,
            "sun_col": (0.82, 0.88, 0.95),
            "exp": -0.10,
            "fog_density": 0.009,
            "fog_col": (0.68, 0.74, 0.80, 1.0),
        },
    }[preset]

    world = bpy.data.worlds.new(f"World_{preset}")
    scene.world = world
    nt = ensure_world_node_tree(world)
    nt.nodes.clear()
    n_out = nt.nodes.new("ShaderNodeOutputWorld")
    n_bg = nt.nodes.new("ShaderNodeBackground")
    n_bg.inputs["Strength"].default_value = cfg["world_str"]
    n_sky = nt.nodes.new("ShaderNodeTexSky")
    configure_physical_sky(
        n_sky,
        sun_elevation_deg=max(0.2, cfg["elev"]),
        sun_rotation_deg=cfg["rot"],
        sun_disc=False,
    )
    nt.links.new(n_sky.outputs["Color"], n_bg.inputs["Color"])
    nt.links.new(n_bg.outputs["Background"], n_out.inputs["Surface"])

    # Remove previous WeatherSun if re-applying preset
    old_sun = bpy.data.objects.get("WeatherSun_Key")
    if old_sun is not None:
        bpy.data.objects.remove(old_sun, do_unlink=True)

    ldata = bpy.data.lights.new("WeatherSun_Key", type="SUN")
    ldata.energy = cfg["sun_energy"]
    ldata.angle = math.radians(cfg["sun_angle"])
    ldata.color = cfg["sun_col"]
    lobj = bpy.data.objects.new("WeatherSun_Key", ldata)
    pitch = max(12.0, 90.0 - max(2.0, cfg["elev"]))
    lobj.rotation_euler = (math.radians(pitch), 0.0, math.radians(cfg["rot"]))
    set_object_ray_visibility(lobj, camera=False, glossy=False, diffuse=True)
    col_lights.objects.link(lobj)

    set_agx_view_transform(scene, look="AgX - Medium High Contrast", exposure=cfg["exp"])

    if add_fog:
        add_bounded_volumetric_fog(
            scene,
            bounds_xyz=fog_bounds,
            center_xyz=(0.0, 0.0, fog_bounds[2] * 0.5),
            density=cfg["fog_density"],
            color=cfg["fog_col"],
        )

    print(f"[WEATHER_PRESET] applied={preset} exp={cfg['exp']:+.2f} fog={add_fog}", flush=True)


def generate_terrain_mesh(
    scene,
    name: str = "Env_ProceduralTerrain",
    size_xy: Tuple[float, float] = (60.0, 60.0),
    grid_res: int = 64,
    height_scale: float = 8.5,
    island_falloff: bool = True,
    seed: int = 42,
    material: Optional[bpy.types.Material] = None,
) -> bpy.types.Object:
    """Generate a smooth multi-octave procedural terrain or coastal island mesh (pure NumPy + bmesh)."""
    col = _get_or_create_collection(scene, "02_ENVIRONMENT")
    rng = np.random.default_rng(seed)

    nx = max(8, int(grid_res))
    ny = max(8, int(grid_res))
    xs = np.linspace(-size_xy[0] * 0.5, size_xy[0] * 0.5, nx)
    ys = np.linspace(-size_xy[1] * 0.5, size_xy[1] * 0.5, ny)
    xx, yy = np.meshgrid(xs, ys, indexing="ij")

    # Deterministic trigonometric multi-octave fBm field (zero external noise library required)
    z = np.zeros_like(xx, dtype=np.float64)
    amp = 1.0
    freq = 2.0 * math.pi / max(size_xy)
    for _ in range(5):
        ang = float(rng.uniform(0, 2.0 * math.pi))
        ph1 = float(rng.uniform(0, 2.0 * math.pi))
        ph2 = float(rng.uniform(0, 2.0 * math.pi))
        u = xx * math.cos(ang) - yy * math.sin(ang)
        v = xx * math.sin(ang) + yy * math.cos(ang)
        z += amp * (0.5 * np.sin(u * freq + ph1) * np.cos(v * freq * 1.13 + ph2) + 0.5)
        amp *= 0.5
        freq *= 2.05

    z = (z - z.min()) / max(1e-6, z.max() - z.min())
    z = np.clip(z, 0.0, 1.0) ** 1.35

    if island_falloff:
        rx = xx / (size_xy[0] * 0.48)
        ry = yy / (size_xy[1] * 0.48)
        dist = np.sqrt(rx * rx + ry * ry)
        mask = np.clip(1.0 - dist * dist, 0.0, 1.0) ** 1.6
        z = z * mask * height_scale - 0.35 * (1.0 - mask)
    else:
        z = z * height_scale

    bm = bmesh.new()
    verts = [[bm.verts.new((float(xx[i, j]), float(yy[i, j]), float(z[i, j]))) for j in range(ny)] for i in range(nx)]
    for i in range(nx - 1):
        for j in range(ny - 1):
            f = bm.faces.new((verts[i][j], verts[i + 1][j], verts[i + 1][j + 1], verts[i][j + 1]))
            f.smooth = True

    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    bm.to_mesh(mesh)
    bm.free()

    obj = bpy.data.objects.new(name, mesh)
    if material is not None:
        obj.data.materials.append(material)
    col.objects.link(obj)
    print(f"[TERRAIN_CREATED] {name}: {nx}x{ny} grid, size={size_xy}m, max_h={float(z.max()):.2f}m", flush=True)
    return obj


def scatter_instances_on_surface(
    scene,
    terrain_obj: bpy.types.Object,
    prototype_mesh: bpy.types.Mesh,
    count: int = 80,
    min_z: float = 0.2,
    max_z: float = 100.0,
    max_slope_deg: float = 30.0,
    scale_range: Tuple[float, float] = (0.75, 1.35),
    prefix: str = "Env_Scatter",
    seed: int = 7,
) -> List[bpy.types.Object]:
    """Scatter memory-lightweight mesh instances onto a terrain filtered by altitude and max slope."""
    col = _get_or_create_collection(scene, "02_ENVIRONMENT")
    rng = random.Random(seed)
    min_nz = math.cos(math.radians(max_slope_deg))
    mw = terrain_obj.matrix_world
    rot_m = mw.to_3x3().normalized()

    candidates: List[Vector] = []
    for poly in terrain_obj.data.polygons:
        wn = (rot_m @ poly.normal).normalized()
        if wn.z < min_nz:
            continue
        wc = mw @ poly.center
        if min_z <= wc.z <= max_z:
            candidates.append(wc)

    if not candidates:
        print(f"[SCATTER_WARN] No terrain faces matched z=[{min_z},{max_z}], slope<={max_slope_deg}deg", flush=True)
        return []

    rng.shuffle(candidates)
    placed: List[bpy.types.Object] = []
    for idx, pt in enumerate(candidates[:count]):
        inst = bpy.data.objects.new(f"{prefix}_{idx:03d}", prototype_mesh)
        inst.location = pt
        inst.rotation_euler = (0.0, 0.0, rng.uniform(0.0, 2.0 * math.pi))
        s = rng.uniform(scale_range[0], scale_range[1])
        inst.scale = (s, s, s * rng.uniform(0.88, 1.15))
        col.objects.link(inst)
        placed.append(inst)

    print(f"[SCATTER_COMPLETE] {prefix}: placed {len(placed)} instances on {terrain_obj.name}", flush=True)
    return placed
