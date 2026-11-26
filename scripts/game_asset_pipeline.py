"""Game-ready asset preparation, procedural PBR->ORM texture baking, LOD/collision builder & glTF/FBX/USD exporter.

Zero external dependencies inside Blender's bundled Python (uses only bpy, bmesh, mathutils, numpy).
Designed for Unreal Engine 5, Unity, Godot 4, and Three.js / WebGL pipelines on Blender 4.2 LTS – 5.2+.

Key capabilities:
  - Clean scale application & pivot snapping (e.g. bottom_center at z=0)
  - Non-overlapping UV0 + optional Lightmap UV1 (Smart UV Project with safe mipmap margins)
  - Weighted Normal shading for crisp hard-surface game silhouettes
  - Metallic-safe Cycles procedural PBR baking (BaseColor, Normal OpenGL/DirectX, AO, Roughness, Metallic)
  - Pure-NumPy ORM channel packing (R=AO, G=Roughness, B=Metallic) + glTF 2.0 Material Output wiring
  - Automatic LOD1/LOD2 decimation tiers & UE5-convention UCX_<Name> convex collision hulls
  - Direct glTF 2.0 (.glb), FBX (.fbx), and USD (.usdc) export
"""

import argparse
import math
import os
import sys
from typing import Dict, List, Optional, Sequence, Tuple

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from blender_compat import ensure_material_node_tree, get_principled_input, set_principled_input
from optix_render_utils import activate_optix_gpu


def _select_only(objs: Sequence[bpy.types.Object], active: Optional[bpy.types.Object] = None) -> None:
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    if active is not None:
        bpy.context.view_layer.objects.active = active
    elif objs:
        bpy.context.view_layer.objects.active = objs[0]


def get_target_meshes(scene, include_env: bool = False, names: Optional[Sequence[str]] = None) -> List[bpy.types.Object]:
    """Select renderable hero meshes (excluding Env_* and UCX_* collision hulls by default)."""
    if names:
        name_set = set(names)
        return [o for o in scene.objects if o.type == "MESH" and o.name in name_set]
    result = []
    for o in scene.objects:
        if o.type != "MESH" or o.hide_render:
            continue
        if o.name.startswith("UCX_") or "_LOD" in o.name:
            continue
        if (not include_env) and o.name.startswith("Env_"):
            continue
        result.append(o)
    return result


def apply_unit_scale(obj: bpy.types.Object) -> None:
    """Bake object scale into mesh geometry cleanly without requiring UI viewport context."""
    sx, sy, sz = obj.scale
    if abs(sx - 1.0) < 1e-5 and abs(sy - 1.0) < 1e-5 and abs(sz - 1.0) < 1e-5:
        return
    if obj.data.users > 1:
        obj.data = obj.data.copy()
    scale_mat = Matrix.Diagonal((sx, sy, sz, 1.0))
    obj.data.transform(scale_mat)
    obj.scale = (1.0, 1.0, 1.0)
    obj.data.update()


def snap_pivot_bottom_center(objs: Sequence[bpy.types.Object]) -> None:
    """Apply unit scale and align each mesh's local origin to its bottom-center (preserving world placement)."""
    for obj in objs:
        apply_unit_scale(obj)
        if obj.data.users > 1:
            obj.data = obj.data.copy()
        if not obj.data.vertices:
            continue
        xs = [v.co.x for v in obj.data.vertices]
        ys = [v.co.y for v in obj.data.vertices]
        zs = [v.co.z for v in obj.data.vertices]
        offset = Vector(((min(xs) + max(xs)) * 0.5, (min(ys) + max(ys)) * 0.5, min(zs)))
        if offset.length < 1e-6:
            continue
        obj.data.transform(Matrix.Translation(-offset))
        obj.location = obj.location + (obj.matrix_world.to_3x3() @ offset)
        obj.data.update()


