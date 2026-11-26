# Real-Time Game-Asset & Environment Pipeline (UE5 / Unity / Godot / WebGL)

Real-time game engines cannot execute Cycles procedural shaders or render million-poly raw subdivision meshes at 60+ fps. Use this playbook and [scripts/game_asset_pipeline.py](../scripts/game_asset_pipeline.py) whenever turning a programmatic Blender scene or hero prop into a **production-ready game asset or real-time game environment**.

---

## 1. Modular Real-World Scale, Pivot & Grid Discipline

- **Scale (`1 BU = 1.0 m`)**: Lock architectural walls, doorways, street props, and modular tiles to power-of-two/metric snapping grids (`0.25 m`, `0.50 m`, `1.0 m`, `2.0 m`, `4.0 m` bay widths; `3.0–4.0 m` floor heights).
- **Mandatory Unit Scale (`scale = (1, 1, 1)`)**: Always bake scale into mesh geometry before export (`apply_unit_scale()` in `game_asset_pipeline.py`). Non-unit scales break UE5/Unity physics colliders, normal map tangent basis, and runtime instancing.
- **Grounded Pivots**: Place every static prop and modular building's local origin at **bottom-center (`z = 0`)** (or bottom-left corner for modular wall kits) using `--pivot-bottom` so assets snap cleanly onto terrain and floors.

---

## 2. Topology, Weighted Normals & Polycount / LOD Budgets

| Asset Class | Hero `LOD0` Triangle Budget | `LOD1` (~50%) | `LOD2` (~20%) | Shading Technique |
| :--- | :---: | :---: | :---: | :--- |
| **Small Prop (crate, lamp, bollard)** | `500 – 4,000` tris | `250 – 2k` | `100 – 800` | Single-segment chamfer + `WeightedNormal` (`keep_sharp=True`) |
| **Hero Prop / Weapon / Vehicle** | `15,000 – 60,000` tris | `7.5k – 30k` | `3k – 12k` | Support chamfers + Baked Tangent Normal Map |
| **Modular Architectural Bay / Building** | `5,000 – 40,000` tris | `2.5k – 20k` | `1k – 8k` | Trim sheets / Baked Atlas + recessed interior shell |
| **Hero Environment Landmark / Tower** | `40,000 – 150,000` tris | `20k – 75k` | `8k – 30k` | Instanced mullions/props + LOD hierarchy + `UCX_` collision |

- **Weighted Normals Over Heavy Subsurf**: For hard-surface game architecture and props, use a `1`-segment bevel + `WeightedNormal` modifier (`--weighted-normals`) instead of Subsurf — it delivers crisp, artifact-free specular edge highlights at a fraction of the triangle count.
- **UE5 Collision Hulls**: Generate lightweight convex hulls named **`UCX_<AssetName>`** (`--collision`) so Unreal Engine automatically binds physical collision on import without needing manual collider authoring.

---

## 3. UV0, Lightmap UV1 & Texel Density

- **UV0 (`UVMap`)**: Non-overlapping island packing (`island_margin = 0.008–0.012`) so mipmaps never bleed across seam boundaries at grazing angles.
- **UV1 (`UVMap_Lightmap`)**: Enable `--lightmap-uv` (`island_margin = 0.02`) when targeting baked global illumination in Unreal Engine or Unity Lightmapper.
- **Texel Density Guidelines**:
  - First-person hero props: `1024 px/m` (`2K` or `4K` maps)
  - Third-person architecture & street furniture: `512 px/m` (`1K` or `2K` maps)
  - Distant skyline / backdrop structures: `128–256 px/m`

---

## 4. Procedural PBR -> Baked Texture & ORM Channel Packing

Blender's procedural `Noise`, `Ambient Occlusion`, `Bevel`, and `ColorRamp` shader nodes **do not export to UE5, Unity, Godot, or WebGL**. Always bake them into standard PBR image sets via `--bake`:

