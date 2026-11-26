"""Physical, anti-plastic, ORM-bake-safe PBR material factory for Blender 4.2 LTS – 5.2+.

Provides 16 energy-conserving architectural, industrial, natural, and game-asset materials
built purely with standard Principled BSDF + procedural multi-scale roughness, AO cavity
darkening, micro-bump, and optional top-facing snow/dust masks. Every material is safe to
render in Cycles/EEVEE and directly bakeable via scripts/game_asset_pipeline.py.
"""

from typing import Dict, List, Optional, Tuple
import bpy

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from blender_compat import ensure_material_node_tree, get_principled_input, set_principled_input


MATERIAL_SPECS: Dict[str, Dict] = {
    "weathered_concrete": {
        "color_a": (0.16, 0.17, 0.185, 1.0),
        "color_b": (0.29, 0.30, 0.32, 1.0),
        "metallic": 0.0,
        "rough_min": 0.50,
        "rough_max": 0.80,
        "ior": 1.50,
        "noise_scale": 6.5,
        "ao_fac": 0.42,
        "bump_strength": 0.12,
        "bump_dist": 0.008,
    },
    "wet_asphalt": {
        "color_a": (0.032, 0.036, 0.042, 1.0),
        "color_b": (0.068, 0.074, 0.084, 1.0),
        "metallic": 0.0,
        "rough_min": 0.10,
        "rough_max": 0.44,
        "ior": 1.52,
        "noise_scale": 2.4,
        "ao_fac": 0.35,
        "bump_strength": 0.10,
        "bump_dist": 0.006,
        "coat_min": 0.12,
        "coat_max": 0.55,
        "coat_rough": 0.05,
    },
    "damp_granite": {
        "color_a": (0.052, 0.058, 0.068, 1.0),
        "color_b": (0.105, 0.112, 0.125, 1.0),
        "metallic": 0.0,
        "rough_min": 0.14,
        "rough_max": 0.42,
        "ior": 1.52,
        "noise_scale": 3.5,
        "ao_fac": 0.32,
        "bump_strength": 0.08,
        "bump_dist": 0.007,
        "coat_min": 0.08,
        "coat_max": 0.42,
        "coat_rough": 0.07,
    },
    "anodized_aluminum": {
        "color_a": (0.045, 0.052, 0.064, 1.0),
        "color_b": (0.075, 0.084, 0.098, 1.0),
        "metallic": 0.92,
        "rough_min": 0.20,
        "rough_max": 0.35,
        "ior": 1.50,
        "noise_scale": 26.0,
        "ao_fac": 0.25,
        "bump_strength": 0.03,
        "bump_dist": 0.002,
    },
    "brushed_steel": {
        "color_a": (0.56, 0.58, 0.61, 1.0),
        "color_b": (0.72, 0.74, 0.76, 1.0),
        "metallic": 1.0,
        "rough_min": 0.14,
        "rough_max": 0.30,
        "ior": 1.50,
        "noise_scale": 34.0,
        "ao_fac": 0.28,
        "bump_strength": 0.04,
        "bump_dist": 0.002,
        "anisotropic": 0.45,
    },
    "aged_brass": {
        "color_a": (0.48, 0.34, 0.11, 1.0),
        "color_b": (0.70, 0.52, 0.20, 1.0),
        "metallic": 1.0,
        "rough_min": 0.18,
        "rough_max": 0.38,
        "ior": 1.50,
        "noise_scale": 14.0,
        "ao_fac": 0.48,
        "bump_strength": 0.05,
        "bump_dist": 0.003,
    },
    "painted_industrial_metal": {
        "color_a": (0.11, 0.14, 0.12, 1.0),
        "color_b": (0.18, 0.22, 0.19, 1.0),
        "metallic": 0.18,
        "rough_min": 0.30,
        "rough_max": 0.56,
        "ior": 1.50,
        "noise_scale": 10.0,
        "ao_fac": 0.45,
        "bump_strength": 0.07,
        "bump_dist": 0.004,
        "coat_min": 0.05,
        "coat_max": 0.20,
        "coat_rough": 0.14,
    },
    "rusty_iron": {
        "color_a": (0.14, 0.065, 0.032, 1.0),
        "color_b": (0.28, 0.14, 0.06, 1.0),
        "metallic": 0.35,
        "rough_min": 0.52,
        "rough_max": 0.86,
        "ior": 1.50,
        "noise_scale": 16.0,
        "ao_fac": 0.50,
        "bump_strength": 0.18,
        "bump_dist": 0.008,
    },
    "curtain_glass": {
        "color_a": (0.68, 0.78, 0.84, 1.0),
        "color_b": (0.68, 0.78, 0.84, 1.0),
        "metallic": 0.0,
        "rough_min": 0.02,
        "rough_max": 0.04,
        "ior": 1.52,
        "transmission": 0.84,
        "coat_min": 0.35,
        "coat_max": 0.35,
        "coat_rough": 0.02,
        "noise_scale": 4.0,
        "ao_fac": 0.0,
        "bump_strength": 0.0,
        "bump_dist": 0.0,
    },
    "calm_water": {
        "color_a": (0.016, 0.038, 0.058, 1.0),
        "color_b": (0.022, 0.048, 0.072, 1.0),
        "metallic": 0.0,
        "rough_min": 0.02,
        "rough_max": 0.06,
        "ior": 1.333,
        "transmission": 0.25,
        "noise_scale": 12.0,
        "ao_fac": 0.0,
        "bump_strength": 0.06,
        "bump_dist": 0.015,
    },
    "oiled_walnut": {
        "color_a": (0.085, 0.045, 0.024, 1.0),
        "color_b": (0.19, 0.105, 0.055, 1.0),
        "metallic": 0.0,
        "rough_min": 0.28,
        "rough_max": 0.50,
        "ior": 1.50,
        "noise_scale": 11.0,
        "ao_fac": 0.38,
        "bump_strength": 0.07,
        "bump_dist": 0.004,
        "coat_min": 0.12,
        "coat_max": 0.22,
        "coat_rough": 0.14,
    },
    "matte_plaster": {
        "color_a": (0.56, 0.54, 0.50, 1.0),
        "color_b": (0.70, 0.68, 0.63, 1.0),
        "metallic": 0.0,
        "rough_min": 0.62,
        "rough_max": 0.85,
        "ior": 1.48,
        "noise_scale": 4.5,
        "ao_fac": 0.30,
        "bump_strength": 0.06,
        "bump_dist": 0.004,
    },
    "mossy_stone": {
        "color_a": (0.09, 0.11, 0.085, 1.0),
        "color_b": (0.21, 0.22, 0.20, 1.0),
        "metallic": 0.0,
        "rough_min": 0.55,
        "rough_max": 0.88,
        "ior": 1.52,
        "noise_scale": 7.5,
        "ao_fac": 0.50,
        "bump_strength": 0.18,
        "bump_dist": 0.012,
    },
    "glazed_ceramic": {
        "color_a": (0.58, 0.62, 0.58, 1.0),
        "color_b": (0.68, 0.72, 0.68, 1.0),
        "metallic": 0.0,
        "rough_min": 0.06,
        "rough_max": 0.16,
        "ior": 1.54,
        "noise_scale": 8.0,
        "ao_fac": 0.18,
        "bump_strength": 0.02,
        "bump_dist": 0.002,
        "coat_min": 0.60,
        "coat_max": 0.75,
        "coat_rough": 0.04,
        "subsurface": 0.18,
    },
    "foliage_leaf": {
        "color_a": (0.045, 0.115, 0.038, 1.0),
        "color_b": (0.11, 0.21, 0.075, 1.0),
        "metallic": 0.0,
        "rough_min": 0.36,
        "rough_max": 0.62,
        "ior": 1.45,
        "noise_scale": 9.0,
        "ao_fac": 0.30,
        "bump_strength": 0.05,
        "bump_dist": 0.004,
        "subsurface": 0.22,
    },
    "warm_emissive": {
        "color_a": (1.0, 0.74, 0.40, 1.0),
        "color_b": (1.0, 0.74, 0.40, 1.0),
        "metallic": 0.0,
        "rough_min": 0.20,
        "rough_max": 0.20,
        "ior": 1.50,
        "emission_color": (1.0, 0.72, 0.38, 1.0),
        "emission_strength": 12.0,
        "noise_scale": 1.0,
        "ao_fac": 0.0,
        "bump_strength": 0.0,
        "bump_dist": 0.0,
    },
}