def ensure_game_uvs(
    objs: Sequence[bpy.types.Object],
    reunwrap: bool = False,
    island_margin: float = 0.008,
    add_lightmap_uv: bool = False,
    lightmap_margin: float = 0.02,
) -> None:
    """Generate clean non-overlapping UV0 (and optional Lightmap UV1) across target meshes."""
    for obj in objs:
        mesh = obj.data
        if mesh.users > 1:
            obj.data = mesh.copy()
            mesh = obj.data
        if len(mesh.polygons) == 0:
            continue

        needs_uv0 = reunwrap or len(mesh.uv_layers) == 0
        if needs_uv0:
            uv0 = mesh.uv_layers[0] if len(mesh.uv_layers) > 0 else mesh.uv_layers.new(name="UVMap")
            mesh.uv_layers.active = uv0
            _select_only([obj], active=obj)
            bpy.ops.object.mode_set(mode="EDIT")
            bpy.ops.mesh.select_all(action="SELECT")
            bpy.ops.uv.smart_project(angle_limit=math.radians(66.0), island_margin=float(island_margin))
            bpy.ops.object.mode_set(mode="OBJECT")

        if add_lightmap_uv:
            lm_uv = mesh.uv_layers.get("UVMap_Lightmap") or mesh.uv_layers.new(name="UVMap_Lightmap")
            mesh.uv_layers.active = lm_uv
            _select_only([obj], active=obj)
            bpy.ops.object.mode_set(mode="EDIT")
            bpy.ops.mesh.select_all(action="SELECT")
            bpy.ops.uv.smart_project(angle_limit=math.radians(66.0), island_margin=float(lightmap_margin))
            bpy.ops.object.mode_set(mode="OBJECT")
            mesh.uv_layers.active = mesh.uv_layers[0]


def add_weighted_normals(objs: Sequence[bpy.types.Object]) -> None:
    """Add Weighted Normal modifier for clean hard-surface shading without high-poly subdivision."""
    for obj in objs:
        if any(m.type == "WEIGHTED_NORMAL" for m in obj.modifiers):
            continue
        mod = obj.modifiers.new(name="WeightedNormal", type="WEIGHTED_NORMAL")
        if hasattr(mod, "keep_sharp"):
            mod.keep_sharp = True


def create_merged_bake_copy(scene, objs: Sequence[bpy.types.Object], name: str = "GameAsset_LOD0") -> bpy.types.Object:
    """Create a clean joined, modifier-applied, unit-scaled copy of hero meshes for single-atlas game baking."""
    depsgraph = bpy.context.evaluated_depsgraph_get()
    temp_objs: List[bpy.types.Object] = []

    for src in objs:
        eval_obj = src.evaluated_get(depsgraph)
        mesh_copy = bpy.data.meshes.new_from_object(eval_obj)
        dup = bpy.data.objects.new(f"_tmp_{src.name}", mesh_copy)
        dup.matrix_world = src.matrix_world.copy()
        scene.collection.objects.link(dup)
        temp_objs.append(dup)

    _select_only(temp_objs, active=temp_objs[0])
    if len(temp_objs) > 1:
        bpy.ops.object.join()

    merged = bpy.context.active_object
    merged.name = name
    # Bake world rotation/scale cleanly while placing pivot at bottom-center on ground
    merged.data.transform(merged.matrix_world)
    merged.matrix_world = Matrix.Identity(4)

    xs = [v.co.x for v in merged.data.vertices]
    ys = [v.co.y for v in merged.data.vertices]
    zs = [v.co.z for v in merged.data.vertices]
    if xs:
        offset = Vector(((min(xs) + max(xs)) * 0.5, (min(ys) + max(ys)) * 0.5, min(zs)))
        merged.data.transform(Matrix.Translation(-offset))
        merged.location = Vector((0.0, 0.0, 0.0))
    merged.data.update()
    return merged


def _img_to_np(img: bpy.types.Image) -> np.ndarray:
    w, h = img.size[0], img.size[1]
    arr = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(arr)
    return arr.reshape((h, w, 4))


def _save_np_image(arr: np.ndarray, out_path: str, colorspace: str = "Non-Color") -> bpy.types.Image:
    h, w, _ = arr.shape
    out_abs = os.path.abspath(out_path)
    os.makedirs(os.path.dirname(out_abs), exist_ok=True)
    img = bpy.data.images.new(os.path.basename(out_abs), width=w, height=h, alpha=True)
    img.colorspace_settings.name = colorspace
    img.pixels.foreach_set(np.clip(arr, 0.0, 1.0).astype(np.float32).ravel())
    img.filepath_raw = out_abs
    img.file_format = "PNG"
    img.save()
    return img


def _set_active_bake_image(mats: Sequence[bpy.types.Material], img: bpy.types.Image) -> List[Tuple[bpy.types.NodeTree, bpy.types.Node]]:
    created = []
    for mat in mats:
        nt = ensure_material_node_tree(mat)
        tex = nt.nodes.new("ShaderNodeTexImage")
        tex.name = "_BakeTargetTemp"
        tex.image = img
        for n in nt.nodes:
            n.select = False
        tex.select = True
        nt.nodes.active = tex
        created.append((nt, tex))
    return created


