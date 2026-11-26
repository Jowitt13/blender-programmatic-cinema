"""Cross-version compatibility shim for Blender 4.2 LTS through Blender 5.2+."""

import math
from typing import Iterable, Optional, Sequence, Tuple

import bpy


BLENDER_VERSION: Tuple[int, int, int] = tuple(bpy.app.version[:3])


def ensure_world_node_tree(world):
    """Return a world's node_tree without triggering Blender 5.2+ deprecation warnings."""
    nt = getattr(world, "node_tree", None)
    if nt is None:
        world.use_nodes = True
        nt = world.node_tree
    return nt


def ensure_material_node_tree(mat):
    """Return a material's node_tree without triggering deprecation warnings."""
    nt = getattr(mat, "node_tree", None)
    if nt is None:
        mat.use_nodes = True
        nt = mat.node_tree
    return nt


def get_eevee_engine_id() -> str:
    """Return the valid EEVEE engine identifier for the running Blender version."""
    enum_items = [
        e.identifier
        for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items
    ]
    for candidate in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        if candidate in enum_items:
            return candidate
    return "BLENDER_EEVEE"


def set_agx_view_transform(
    scene,
    look: str = "AgX - Medium High Contrast",
    exposure: float = 0.0,
    gamma: float = 1.0,
) -> str:
    """Configure AgX color management gracefully across Blender 4.2–5.2+."""
    vs = scene.view_settings
    for vt in ("AgX", "Filmic", "Standard"):
        try:
            vs.view_transform = vt
            break
        except Exception:
            continue

    if vs.view_transform == "AgX":
        for lk in (look, "AgX - High Contrast", "AgX - Base Contrast", "None"):
            try:
                vs.look = lk
                break
            except Exception:
                continue

    vs.exposure = float(exposure)
    vs.gamma = float(gamma)
    return vs.view_transform


def set_principled_input(bsdf_node, candidate_names: Sequence[str], value) -> bool:
    """Set the first matching Principled BSDF socket across Blender 4.x/5.x naming."""
    for name in candidate_names:
        sock = bsdf_node.inputs.get(name)
        if sock is not None:
            sock.default_value = value
            return True
    return False


def get_principled_input(bsdf_node, candidate_names: Sequence[str]):
    """Return the first matching Principled BSDF input socket across Blender 4.x/5.x."""
    for name in candidate_names:
        sock = bsdf_node.inputs.get(name)
        if sock is not None:
            return sock
    return None


def create_compositor_tree(scene, group_name: str = "StudioCompositor"):
    """Create a fresh compositor node tree compatible with Blender 5.0+ and Blender 4.x.

    Returns (node_tree, output_node).
    """
    if hasattr(scene, "compositing_node_group"):
        ng = bpy.data.node_groups.new(group_name, "CompositorNodeTree")
        scene.compositing_node_group = ng
        ng.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
        out_node = ng.nodes.new("NodeGroupOutput")
        return ng, out_node

    scene.use_nodes = True
    ng = scene.node_tree
    ng.nodes.clear()
    out_node = ng.nodes.new("CompositorNodeComposite")
    return ng, out_node


def configure_glare_node(
    glare_node,
    glare_type: str = "Fog Glow",
    quality: str = "High",
    threshold: float = 1.2,
    strength: float = 0.35,
    size: float = 0.7,
    streaks: int = 4,
    streaks_angle_deg: float = 15.0,
    fade: float = 0.84,
) -> None:
    """Configure CompositorNodeGlare across Blender 5.2 socket API and Blender 4.x attribute API."""
    if "Type" in glare_node.inputs:
        # Blender 5.x socket-driven Glare node (Title Case enums)
        glare_node.inputs["Type"].default_value = glare_type
        if "Quality" in glare_node.inputs:
            glare_node.inputs["Quality"].default_value = quality
        if "Threshold" in glare_node.inputs:
            glare_node.inputs["Threshold"].default_value = float(threshold)
        if "Strength" in glare_node.inputs:
            glare_node.inputs["Strength"].default_value = float(strength)
        if "Size" in glare_node.inputs:
            glare_node.inputs["Size"].default_value = float(size)
        if "Streaks" in glare_node.inputs:
            glare_node.inputs["Streaks"].default_value = int(streaks)
        if "Streaks Angle" in glare_node.inputs:
            glare_node.inputs["Streaks Angle"].default_value = math.radians(streaks_angle_deg)
        if "Fade" in glare_node.inputs:
            glare_node.inputs["Fade"].default_value = float(fade)
        return

    # Legacy Blender 4.x attribute-driven Glare node
    type_map = {
        "Fog Glow": "FOG_GLOW",
        "Bloom": "BLOOM",
        "Streaks": "STREAKS",
        "Ghosts": "GHOSTS",
        "Simple Star": "SIMPLE_STAR",
    }
    glare_node.glare_type = type_map.get(glare_type, glare_type.upper().replace(" ", "_"))
    glare_node.quality = quality.upper()
    glare_node.threshold = float(threshold)
    glare_node.mix = max(-1.0, min(1.0, float(strength) - 1.0))
    if hasattr(glare_node, "size"):
        glare_node.size = max(6, min(9, int(round(6 + size * 3))))
    if hasattr(glare_node, "streaks"):
        glare_node.streaks = int(streaks)
    if hasattr(glare_node, "angle_offset"):
        glare_node.angle_offset = math.radians(streaks_angle_deg)
    if hasattr(glare_node, "fade"):
        glare_node.fade = float(fade)