def list_materials() -> List[str]:
    """Return all built-in physical PBR preset names."""
    return sorted(MATERIAL_SPECS.keys())


def make_material(
    preset: str,
    name: Optional[str] = None,
    tint: Optional[Tuple[float, float, float]] = None,
    emission_strength: Optional[float] = None,
    snow_dusting: float = 0.0,
    noise_scale_mult: float = 1.0,
) -> bpy.types.Material:
    """Create a physically grounded, anti-plastic, ORM-bake-safe Principled BSDF material.

    Args:
      preset: One of list_materials() (e.g. 'weathered_concrete', 'wet_asphalt', 'brushed_steel').
      name: Optional Blender material datablock name.
      tint: Optional linear (r, g, b) multiplier applied to base colors (for painted metal/emissives).
      emission_strength: Override emission strength (useful for LEDs/beacons).
      snow_dusting: 0.0..1.0 top-facing Normal.Z snow overlay strength for winter scenes.
      noise_scale_mult: Multiplier for procedural noise scale (adjust for small props vs huge buildings).
    """
    if preset not in MATERIAL_SPECS:
        raise ValueError(f"Unknown material preset {preset!r}. Available: {list_materials()}")

    spec = MATERIAL_SPECS[preset]
    mat = bpy.data.materials.new(name or f"Mat_{preset}")
    nt = ensure_material_node_tree(mat)
    nt.nodes.clear()

    out = nt.nodes.new("ShaderNodeOutputMaterial")
    out.location = (620, 0)
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (300, 0)
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    def _tint_rgba(rgba):
        if tint is None:
            return rgba
        return (
            min(0.84, max(0.015, rgba[0] * tint[0])),
            min(0.84, max(0.015, rgba[1] * tint[1])),
            min(0.84, max(0.015, rgba[2] * tint[2])),
            1.0,
        )

    col_a = _tint_rgba(spec["color_a"])
    col_b = _tint_rgba(spec["color_b"])

    # Emissive shortcut
    if "emission_color" in spec or (emission_strength is not None and emission_strength > 0.0):
        em_col = spec.get("emission_color", col_a)
        if tint is not None:
            em_col = (tint[0], tint[1], tint[2], 1.0)
        em_str = float(emission_strength if emission_strength is not None else spec.get("emission_strength", 10.0))
        bsdf.inputs["Base Color"].default_value = em_col
        set_principled_input(bsdf, ("Emission Color", "Emission"), em_col)
        set_principled_input(bsdf, ("Emission Strength",), em_str)
        bsdf.inputs["Roughness"].default_value = spec["rough_min"]
        return mat

    # Base scalar physical properties
    bsdf.inputs["Metallic"].default_value = float(spec["metallic"])
    bsdf.inputs["IOR"].default_value = float(spec["ior"])
    if "transmission" in spec:
        set_principled_input(bsdf, ("Transmission Weight", "Transmission"), float(spec["transmission"]))
    if "subsurface" in spec:
        set_principled_input(bsdf, ("Subsurface Weight", "Subsurface"), float(spec["subsurface"]))
    if "anisotropic" in spec:
        set_principled_input(bsdf, ("Anisotropic",), float(spec["anisotropic"]))

    # Procedural multi-scale texture basis
    tc = nt.nodes.new("ShaderNodeTexCoord")
    tc.location = (-740, 0)

    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.location = (-520, 40)
    noise.inputs["Scale"].default_value = float(spec["noise_scale"]) * float(noise_scale_mult)
    noise.inputs["Detail"].default_value = 9.0
    noise.inputs["Roughness"].default_value = 0.62
    nt.links.new(tc.outputs["Object"], noise.inputs["Vector"])

    # Albedo variation + AO cavity darkening
    mix_col = nt.nodes.new("ShaderNodeMix")
    mix_col.data_type = "RGBA"
    mix_col.location = (-240, 260)
    mix_col.inputs["A"].default_value = col_a
    mix_col.inputs["B"].default_value = col_b
    nt.links.new(noise.outputs["Fac"], mix_col.inputs["Factor"])
    color_out = mix_col.outputs["Result"]

    if spec.get("ao_fac", 0.0) > 0.0:
        ao = nt.nodes.new("ShaderNodeAmbientOcclusion")
        ao.location = (-240, 460)
        ao.inputs["Distance"].default_value = 0.45
        ao_mul = nt.nodes.new("ShaderNodeMix")
        ao_mul.data_type = "RGBA"
        ao_mul.blend_type = "MULTIPLY"
        ao_mul.location = (0, 280)
        ao_mul.inputs["Factor"].default_value = float(spec["ao_fac"])
        nt.links.new(color_out, ao_mul.inputs["A"])
        nt.links.new(ao.outputs["Color"], ao_mul.inputs["B"])
        color_out = ao_mul.outputs["Result"]

    # Roughness multi-scale breakup
    rm_rough = nt.nodes.new("ShaderNodeMapRange")
    rm_rough.location = (-160, -40)
    rm_rough.inputs["From Min"].default_value = 0.22
    rm_rough.inputs["From Max"].default_value = 0.78
    rm_rough.inputs["To Min"].default_value = float(spec["rough_min"])
    rm_rough.inputs["To Max"].default_value = float(spec["rough_max"])
    nt.links.new(noise.outputs["Fac"], rm_rough.inputs["Value"])
    rough_out = rm_rough.outputs["Result"]

    # Optional Normal.Z snow-dusting layer for winter environments
    if snow_dusting > 0.0:
        geom = nt.nodes.new("ShaderNodeNewGeometry")
        geom.location = (-520, 480)
        sep_n = nt.nodes.new("ShaderNodeSeparateXYZ")
        sep_n.location = (-320, 560)
        nt.links.new(geom.outputs["Normal"], sep_n.inputs["Vector"])

        snow_ramp = nt.nodes.new("ShaderNodeMapRange")
        snow_ramp.location = (-120, 560)
        thresh = max(0.35, 0.90 - float(snow_dusting) * 0.45)
        snow_ramp.inputs["From Min"].default_value = thresh
        snow_ramp.inputs["From Max"].default_value = min(0.98, thresh + 0.14)
        snow_ramp.inputs["To Min"].default_value = 0.0
        snow_ramp.inputs["To Max"].default_value = min(1.0, float(snow_dusting))
        nt.links.new(sep_n.outputs["Z"], snow_ramp.inputs["Value"])

        snow_mix = nt.nodes.new("ShaderNodeMix")
        snow_mix.data_type = "RGBA"
        snow_mix.location = (120, 340)
        snow_mix.inputs["B"].default_value = (0.74, 0.77, 0.80, 1.0)
        nt.links.new(snow_ramp.outputs["Result"], snow_mix.inputs["Factor"])
        nt.links.new(color_out, snow_mix.inputs["A"])
        color_out = snow_mix.outputs["Result"]

    nt.links.new(color_out, bsdf.inputs["Base Color"])
    nt.links.new(rough_out, bsdf.inputs["Roughness"])

    # Optional noise-modulated damp/varnish Coat
    if "coat_min" in spec:
        coat_sock = get_principled_input(bsdf, ("Coat Weight", "Clearcoat"))
        set_principled_input(bsdf, ("Coat Roughness", "Clearcoat Roughness"), float(spec.get("coat_rough", 0.07)))
        if coat_sock is not None:
            if spec["coat_min"] == spec["coat_max"]:
                coat_sock.default_value = float(spec["coat_min"])
            else:
                rm_coat = nt.nodes.new("ShaderNodeMapRange")
                rm_coat.location = (-160, -240)
                rm_coat.inputs["From Min"].default_value = 0.30
                rm_coat.inputs["From Max"].default_value = 0.72
                rm_coat.inputs["To Min"].default_value = float(spec["coat_min"])
                rm_coat.inputs["To Max"].default_value = float(spec["coat_max"])
                nt.links.new(noise.outputs["Fac"], rm_coat.inputs["Value"])
                nt.links.new(rm_coat.outputs["Result"], coat_sock)

    # Micro-surface Bump
    if spec.get("bump_strength", 0.0) > 0.0:
        bump = nt.nodes.new("ShaderNodeBump")
        bump.location = (40, -240)
        bump.inputs["Strength"].default_value = float(spec["bump_strength"])
        bump.inputs["Distance"].default_value = float(spec.get("bump_dist", 0.006))
        nt.links.new(noise.outputs["Fac"], bump.inputs["Height"])
        nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

    return mat