def _cleanup_temp_nodes(nodes: Sequence[Tuple[bpy.types.NodeTree, bpy.types.Node]]) -> None:
    for nt, node in nodes:
        if node.name in nt.nodes:
            nt.nodes.remove(node)


def _bake_principled_channel_via_emit(
    scene,
    obj: bpy.types.Object,
    mats: Sequence[bpy.types.Material],
    socket_names: Sequence[str],
    fallback_value,
    tex_size: int,
    colorspace: str = "sRGB",
    margin_px: int = 8,
) -> np.ndarray:
    """Metallic-safe baking of any Principled BSDF input by routing it temporarily into Emission -> EMIT bake."""
    saved_links = []
    temp_nodes = []

    for mat in mats:
        nt = ensure_material_node_tree(mat)
        out_node = next((n for n in nt.nodes if n.type == "OUTPUT_MATERIAL"), None)
        bsdf = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if out_node is None or bsdf is None:
            continue

        surf_in = out_node.inputs["Surface"]
        orig_from = surf_in.links[0].from_socket if surf_in.is_linked else None
        saved_links.append((nt, surf_in, orig_from))

        em = nt.nodes.new("ShaderNodeEmission")
        em.inputs["Strength"].default_value = 1.0
        temp_nodes.append((nt, em))

        src_sock = get_principled_input(bsdf, socket_names)
        if src_sock is not None and src_sock.is_linked:
            nt.links.new(src_sock.links[0].from_socket, em.inputs["Color"])
        elif src_sock is not None:
            val = src_sock.default_value
            if isinstance(val, (int, float)):
                em.inputs["Color"].default_value = (float(val), float(val), float(val), 1.0)
            else:
                em.inputs["Color"].default_value = (float(val[0]), float(val[1]), float(val[2]), 1.0)
        else:
            em.inputs["Color"].default_value = fallback_value

        nt.links.new(em.outputs["Emission"], surf_in)

    bake_img = bpy.data.images.new("_BakeEmitTmp", width=tex_size, height=tex_size, alpha=True)
    bake_img.colorspace_settings.name = colorspace
    target_nodes = _set_active_bake_image(mats, bake_img)

    try:
        _select_only([obj], active=obj)
        scene.render.bake.margin = int(margin_px)
        bpy.ops.object.bake(type="EMIT")
        arr = _img_to_np(bake_img)
    finally:
        _cleanup_temp_nodes(target_nodes)
        for nt, surf_in, orig_from in saved_links:
            for lk in list(surf_in.links):
                nt.links.remove(lk)
            if orig_from is not None:
                nt.links.new(orig_from, surf_in)
        _cleanup_temp_nodes(temp_nodes)
        bpy.data.images.remove(bake_img)

    return arr


