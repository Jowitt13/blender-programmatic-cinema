# Changelog

All notable changes to **Blender Programmatic Studio** are documented here.

## [2.1.0] - 2026-11-27

### Added
- **`scripts/material_library.py`**: One-line physical PBR material factory with 16 anti-plastic, ORM-bake-safe materials (`weathered_concrete`, `wet_asphalt`, `damp_granite`, `anodized_aluminum`, `brushed_steel`, `aged_brass`, `painted_industrial_metal`, `rusty_iron`, `curtain_glass`, `calm_water`, `oiled_walnut`, `matte_plaster`, `mossy_stone`, `glazed_ceramic`, `foliage_leaf`, `warm_emissive`), optional linear tinting, and top-facing `Normal.Z` snow dusting.
- **`scripts/environment_kit.py`**: Game-scene atmosphere & terrain toolkit featuring 5 weather presets (`blue_hour`, `rainy_night`, `golden_haze`, `snow_dusting`, `overcast_nordic`), bounded volumetric fog (`add_bounded_volumetric_fog`), procedural multi-octave terrain/island heightfield builder, and slope/altitude-filtered instanced asset scatterer.
- **`scripts/cleanup_imported_mesh.py`**: End-to-end cleanup and game-engine prep pipeline for imported AI-generated or scanned meshes (`.glb`/`.gltf`/`.fbx`/`.obj` from Tripo3D, `camera-to-blender`, Meshy, Hunyuan3D, photogrammetry) — vertex welding, outward normal repair, real-world height normalization, bottom-center pivot grounding, triangle-budget decimation, UV0/Lightmap UV1 unwrapping, LODs, UE5 `UCX_` collision, and `.glb`/`.fbx` export.
- **`examples/02_game_hero_prop.py`**: Runnable hard-surface game hero prop (armored industrial supply crate) using `material_library.py`, accompanied by rendered clay-to-Cycles visual showcase `assets/example_02_game_prop_qc.jpg`.
- **`.github/workflows/ci.yml`**: Automated GitHub Actions CI verifying frontmatter, Markdown relative links, Python compilation, and cross-platform installer execution on every push and PR.
- **`.claude-plugin/plugin.json` & `marketplace.json`**: Native Claude Code `/plugin` marketplace installation manifests.

## [2.0.0] - 2026-11-26

### Added
- Rebranded and expanded into **`blender-programmatic-studio`** — dual-track Photoreal Cinema & Real-Time Game-Asset Pipeline supporting Blender `4.2 LTS – 5.2+`.
- `scripts/blender_compat.py`: Cross-version shim fixing Blender 5.2 `ShaderNodeTexSky` (`MULTIPLE_SCATTERING` vs `NISHITA`), `scene.compositing_node_group` + `NodeGroupOutput`, Title-Case `Glare` sockets, socket-driven `ColorBalance`, slotted actions, and `BLENDER_EEVEE_NEXT` / `BLENDER_EEVEE`.
- `scripts/game_asset_pipeline.py`: Metallic-safe Cycles PBR -> ORM baking (`R=AO, G=Roughness, B=Metallic`), `opengl`/`directx` normal maps, UV0/UV1, `WeightedNormal`, automatic LOD1/LOD2, UE5 `UCX_` collision hulls, and `.glb`/`.fbx`/`.usdc` export.
- `scripts/scene_auditor.py` (standard + `--game-ready` mode), `scripts/visual_qc_kit.py` (zero-dependency 4-view clay + `1:1` Cycles crop), `scripts/delivery_audit.py`.
- 5 reusable `--preset` scene templates in `scripts/cinema_rig_kit.py`.
- Photoreal modeling, PBR cookbook, and game-asset reference guides, plus Chiba Port Tower Clay -> Cycles visual showcase, `examples/01_photoreal_architectural_bay.py`, `adapters/UNIVERSAL_PROMPT.md`, `install/install.sh` / `install.ps1`, and `tests/run_smoke_test.py`.

## [1.0.0] - 2026-11-25

### Added
- Initial release (`blender-programmatic-cinema`) covering script-driven Blender 5.2 Cycles OptiX short-film rendering, Horizon-Arch macro rig, and resumable GPU sequence rendering.
