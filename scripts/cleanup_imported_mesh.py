"""Cleanup & game-ready conversion pipeline for imported AI-generated or scanned 3D meshes (.glb/.fbx/.obj).

Turns raw meshes from Tripo3D, ahujasid/camera-to-blender, Meshy, Hunyuan3D, or photogrammetry
into clean, engine-ready assets for UE5 / Unity / Godot / WebGL or Cycles look-dev:
  - Imports .glb / .gltf / .fbx / .obj cleanly
  - Merges by distance, removes loose geometry, recalculates outward normals
  - Normalizes real-world height (--target-height) and snaps pivot to bottom-center (z=0)
  - Decimates overly dense scans to a target triangle budget (--target-tris)
  - Generates clean UV0 + optional Lightmap UV1, LOD1/LOD2, and UE5 UCX_ collision hull
  - Exports clean .glb / .fbx and/or .blend
"""

import argparse
import os
import sys
from typing import List

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from game_asset_pipeline import (
    add_weighted_normals,
    ensure_game_uvs,
    export_game_assets,
    generate_lods,
    generate_ue_collision_hull,
)


def _import_mesh_file(path: str) -> List[bpy.types.Object]:
    abs_p = os.path.abspath(path)
    ext = os.path.splitext(abs_p)[1].lower()
    before = set(bpy.data.objects)

    if ext in (".glb", ".gltf"):
        bpy.ops.import_scene.gltf(filepath=abs_p)
    elif ext == ".fbx":
        bpy.ops.import_scene.fbx(filepath=abs_p)
    elif ext == ".obj":
        if hasattr(bpy.ops.wm, "obj_import"):
            bpy.ops.wm.obj_import(filepath=abs_p)
        else:
            bpy.ops.import_scene.obj(filepath=abs_p)
    else:
        raise ValueError(f"Unsupported mesh format {ext!r}; supported: .glb, .gltf, .fbx, .obj")

    return [o for o in bpy.data.objects if o not in before and o.type == "MESH"]


def _tri_count(mesh: bpy.types.Mesh) -> int:
    return sum(max(0, len(p.vertices) - 2) for p in mesh.polygons)