def _create_gltf_baked_material(
    name: str,
    base_color_path: str,
    orm_path: str,
    normal_path: str,
    emissive_path: Optional[str] = None,
) -> bpy.types.Material:
    """Wire baked BaseColor + ORM (R=AO, G=Roughness, B=Metallic) + Normal into a glTF 2.0 / UE5-ready material."""
    mat = bpy.data.materials.new(name)
    nt = ensure_material_node_tree(mat)
    nt.nodes.clear()

    out = nt.nodes.new("ShaderNodeOutputMaterial")
    out.location = (500, 0)
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (180, 0)
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    # BaseColor (sRGB)
    tex_bc = nt.nodes.new("ShaderNodeTexImage")
    tex_bc.location = (-360, 260)
    img_bc = bpy.data.images.load(os.path.abspath(base_color_path), check_existing=True)
    img_bc.colorspace_settings.name = "sRGB"
    tex_bc.image = img_bc
    nt.links.new(tex_bc.outputs["Color"], bsdf.inputs["Base Color"])

    # ORM Packed (Non-Color: R=AO, G=Roughness, B=Metallic)
    tex_orm = nt.nodes.new("ShaderNodeTexImage")
    tex_orm.location = (-460, -20)
    img_orm = bpy.data.images.load(os.path.abspath(orm_path), check_existing=True)
    img_orm.colorspace_settings.name = "Non-Color"
    tex_orm.image = img_orm

    sep = nt.nodes.new("ShaderNodeSeparateColor")
    sep.location = (-160, -20)
    nt.links.new(tex_orm.outputs["Color"], sep.inputs["Color"])
    nt.links.new(sep.outputs["Green"], bsdf.inputs["Roughness"])
    nt.links.new(sep.outputs["Blue"], bsdf.inputs["Metallic"])

    # glTF 2.0 official Occlusion node group so .glb exports exact ORM occlusionTexture
    gltf_ng = bpy.data.node_groups.get("glTF Material Output")
    if gltf_ng is None:
        gltf_ng = bpy.data.node_groups.new("glTF Material Output", "ShaderNodeTree")
        gltf_ng.interface.new_socket("Occlusion", in_out="INPUT", socket_type="NodeSocketFloat")
    gltf_node = nt.nodes.new("ShaderNodeGroup")
    gltf_node.node_tree = gltf_ng
    gltf_node.location = (180, -320)
    nt.links.new(sep.outputs["Red"], gltf_node.inputs["Occlusion"])

    # Normal Map (Non-Color)
    tex_nrm = nt.nodes.new("ShaderNodeTexImage")
    tex_nrm.location = (-460, -320)
    img_nrm = bpy.data.images.load(os.path.abspath(normal_path), check_existing=True)
    img_nrm.colorspace_settings.name = "Non-Color"
    tex_nrm.image = img_nrm

    nrm_node = nt.nodes.new("ShaderNodeNormalMap")
    nrm_node.location = (-160, -320)
    nt.links.new(tex_nrm.outputs["Color"], nrm_node.inputs["Color"])
    nt.links.new(nrm_node.outputs["Normal"], bsdf.inputs["Normal"])

    # Optional Emissive map
    if emissive_path and os.path.isfile(emissive_path):
        tex_em = nt.nodes.new("ShaderNodeTexImage")
        tex_em.location = (-360, 520)
        img_em = bpy.data.images.load(os.path.abspath(emissive_path), check_existing=True)
        img_em.colorspace_settings.name = "sRGB"
        tex_em.image = img_em
        em_col_sock = get_principled_input(bsdf, ("Emission Color", "Emission"))
        if em_col_sock is not None:
            nt.links.new(tex_em.outputs["Color"], em_col_sock)
        set_principled_input(bsdf, ("Emission Strength",), 1.0)

    return mat