def configure_color_balance_lgg(
    cb_node,
    factor: float = 0.35,
    lift: Tuple[float, float, float, float] = (1.0, 1.0, 1.0, 1.0),
    gamma: Tuple[float, float, float, float] = (1.0, 1.0, 1.0, 1.0),
    gain: Tuple[float, float, float, float] = (1.0, 1.0, 1.0, 1.0),
) -> None:
    """Configure CompositorNodeColorBalance (Lift/Gamma/Gain) on Blender 5.2+ and 4.x."""
    if len(cb_node.inputs) >= 9 and getattr(cb_node.inputs[2], "name", "") == "Type":
        cb_node.inputs[1].default_value = float(factor)
        cb_node.inputs[2].default_value = "Lift/Gamma/Gain"
        cb_node.inputs[4].default_value = tuple(lift)
        cb_node.inputs[6].default_value = tuple(gamma)
        cb_node.inputs[8].default_value = tuple(gain)
        return

    if hasattr(cb_node, "correction_method"):
        cb_node.correction_method = "LIFT_GAMMA_GAIN"
    if "Fac" in cb_node.inputs:
        cb_node.inputs["Fac"].default_value = float(factor)
    cb_node.lift = tuple(lift[:3])
    cb_node.gamma = tuple(gamma[:3])
    cb_node.gain = tuple(gain[:3])


def set_action_interpolation(action, interpolation: str = "LINEAR") -> int:
    """Set keyframe interpolation across Blender 5.x slotted actions and legacy fcurves."""
    if not action:
        return 0

    seen = set()
    updated = 0

    def _apply(fc) -> None:
        nonlocal updated
        fid = id(fc)
        if fid in seen:
            return
        seen.add(fid)
        for kp in fc.keyframe_points:
            kp.interpolation = interpolation
            updated += 1

    if hasattr(action, "layers"):
        slots = list(getattr(action, "slots", []))
        for layer in action.layers:
            for strip in layer.strips:
                for bag in getattr(strip, "channelbags", []):
                    for fc in bag.fcurves:
                        _apply(fc)
                if hasattr(strip, "channelbag"):
                    for slot in slots:
                        bag = strip.channelbag(slot)
                        if bag is not None:
                            for fc in bag.fcurves:
                                _apply(fc)

    legacy_fcurves = getattr(action, "fcurves", None)
    if legacy_fcurves is not None:
        for fc in legacy_fcurves:
            _apply(fc)

    return updated


def configure_physical_sky(
    sky_node,
    sun_elevation_deg: float = 6.0,
    sun_rotation_deg: float = 42.0,
    sun_disc: bool = False,
    air_density: float = 1.2,
    dust_density: float = 1.4,
    ozone_density: float = 2.0,
) -> str:
    """Configure ShaderNodeTexSky across Blender 4.2–5.2+ ('NISHITA' vs 'MULTIPLE_SCATTERING')."""
    chosen = ""
    for sky_type in ("MULTIPLE_SCATTERING", "NISHITA", "SINGLE_SCATTERING", "HOSEK_WILKIE"):
        try:
            sky_node.sky_type = sky_type
            chosen = sky_type
            break
        except Exception:
            continue

    if hasattr(sky_node, "sun_disc"):
        sky_node.sun_disc = bool(sun_disc)
    if hasattr(sky_node, "sun_elevation"):
        sky_node.sun_elevation = math.radians(sun_elevation_deg)
    if hasattr(sky_node, "sun_rotation"):
        sky_node.sun_rotation = math.radians(sun_rotation_deg)
    if hasattr(sky_node, "air_density"):
        sky_node.air_density = float(air_density)
    if hasattr(sky_node, "dust_density"):
        sky_node.dust_density = float(dust_density)
    if hasattr(sky_node, "ozone_density"):
        sky_node.ozone_density = float(ozone_density)
    return chosen


def set_object_ray_visibility(
    obj,
    camera: Optional[bool] = None,
    glossy: Optional[bool] = None,
    diffuse: Optional[bool] = None,
    shadow: Optional[bool] = None,
) -> None:
    """Set object ray visibility flags cleanly across Blender 4.2–5.2+."""
    mapping = (
        ("visible_camera", camera),
        ("visible_glossy", glossy),
        ("visible_diffuse", diffuse),
        ("visible_shadow", shadow),
    )
    for attr, val in mapping:
        if val is not None and hasattr(obj, attr):
            setattr(obj, attr, bool(val))
