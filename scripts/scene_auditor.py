"""Automated pre-render & game-ready .blend scene auditor.

Checks real-world scale, geometry hygiene, PBR physical plausibility, lighting traps, camera framing,
and (with --game-ready) triangle budgets, unit scales, UV layers, and unbaked procedural shaders.
"""

import argparse
import json
import math
import os
import sys
from typing import Any, Dict, List

import bmesh
import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector


PROCEDURAL_NODE_TYPES = {
    "TEX_NOISE",
    "TEX_VORONOI",
    "TEX_WAVE",
    "TEX_MUSGRAVE",
    "TEX_MAGIC",
    "TEX_BRICK",
    "AMBIENT_OCCLUSION",
    "BEVEL",
}


def _rgb_luma(rgba) -> float:
    return 0.2126 * float(rgba[0]) + 0.7152 * float(rgba[1]) + 0.0722 * float(rgba[2])


def audit_scene(
    scene,
    expected_height: float = 0.0,
    game_ready: bool = False,
    max_tris: int = 150000,
) -> Dict[str, Any]:
    """Run deterministic pre-render & optional game-asset compliance diagnostics on the active scene."""
    issues: List[Dict[str, str]] = []

    def _add(level: str, code: str, message: str) -> None:
        issues.append({"level": level, "code": code, "message": message})

    renderable_meshes = [
        obj
        for obj in scene.objects
        if obj.type == "MESH" and not obj.hide_render and obj.visible_get()
    ]
    lights = [obj for obj in scene.objects if obj.type == "LIGHT" and not obj.hide_render]
    cam = scene.camera

    if not renderable_meshes:
        _add("FAIL", "NO_MESHES", "Scene contains zero visible renderable mesh objects.")

    if cam is None and not game_ready:
        _add("FAIL", "NO_CAMERA", "No active scene.camera assigned.")

    min_pt = Vector((1e18, 1e18, 1e18))
    max_pt = Vector((-1e18, -1e18, -1e18))
    total_polys = 0
    total_tris = 0
    total_verts = 0
    hero_tris = 0
    missing_mat_objs: List[str] = []
    sharp_box_objs: List[str] = []
    empty_mesh_objs: List[str] = []
    unapplied_scale_objs: List[str] = []
    missing_uv_objs: List[str] = []

    for obj in renderable_meshes:
        mesh = obj.data
        n_verts = len(mesh.vertices)
        n_polys = len(mesh.polygons)
        n_tris = sum(max(0, len(p.vertices) - 2) for p in mesh.polygons)
        total_verts += n_verts
        total_polys += n_polys
        total_tris += n_tris

        is_env = obj.name.startswith("Env_")
        if not is_env:
            hero_tris += n_tris

        if n_verts == 0 or n_polys == 0:
            empty_mesh_objs.append(obj.name)
            continue

        if not obj.data.materials or all(m is None for m in obj.data.materials):
            missing_mat_objs.append(obj.name)

        if game_ready and not is_env:
            sx, sy, sz = obj.scale
            if abs(sx - 1.0) > 1e-3 or abs(sy - 1.0) > 1e-3 or abs(sz - 1.0) > 1e-3:
                unapplied_scale_objs.append(f"{obj.name}({sx:.2f},{sy:.2f},{sz:.2f})")
            if len(mesh.uv_layers) == 0:
                missing_uv_objs.append(obj.name)

        for corner in obj.bound_box:
            wc = obj.matrix_world @ Vector(corner)
            min_pt.x = min(min_pt.x, wc.x)
            min_pt.y = min(min_pt.y, wc.y)
            min_pt.z = min(min_pt.z, wc.z)
            max_pt.x = max(max_pt.x, wc.x)
            max_pt.y = max(max_pt.y, wc.y)
            max_pt.z = max(max_pt.z, wc.z)

        has_bevel_mod = any(m.type == "BEVEL" for m in obj.modifiers)
        if not has_bevel_mod and 6 <= n_polys <= 24:
            bm = bmesh.new()
            try:
                bm.from_mesh(mesh)
                bm.edges.ensure_lookup_table()
                sharp_edges = sum(
                    1
                    for e in bm.edges
                    if len(e.link_faces) == 2 and math.degrees(e.calc_face_angle(0.0)) >= 80.0
                )
                if sharp_edges >= 8:
                    sharp_box_objs.append(obj.name)
            finally:
                bm.free()

    bbox_size = (0.0, 0.0, 0.0)
    if renderable_meshes and min_pt.x < 1e17:
        dims = max_pt - min_pt
        bbox_size = (round(dims.x, 4), round(dims.y, 4), round(dims.z, 4))
        max_dim = max(dims.x, dims.y, dims.z)
        if max_dim < 0.005:
            _add("WARN", "TINY_SCALE", f"Scene max dimension is {max_dim:.5f}m — verify real-world scale (1 BU = 1m).")
        elif max_dim > 5000.0:
            _add("WARN", "HUGE_SCALE", f"Scene max dimension is {max_dim:.1f}m — check clip_end and floating-point precision.")
        if expected_height > 0.0:
            ratio = dims.z / expected_height if expected_height > 0 else 1.0
            if ratio < 0.5 or ratio > 2.0:
                _add(
                    "WARN",
                    "HEIGHT_MISMATCH",
                    f"Measured scene height {dims.z:.3f}m differs significantly from expected {expected_height:.3f}m.",
                )

    if empty_mesh_objs:
        _add("WARN", "EMPTY_MESHES", f"{len(empty_mesh_objs)} empty mesh(es): {empty_mesh_objs[:5]}")
    if missing_mat_objs:
        _add("WARN", "MISSING_MATERIALS", f"{len(missing_mat_objs)} visible mesh(es) lack materials: {missing_mat_objs[:5]}")
    if sharp_box_objs:
        _add(
            "WARN",
            "UNBEVELED_SHARP_BOXES",
            f"{len(sharp_box_objs)} low-poly box mesh(es) have razor-sharp >=80° edges with no Bevel: {sharp_box_objs[:6]}. "
            "Add Bevel/chamfers or structural framing to avoid CG-toy silhouettes.",
        )

    if game_ready:
        if unapplied_scale_objs:
            _add(
                "FAIL",
                "UNAPPLIED_SCALE",
                f"Hero mesh(es) have non-unit scale (breaks UE5/Unity physics & normals): {unapplied_scale_objs[:6]}. "
                "Run scripts/game_asset_pipeline.py to apply scale.",
            )
        if missing_uv_objs:
            _add(
                "FAIL",
                "MISSING_UV_MAP",
                f"{len(missing_uv_objs)} hero mesh(es) have no UV map: {missing_uv_objs[:6]}. "
                "Run scripts/game_asset_pipeline.py --uv.",
            )
        if max_tris > 0 and hero_tris > max_tris:
            _add(
                "WARN",
                "TRI_BUDGET_EXCEEDED",
                f"Hero triangle count ({hero_tris:,}) exceeds target budget ({max_tris:,}). Generate LODs via --lods.",
            )

    # PBR material physical plausibility & game-bake readiness
    used_mats = set()
    for obj in renderable_meshes:
        if game_ready and obj.name.startswith("Env_"):
            continue
        for mat in obj.data.materials:
            if mat is not None:
                used_mats.add(mat)

    flat_rough_mats: List[str] = []
    albedo_high_mats: List[str] = []
    albedo_low_mats: List[str] = []
    unbaked_proc_mats: List[str] = []

    for mat in sorted(used_mats, key=lambda m: m.name):
        nt = getattr(mat, "node_tree", None)
        if nt is None:
            continue
        node_types = {n.type for n in nt.nodes}
        if game_ready and (node_types & PROCEDURAL_NODE_TYPES) and ("TEX_IMAGE" not in node_types):
            unbaked_proc_mats.append(mat.name)

        for node in nt.nodes:
            if node.type != "BSDF_PRINCIPLED":
                continue
            bc = node.inputs.get("Base Color")
            rough = node.inputs.get("Roughness")
            metal = node.inputs.get("Metallic")
            trans = node.inputs.get("Transmission Weight") or node.inputs.get("Transmission")
            em_str = node.inputs.get("Emission Strength")

            is_emissive = em_str is not None and not em_str.is_linked and float(em_str.default_value) > 0.5
            is_trans = trans is not None and not trans.is_linked and float(trans.default_value) > 0.5
            is_metal = metal is not None and not metal.is_linked and float(metal.default_value) > 0.5

            if bc is not None and not bc.is_linked and not is_emissive and not is_trans:
                luma = _rgb_luma(bc.default_value)
                if not is_metal and luma > 0.85:
                    albedo_high_mats.append(f"{mat.name}(luma={luma:.2f})")
                elif luma < 0.012:
                    albedo_low_mats.append(f"{mat.name}(luma={luma:.3f})")

            if rough is not None and not rough.is_linked and not is_emissive and not is_trans:
                flat_rough_mats.append(mat.name)

    if albedo_high_mats:
        _add("WARN", "IMPOSSIBLE_WHITE_ALBEDO", f"Diffuse albedo exceeds 0.85 linear luminance: {albedo_high_mats[:5]}")
    if albedo_low_mats:
        _add("WARN", "PURE_BLACK_ALBEDO", f"Albedo below 0.012 linear luminance kills shadow detail: {albedo_low_mats[:5]}")
    if flat_rough_mats:
        _add(
            "INFO",
            "UNIFORM_ROUGHNESS",
            f"{len(flat_rough_mats)} material(s) use constant unlinked Roughness ({flat_rough_mats[:5]}).",
        )
    if unbaked_proc_mats:
        _add(
            "WARN",
            "UNBAKED_PROCEDURAL_SHADER",
            f"Material(s) rely on Blender procedural nodes without baked image textures: {unbaked_proc_mats[:5]}. "
            "Game engines (UE5/Unity/Godot) cannot evaluate Blender procedural shaders — run scripts/game_asset_pipeline.py --bake.",
        )

    # Camera frustum coverage audit
    frustum_info: Dict[str, Any] = {}
    if cam is not None and renderable_meshes and min_pt.x < 1e17:
        us, vs, zs = [], [], []
        for obj in renderable_meshes:
            if obj.name.startswith("Env_"):
                continue
            for corner in obj.bound_box:
                wc = obj.matrix_world @ Vector(corner)
                co_ndc = world_to_camera_view(scene, cam, wc)
                us.append(co_ndc.x)
                vs.append(co_ndc.y)
                zs.append(co_ndc.z)

        if us:
            in_front = any(z > cam.data.clip_start for z in zs)
            u_min, u_max = max(0.0, min(us)), min(1.0, max(us))
            v_min, v_max = max(0.0, min(vs)), min(1.0, max(vs))
            cov_w = max(0.0, u_max - u_min)
            cov_h = max(0.0, v_max - v_min)
            area_cov = cov_w * cov_h
            frustum_info = {
                "camera": cam.name,
                "lens_mm": round(cam.data.lens, 2),
                "width_coverage": round(cov_w, 3),
                "height_coverage": round(cov_h, 3),
                "area_coverage": round(area_cov, 3),
                "max_depth_m": round(max(zs), 2),
                "clip_end_m": round(cam.data.clip_end, 2),
            }
            if not game_ready:
                if not in_front or area_cov <= 0.001:
                    _add("FAIL", "HERO_OUT_OF_FRAME", f"Hero geometry is outside {cam.name}'s view frustum.")
                elif area_cov < 0.08:
                    _add("WARN", "HERO_TOO_SMALL", f"Hero covers only {area_cov*100:.1f}% of {cam.name} frame.")
                if max(zs) > cam.data.clip_end:
                    _add("FAIL", "CLIP_END_EXCEEDED", f"Geometry reaches {max(zs):.1f}m > camera clip_end ({cam.data.clip_end:.1f}m).")

    # Lighting & Color Management audit
    if not game_ready:
        if scene.view_settings.view_transform != "AgX":
            _add("WARN", "NON_AGX_COLOR", f"view_transform is '{scene.view_settings.view_transform}', recommended 'AgX'.")
        if not lights and (scene.world is None or getattr(scene.world, "node_tree", None) is None):
            _add("FAIL", "NO_LIGHTING", "No renderable lights and no world shader configured.")

    for lobj in lights:
        if lobj.data.type == "SUN":
            ang_deg = math.degrees(lobj.data.angle)
            if ang_deg > 5.0 and getattr(lobj, "visible_glossy", True):
                _add(
                    "WARN",
                    "WIDE_SUN_GLOSSY_DISC",
                    f"SUN '{lobj.name}' has wide angle ({ang_deg:.1f}°) with visible_glossy=True — casts an artificial white disc on water/glass.",
                )

    fail_count = sum(1 for i in issues if i["level"] == "FAIL")
    warn_count = sum(1 for i in issues if i["level"] == "WARN")
    status = "FAIL" if fail_count > 0 else ("WARN" if warn_count > 0 else "PASS")

    return {
        "status": status,
        "game_ready_mode": game_ready,
        "summary": {
            "renderable_meshes": len(renderable_meshes),
            "total_verts": total_verts,
            "total_polys": total_polys,
            "total_tris": total_tris,
            "hero_tris": hero_tris,
            "lights": len(lights),
            "used_materials": len(used_mats),
            "bbox_size_m": bbox_size,
            "engine": scene.render.engine,
            "view_transform": scene.view_settings.view_transform,
            "resolution": f"{scene.render.resolution_x}x{scene.render.resolution_y}",
            "frustum": frustum_info,
            "fail_count": fail_count,
            "warn_count": warn_count,
        },
        "issues": issues,
    }