def bake_pbr_and_orm(
    scene,
    obj: bpy.types.Object,
    tex_dir: str,
    asset_name: str = "Asset",
    tex_size: int = 1024,
    bake_samples: int = 16,
    normal_format: str = "opengl",
    margin_px: int = 8,
    bake_emissive: bool = False,
) -> Dict[str, str]:
    """Bake BaseColor, Normal, AO, Roughness, Metallic (and optional Emissive) and pack ORM texture."""
    mats = [m for m in obj.data.materials if m is not None]
    if not mats:
        raise RuntimeError(f"Object {obj.name!r} has no materials to bake.")

    activate_optix_gpu(scene, tile_size=1024, samples=bake_samples, res_percent=100)
    # Use fast non-denoised bake pass for crisp UV edges
    scene.cycles.use_denoising = False
    scene.cycles.samples = int(bake_samples)

    os.makedirs(os.path.abspath(tex_dir), exist_ok=True)
    p_bc = os.path.join(tex_dir, f"{asset_name}_BaseColor.png")
    p_orm = os.path.join(tex_dir, f"{asset_name}_ORM.png")
    p_nrm = os.path.join(tex_dir, f"{asset_name}_Normal.png")
    p_em = os.path.join(tex_dir, f"{asset_name}_Emissive.png")

    # 1. Metallic-safe BaseColor, Roughness, Metallic via temporary Emission routing
    arr_bc = _bake_principled_channel_via_emit(
        scene, obj, mats, ("Base Color",), (0.5, 0.5, 0.5, 1.0), tex_size, colorspace="sRGB", margin_px=margin_px
    )
    arr_rough = _bake_principled_channel_via_emit(
        scene, obj, mats, ("Roughness",), (0.5, 0.5, 0.5, 1.0), tex_size, colorspace="Non-Color", margin_px=margin_px
    )
    arr_metal = _bake_principled_channel_via_emit(
        scene, obj, mats, ("Metallic",), (0.0, 0.0, 0.0, 1.0), tex_size, colorspace="Non-Color", margin_px=margin_px
    )

    # 2. Ambient Occlusion (Cycles native AO bake)
    img_ao = bpy.data.images.new("_BakeAOTmp", width=tex_size, height=tex_size, alpha=True)
    img_ao.colorspace_settings.name = "Non-Color"
    t_ao = _set_active_bake_image(mats, img_ao)
    try:
        _select_only([obj], active=obj)
        scene.render.bake.margin = int(margin_px)
        bpy.ops.object.bake(type="AO")
        arr_ao = _img_to_np(img_ao)
    finally:
        _cleanup_temp_nodes(t_ao)
        bpy.data.images.remove(img_ao)

    # 3. Tangent-Space Normal (OpenGL +Y or DirectX -Y for UE5)
    img_nrm = bpy.data.images.new("_BakeNrmTmp", width=tex_size, height=tex_size, alpha=True)
    img_nrm.colorspace_settings.name = "Non-Color"
    t_nrm = _set_active_bake_image(mats, img_nrm)
    try:
        _select_only([obj], active=obj)
        scene.render.bake.margin = int(margin_px)
        scene.render.bake.normal_space = "TANGENT"
        scene.render.bake.normal_r = "POS_X"
        scene.render.bake.normal_g = "NEG_Y" if normal_format.lower() == "directx" else "POS_Y"
        scene.render.bake.normal_b = "POS_Z"
        bpy.ops.object.bake(type="NORMAL")
        arr_nrm = _img_to_np(img_nrm)
    finally:
        _cleanup_temp_nodes(t_nrm)
        bpy.data.images.remove(img_nrm)

    # 4. Pack ORM: R = AO, G = Roughness, B = Metallic, A = 1.0
    arr_orm = np.ones((tex_size, tex_size, 4), dtype=np.float32)
    arr_orm[:, :, 0] = arr_ao[:, :, 0]
    arr_orm[:, :, 1] = arr_rough[:, :, 0]
    arr_orm[:, :, 2] = arr_metal[:, :, 0]

    _save_np_image(arr_bc, p_bc, colorspace="sRGB")
    _save_np_image(arr_orm, p_orm, colorspace="Non-Color")
    _save_np_image(arr_nrm, p_nrm, colorspace="Non-Color")

    out_paths = {"base_color": p_bc, "orm": p_orm, "normal": p_nrm}

    if bake_emissive:
        img_em = bpy.data.images.new("_BakeEmTmp", width=tex_size, height=tex_size, alpha=True)
        img_em.colorspace_settings.name = "sRGB"
        t_em = _set_active_bake_image(mats, img_em)
        try:
            _select_only([obj], active=obj)
            scene.render.bake.margin = int(margin_px)
            bpy.ops.object.bake(type="EMIT")
            arr_em = _img_to_np(img_em)
        finally:
            _cleanup_temp_nodes(t_em)
            bpy.data.images.remove(img_em)
        _save_np_image(arr_em, p_em, colorspace="sRGB")
        out_paths["emissive"] = p_em

    # Replace procedural materials with single clean baked glTF/UE5-ready PBR material
    baked_mat = _create_gltf_baked_material(
        name=f"Mat_{asset_name}_BakedPBR",
        base_color_path=p_bc,
        orm_path=p_orm,
        normal_path=p_nrm,
        emissive_path=out_paths.get("emissive"),
    )
    obj.data.materials.clear()
    obj.data.materials.append(baked_mat)

    print(
        f"[GAME_BAKE_COMPLETE] size={tex_size}px normal={normal_format} "
        f"maps={list(out_paths.values())}",
        flush=True,
    )
    return out_paths


def generate_lods(scene, base_obj: bpy.types.Object, ratios: Sequence[float]) -> List[bpy.types.Object]:
    """Generate decimated LOD1, LOD2, ... meshes from base_obj (ratio < 1.0)."""
    created: List[bpy.types.Object] = []
    stem = base_obj.name.replace("_LOD0", "")
    for idx, ratio in enumerate(ratios, start=1):
        r = max(0.05, min(0.95, float(ratio)))
        lod_mesh = base_obj.data.copy()
        lod_obj = bpy.data.objects.new(f"{stem}_LOD{idx}", lod_mesh)
        lod_obj.matrix_world = base_obj.matrix_world.copy()
        scene.collection.objects.link(lod_obj)

        mod = lod_obj.modifiers.new(name="LOD_Decimate", type="DECIMATE")
        mod.decimate_type = "COLLAPSE"
        mod.ratio = r
        _select_only([lod_obj], active=lod_obj)
        bpy.ops.object.modifier_apply(modifier=mod.name)
        tris = sum(max(0, len(p.vertices) - 2) for p in lod_obj.data.polygons)
        print(f"[LOD_CREATED] {lod_obj.name}: ratio={r:.2f} tris={tris}", flush=True)
        created.append(lod_obj)
    return created