def cleanup_imported_asset(
    input_path: str,
    asset_name: str = "CleanedAsset",
    target_height: float = 0.0,
    target_tris: int = 0,
    merge_dist: float = 0.0005,
    reunwrap: bool = False,
    lightmap_uv: bool = False,
    weighted_normals: bool = False,
    lods: str = "",
    collision: bool = False,
    out_blend: str = "",
    export_glb: str = "",
    export_fbx: str = "",
) -> bpy.types.Object:
    """Import, weld/recalc normals, rescale, ground pivot, decimate, unwrap, and export a clean game asset."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.name = f"Cleanup_{asset_name}"

    imported = _import_mesh_file(input_path)
    if not imported:
        raise RuntimeError(f"No mesh objects found in {input_path}")

    # Bake world transforms and join into one clean hero mesh
    depsgraph = bpy.context.evaluated_depsgraph_get()
    baked_objs: List[bpy.types.Object] = []
    for src in imported:
        eval_obj = src.evaluated_get(depsgraph)
        m = bpy.data.meshes.new_from_object(eval_obj)
        m.transform(src.matrix_world)
        o = bpy.data.objects.new(f"_clean_{src.name}", m)
        scene.collection.objects.link(o)
        baked_objs.append(o)

    for src in list(bpy.data.objects):
        if src not in baked_objs:
            bpy.data.objects.remove(src, do_unlink=True)

    bpy.ops.object.select_all(action="DESELECT")
    for o in baked_objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = baked_objs[0]
    if len(baked_objs) > 1:
        bpy.ops.object.join()

    hero = bpy.context.active_object
    hero.name = f"{asset_name}_LOD0"
    hero.matrix_world = Matrix.Identity(4)

    # Weld near-duplicate vertices, remove loose verts/edges, fix inverted normals
    bm = bmesh.new()
    bm.from_mesh(hero.data)
    if merge_dist > 0.0:
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=float(merge_dist))
    loose_verts = [v for v in bm.verts if not v.link_faces]
    if loose_verts:
        bmesh.ops.delete(bm, geom=loose_verts, context="VERTS")
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(hero.data)
    bm.free()

    # Normalize height (if requested) and ground pivot to bottom-center (0, 0, 0)
    verts = hero.data.vertices
    if verts:
        xs = [v.co.x for v in verts]
        ys = [v.co.y for v in verts]
        zs = [v.co.z for v in verts]
        cur_h = max(1e-6, max(zs) - min(zs))
        offset = Vector(((min(xs) + max(xs)) * 0.5, (min(ys) + max(ys)) * 0.5, min(zs)))
        hero.data.transform(Matrix.Translation(-offset))
        if target_height > 0.0:
            s = float(target_height) / cur_h
            hero.data.transform(Matrix.Diagonal((s, s, s, 1.0)))
        hero.data.update()

    # Optional decimation to target triangle budget
    tris_before = _tri_count(hero.data)
    if target_tris > 0 and tris_before > target_tris:
        ratio = max(0.02, float(target_tris) / float(tris_before))
        mod = hero.modifiers.new(name="CleanupDecimate", type="DECIMATE")
        mod.decimate_type = "COLLAPSE"
        mod.ratio = ratio
        bpy.ops.object.select_all(action="DESELECT")
        hero.select_set(True)
        bpy.context.view_layer.objects.active = hero
        bpy.ops.object.modifier_apply(modifier=mod.name)

    tris_after = _tri_count(hero.data)
    ensure_game_uvs([hero], reunwrap=reunwrap, add_lightmap_uv=lightmap_uv)
    if weighted_normals:
        add_weighted_normals([hero])

    export_list = [hero]
    if lods:
        ratios = [float(x.strip()) for x in lods.split(",") if x.strip()]
        export_list.extend(generate_lods(scene, hero, ratios))
    if collision:
        export_list.append(generate_ue_collision_hull(scene, hero))

    if export_glb or export_fbx:
        export_game_assets(export_list, glb_path=export_glb, fbx_path=export_fbx)

    if out_blend:
        out_b = os.path.abspath(out_blend)
        os.makedirs(os.path.dirname(out_b), exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=out_b)
        print(f"[CLEANUP_BLEND_SAVED] {out_b}", flush=True)

    print(
        f"[MESH_CLEANED] {hero.name}: tris {tris_before:,} -> {tris_after:,} | "
        f"uv_layers={len(hero.data.uv_layers)} | exported={len(export_list)} obj(s)",
        flush=True,
    )
    return hero


def _parse_cli(args):
    parser = argparse.ArgumentParser(
        prog="cleanup_imported_mesh.py",
        description="Clean and optimize imported AI-generated or scanned 3D meshes (.glb/.fbx/.obj) for game engines.",
    )
    parser.add_argument("--input", required=True, help="Path to source .glb/.gltf/.fbx/.obj mesh.")
    parser.add_argument("--asset-name", default="CleanedAsset", help="Output asset name.")
    parser.add_argument("--target-height", type=float, default=0.0, help="Normalize real-world height in meters (0=keep).")
    parser.add_argument("--target-tris", type=int, default=0, help="Optional maximum triangle budget via Collapse Decimate.")
    parser.add_argument("--merge-dist", type=float, default=0.0005, help="Vertex weld threshold in meters.")
    parser.add_argument("--reunwrap", action="store_true", help="Force fresh Smart UV Project on UV0.")
    parser.add_argument("--lightmap-uv", action="store_true", help="Also generate UVMap_Lightmap (UV1).")
    parser.add_argument("--weighted-normals", action="store_true", help="Add Weighted Normal modifier.")
    parser.add_argument("--lods", default="", help="Comma-separated LOD ratios (e.g. '0.5,0.2').")
    parser.add_argument("--collision", action="store_true", help="Generate UE5 UCX_<Name> convex collision hull.")
    parser.add_argument("--out-blend", default="", help="Optional cleaned .blend output path.")
    parser.add_argument("--export-glb", default="", help="Optional cleaned .glb export path.")
    parser.add_argument("--export-fbx", default="", help="Optional cleaned .fbx export path.")
    return parser.parse_args(args)


if __name__ == "__main__":
    argv = sys.argv
    if "--" in argv:
        opts = _parse_cli(argv[argv.index("--") + 1 :])
        cleanup_imported_asset(
            input_path=opts.input,
            asset_name=opts.asset_name,
            target_height=opts.target_height,
            target_tris=opts.target_tris,
            merge_dist=opts.merge_dist,
            reunwrap=opts.reunwrap,
            lightmap_uv=opts.lightmap_uv,
            weighted_normals=opts.weighted_normals,
            lods=opts.lods,
            collision=opts.collision,
            out_blend=opts.out_blend,
            export_glb=opts.export_glb,
            export_fbx=opts.export_fbx,
        )