def _parse_cli(args):
    parser = argparse.ArgumentParser(prog="scene_auditor.py", description="Pre-render & game-ready Blender scene auditor.")
    parser.add_argument("--blend", required=True, help="Path to .blend file to audit.")
    parser.add_argument("--expected-height", type=float, default=0.0, help="Optional expected hero height in meters.")
    parser.add_argument("--game-ready", action="store_true", help="Enable UE5/Unity/Godot game-asset compliance checks.")
    parser.add_argument("--max-tris", type=int, default=150000, help="Hero triangle budget warning limit in --game-ready mode.")
    parser.add_argument("--json-out", default="", help="Optional path to write JSON audit report.")
    parser.add_argument("--fail-on-error", action="store_true", help="Exit with code 2 if any FAIL issue is found.")
    return parser.parse_args(args)


if __name__ == "__main__":
    argv = sys.argv
    if "--" in argv:
        opts = _parse_cli(argv[argv.index("--") + 1 :])
        bpy.ops.wm.open_mainfile(filepath=os.path.abspath(opts.blend))
        report = audit_scene(
            bpy.context.scene,
            expected_height=opts.expected_height,
            game_ready=opts.game_ready,
            max_tris=opts.max_tris,
        )

        s = report["summary"]
        print(
            f"[SCENE_AUDIT] status={report['status']} game_ready={report['game_ready_mode']} "
            f"meshes={s['renderable_meshes']} hero_tris={s['hero_tris']:,} bbox={s['bbox_size_m']}m "
            f"mats={s['used_materials']} fails={s['fail_count']} warns={s['warn_count']}",
            flush=True,
        )
        if s["frustum"]:
            f = s["frustum"]
            print(
                f"[FRUSTUM] cam={f['camera']} lens={f['lens_mm']}mm "
                f"coverage={f['width_coverage']*100:.0f}%x{f['height_coverage']*100:.0f}% "
                f"(area={f['area_coverage']*100:.1f}%) max_z={f['max_depth_m']}m",
                flush=True,
            )
        for item in report["issues"]:
            print(f"  [{item['level']}] {item['code']}: {item['message']}", flush=True)

        if opts.json_out:
            out_p = os.path.abspath(opts.json_out)
            os.makedirs(os.path.dirname(out_p), exist_ok=True)
            with open(out_p, "w", encoding="utf-8") as fh:
                json.dump(report, fh, indent=2)
            print(f"[AUDIT_JSON_SAVED] {out_p}", flush=True)

        if opts.fail_on_error and report["summary"]["fail_count"] > 0:
            sys.exit(2)