def generate_ue_collision_hull(scene, base_obj: bpy.types.Object) -> bpy.types.Object:
    """Create an Unreal Engine UCX_<Name> convex collision hull from base_obj."""
    stem = base_obj.name.replace("_LOD0", "")
    bm = bmesh.new()
    bm.from_mesh(base_obj.data)
    res = bmesh.ops.convex_hull(bm, input=bm.verts)
    # Remove interior unused vertices/edges/faces not part of the convex hull boundary
    geom_hull = set(res.get("geom", []))
    for f in list(bm.faces):
        if f not in geom_hull:
            bm.faces.remove(f)
    for e in list(bm.edges):
        if e not in geom_hull:
            bm.edges.remove(e)
    for v in list(bm.verts):
        if v not in geom_hull:
            bm.verts.remove(v)

    col_mesh = bpy.data.meshes.new(f"UCX_{stem}_Mesh")
    bm.to_mesh(col_mesh)
    bm.free()

    col_obj = bpy.data.objects.new(f"UCX_{stem}", col_mesh)
    col_obj.matrix_world = base_obj.matrix_world.copy()
    col_obj.display_type = "WIRE"
    col_obj.hide_render = True
    scene.collection.objects.link(col_obj)
    tris = sum(max(0, len(p.vertices) - 2) for p in col_mesh.polygons)
    print(f"[COLLISION_CREATED] {col_obj.name}: tris={tris}", flush=True)
    return col_obj


def export_game_assets(
    objs: Sequence[bpy.types.Object],
    glb_path: str = "",
    fbx_path: str = "",
    usd_path: str = "",
) -> None:
    """Export selected game-ready meshes to glTF 2.0 (.glb), FBX (.fbx), and/or USD (.usdc)."""
    _select_only(objs, active=objs[0] if objs else None)

    if glb_path:
        out = os.path.abspath(glb_path)
        os.makedirs(os.path.dirname(out), exist_ok=True)
        bpy.ops.export_scene.gltf(
            filepath=out,
            export_format="GLB",
            use_selection=True,
            export_normals=True,
            export_materials="EXPORT",
        )
        print(f"[EXPORT_GLB] {out} ({os.path.getsize(out)} bytes)", flush=True)

    if fbx_path:
        out = os.path.abspath(fbx_path)
        os.makedirs(os.path.dirname(out), exist_ok=True)
        bpy.ops.export_scene.fbx(
            filepath=out,
            use_selection=True,
            apply_scale_options="FBX_SCALE_ALL",
            mesh_smooth_type="FACE",
            path_mode="COPY",
            embed_textures=True,
        )
        print(f"[EXPORT_FBX] {out} ({os.path.getsize(out)} bytes)", flush=True)

    if usd_path:
        out = os.path.abspath(usd_path)
        os.makedirs(os.path.dirname(out), exist_ok=True)
        bpy.ops.wm.usd_export(filepath=out, selected_objects_only=True)
        print(f"[EXPORT_USD] {out} ({os.path.getsize(out)} bytes)", flush=True)