1. **Avoid the Cycles Black-Metal Bake Trap**: Baking `DIFFUSE` in Cycles produces pitch-black `(0,0,0)` pixels on metallic surfaces (`Metallic = 1.0`). [scripts/game_asset_pipeline.py](../scripts/game_asset_pipeline.py) avoids this by temporarily routing `Base Color`, `Roughness`, and `Metallic` through `ShaderNodeEmission` (`type='EMIT'`) for exact, lighting-independent, metallic-safe maps.
2. **ORM Channel Packing (`<Asset>_ORM.png`, `Non-Color`)**:
   - **Red (`R`)** = Ambient Occlusion (`Cycles AO bake`)
   - **Green (`G`)** = Roughness
   - **Blue (`B`)** = Metallic
   - Packing all 3 grayscale maps into one RGBA texture cuts real-time VRAM usage and texture sampler lookups by **3x**, and matches glTF 2.0 (`glTF Material Output -> Occlusion`), Unreal Engine 5, and Unity HDRP/URP directly.
3. **Normal Map Handedness (`--normal-format`)**:
   - **`opengl`** (`+Y` Green — default): Required for **glTF 2.0 (`.glb`), Unity, Godot 4, Three.js / WebGL, Blender**.
   - **`directx`** (`-Y` Green): Required for **Unreal Engine 5 (FBX)** (or import OpenGL into UE5 with *Flip Green Channel* checked).

---

## 5. Target Engine Export Matrix

| Target Engine | Recommended Format | `game_asset_pipeline.py` Flags | Notes |
| :--- | :--- | :--- | :--- |
| **Unreal Engine 5** | `.glb` / `.fbx` / `.usdc` | `--merge-hero --bake --lightmap-uv --normal-format directx --lods 0.5,0.2 --collision --export-fbx out.fbx --export-glb out.glb` | `UCX_<Name>` auto-imports as collision; FBX/glTF handles `1m -> 100cm` scale cleanly |
| **Unity (URP / HDRP)** | `.glb` (glTFast) / `.fbx` | `--merge-hero --bake --lightmap-uv --normal-format opengl --lods 0.5,0.2 --export-glb out.glb --export-fbx out.fbx` | OpenGL `+Y` normals; ORM maps map directly in glTFast or via channel swizzle |
| **Godot 4** | `.glb` (Native glTF 2.0) | `--merge-hero --bake --normal-format opengl --lods 0.5,0.2 --export-glb out.glb` | Drop `.glb` straight into `res://` — ORM + Normal + BaseColor load with zero rewiring |
| **Three.js / WebGL** | `.glb` | `--merge-hero --bake --tex-size 1024 --normal-format opengl --export-glb out.glb` | Native `glTF Material Output` Occlusion embeds exact ORM occlusion + metallicRoughness |

---

## 6. Hybrid External Asset Ingestion (Real Scans & Photo-to-3D)

For intricate organic props (statues, shoes, food, bespoke furniture) where pure procedural `bmesh` modeling is inefficient:
1. Capture or generate a base `.glb` mesh externally (e.g., photogrammetry or real-object photo-to-3D tools such as [ahujasid/camera-to-blender](https://github.com/ahujasid/camera-to-blender)).
2. Import into Blender, then run our deterministic cleanup pipeline:
   - `game_asset_pipeline.py --pivot-bottom --reunwrap --lods 0.5,0.2 --collision --export-glb`
   - `scene_auditor.py --game-ready --fail-on-error`
   - `visual_qc_kit.py --mode clay_4view` + `--mode cycles_crop` to verify silhouette, baked normals, and lighting parity before shipping into your game engine.
3. For specialized character rigging (Rigify, ARKit 52 facial blendshapes, clothing sims, hair cards), pair cleanly with dedicated character skills such as [EL4CTEO/blender-skills](https://github.com/EL4CTEO/blender-skills).