def _parse_cli(args):
    parser = argparse.ArgumentParser(
        prog="game_asset_pipeline.py",
        description="Prepare, unwrap, bake PBR+ORM textures, build LODs/collision, and export game-ready assets.",
    )
    parser.add_argument("--blend", required=True, help="Input .blend file.")
    parser.add_argument("--out-blend", default="", help="Optional output game-ready .blend path.")
    parser.add_argument("--asset-name", default="GameAsset", help="Base asset/texture name prefix.")
    parser.add_argument("--include-env", action="store_true", help="Include Env_* meshes (default: hero meshes only).")
    parser.add_argument("--merge-hero", action="store_true", help="Merge hero meshes into a single draw-call LOD0 mesh.")
    parser.add_argument("--pivot-bottom", action="store_true", help="Apply scale and snap pivot to bottom-center.")
    parser.add_argument("--weighted-normals", action="store_true", help="Add Weighted Normal modifier to meshes.")
    parser.add_argument("--uv", action="store_true", help="Ensure clean non-overlapping UV0 map.")
    parser.add_argument("--reunwrap", action="store_true", help="Force fresh Smart UV Project on UV0.")
    parser.add_argument("--lightmap-uv", action="store_true", help="Also generate UVMap_Lightmap (UV1) for UE5/Unity.")
    parser.add_argument("--bake", action="store_true", help="Bake procedural PBR to BaseColor + ORM + Normal PNGs.")
    parser.add_argument("--bake-emissive", action="store_true", help="Also bake Emissive map.")
    parser.add_argument("--tex-dir", default="./textures", help="Output directory for baked textures.")
    parser.add_argument("--tex-size", type=int, default=1024, help="Texture resolution in px (default: 1024).")
    parser.add_argument("--bake-samples", type=int, default=16, help="Cycles samples for AO/Normal bake (default: 16).")
    parser.add_argument("--normal-format", default="opengl", choices=("opengl", "directx"), help="Normal map green-channel convention.")
    parser.add_argument("--lods", default="", help="Comma-separated decimate ratios for LOD1,LOD2... (e.g. '0.5,0.2').")
    parser.add_argument("--collision", action="store_true", help="Generate UE5 UCX_<Name> convex collision hull.")
    parser.add_argument("--export-glb", default="", help="Optional glTF 2.0 (.glb) export path.")
    parser.add_argument("--export-fbx", default="", help="Optional FBX (.fbx) export path.")
    parser.add_argument("--export-usd", default="", help="Optional USD (.usdc) export path.")
    return parser.parse_args(args)


if __name__ == "__main__":
    argv = sys.argv
    if "--" in argv:
        opts = _parse_cli(argv[argv.index("--") + 1 :])
        bpy.ops.wm.open_mainfile(filepath=os.path.abspath(opts.blend))
        scene = bpy.context.scene

        targets = get_target_meshes(scene, include_env=opts.include_env)
        if not targets:
            raise RuntimeError("No target hero meshes found in scene.")

        export_list: List[bpy.types.Object] = []

        if opts.merge_hero or opts.bake:
            hero = create_merged_bake_copy(scene, targets, name=f"{opts.asset_name}_LOD0")
            # Hide originals so only game-ready hierarchy is exported/audited
            for orig in targets:
                orig.hide_render = True
                orig.hide_viewport = True
            ensure_game_uvs([hero], reunwrap=True, add_lightmap_uv=opts.lightmap_uv)
            if opts.weighted_normals:
                add_weighted_normals([hero])
            if opts.bake:
                bake_pbr_and_orm(
                    scene,
                    hero,
                    tex_dir=opts.tex_dir,
                    asset_name=opts.asset_name,
                    tex_size=opts.tex_size,
                    bake_samples=opts.bake_samples,
                    normal_format=opts.normal_format,
                    bake_emissive=opts.bake_emissive,
                )
            export_list.append(hero)
            if opts.lods:
                ratios = [float(x.strip()) for x in opts.lods.split(",") if x.strip()]
                export_list.extend(generate_lods(scene, hero, ratios))
            if opts.collision:
                export_list.append(generate_ue_collision_hull(scene, hero))
        else:
            if opts.pivot_bottom:
                snap_pivot_bottom_center(targets)
            else:
                for o in targets:
                    apply_unit_scale(o)
            if opts.uv or opts.reunwrap or opts.lightmap_uv:
                ensure_game_uvs(targets, reunwrap=opts.reunwrap, add_lightmap_uv=opts.lightmap_uv)
            if opts.weighted_normals:
                add_weighted_normals(targets)
            export_list.extend(targets)
            if opts.lods:
                ratios = [float(x.strip()) for x in opts.lods.split(",") if x.strip()]
                for t in list(targets):
                    export_list.extend(generate_lods(scene, t, ratios))
            if opts.collision:
                for t in list(targets):
                    export_list.append(generate_ue_collision_hull(scene, t))

        if opts.export_glb or opts.export_fbx or opts.export_usd:
            export_game_assets(export_list, glb_path=opts.export_glb, fbx_path=opts.export_fbx, usd_path=opts.export_usd)

        if opts.out_blend:
            out_b = os.path.abspath(opts.out_blend)
            os.makedirs(os.path.dirname(out_b), exist_ok=True)
            bpy.ops.wm.save_as_mainfile(filepath=out_b)
            print(f"[GAME_BLEND_SAVED] {out_b}", flush=True)
