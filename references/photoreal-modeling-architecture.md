# Photorealistic Modeling & 3-Tier Detailing Architecture

Why do most AI-generated Blender scenes look like low-poly toys while studio CG looks indistinguishable from photography? **Never because of render samples alone — almost always because of scale, edge truth, structural joints, and layered detail density.** Follow these architectural rules in every Python modeling script.

---

## 1. Spec-First Blueprint (`1 BU = 1.0 m`)

Never eyeball arbitrary numbers inline across 50 `create_cube` calls. Define a single canonical `SPEC` dictionary at the top of your build script in **real-world SI meters**:
- **Architecture**: Door `0.90 × 2.10 m`, floor-to-floor height `3.2–4.0 m`, handrail `1.05 m`, stair riser `0.17 m` / tread `0.28 m`, curtain-wall mullion `0.06–0.10 m` wide × `0.14–0.22 m` deep, concrete reveal groove `0.015–0.025 m`.
- **Interiors & Furniture**: Desk height `0.74–0.76 m`, chair seat `0.45 m`, baseboard `0.08–0.12 m`, window sill `0.85–0.95 m`, wall thickness `0.18–0.30 m`.
- **Products & Craft**: Wristwatch case `Ø 0.040 m × 0.011 m`, ceramic cup `Ø 0.082 m × 0.095 m`, wall thickness `0.003–0.005 m`.
- **Terrain & Urban Dioramas**: Lock real horizontal footprint + vertical exaggeration ratio (e.g., `1.0x` photographic or `1.25x` subtle architectural relief) so camera focal length and DOF behave physically.

---

## 2. The Macro -> Meso -> Micro 3-Tier Geometry Law

Every hero asset must explicitly construct **all three detail tiers** before any Cycles render:

| Tier | Role | Concrete Requirements in Code |
| :--- | :--- | :--- |
| **Tier 1 · Macro (Primary Massing)** | Silhouette, proportion, grounding | Accurate real-world footprint & massing ratios; every resting object meets a plinth, curb, baseboard, or contact seam (`z = 0` or exact support surface — **zero floating parts**). |
| **Tier 2 · Meso (Structural Logic)** | Believable construction & depth | Real thickness on walls/shells (`Solidify` or extruded volumes, never paper-thin single planes); recessed window/door apertures (`0.12–0.28 m` recess); curtain-wall mullions & transoms; roof parapets & copings; beveled edges (`bmesh.ops.bevel` `0.004–0.025 m`, `segments=2–3`) so every edge catches real specular highlights. |
| **Tier 3 · Micro (Tactile Credibility)** | Breaks CG sterility up close | Panel seam reveals (`5–15 mm` gaps), window gaskets/frames, fasteners/rivets/hardware, interior furnishings behind glass, curb chamfer blocks, light fixtures/bollards, subtle non-uniform surface warps/displacement, and instanced environmental dressing. |

**The Golden Edge Rule**: In the physical world, **zero razor-sharp 90° edges exist**. Even machined steel has a `0.3–1.0 mm` chamfer; architectural concrete has a `10–20 mm` chamfer; wood/ceramic has a `1–4 mm` fillet. Specular highlights riding along beveled edges are the single fastest visual cue of photorealism.

---

## 3. True Behind-Glass Depth ("真内透")

Never paint fake emissive rectangles onto flat building exteriors when a shot comes closer than medium distance:
1. Build a real structural recess behind the outer curtain-wall glass (`normal_offset = -0.10 to -0.25 m`).
2. Construct physical floor slabs, rear walls, ceiling light coves, desks/columns, or warm interior rooms inside the shell.
3. Place thin architectural glass (`thickness = 0.02–0.03 m` or single sheet with Fresnel reflection + `Transmission Weight = 0.80–0.90`) in front of the interior, framed by dark anodized mullions (`Metallic = 0.90+`).
4. For night facades with LEDs or twinkle patterns, attach custom per-face float attributes (`bulb_phase`, `bulb_seed`, `bulb_z_norm`) on interior strips behind glass so real mullions and glass reflections interact with the light.

---

## 4. Clean Modular Script Architecture & Instancing Discipline

Structure every complex scene into clean, deterministic Python builders:
- `00_CAMERAS_AND_RIG`: Cameras, `Track To` target empties, animation paths.
- `01_LIGHTING`: Sun, sky rigs, practical area lights, accent rim strips.
- `02_ENVIRONMENT`: Ground plaza/terrain, water plane, distant skyline/backdrop (`Env_*` prefix so `scene_auditor.py` and `visual_qc_kit.py` auto-focus hero bounds accurately).
- `03_HERO_ASSET`: Multi-part hero meshes, cleanly named (`Hero_*`), never merged into one giant uneditable blob until needed.

**Instancing & Memory Discipline**:
- Reuse `bpy.data.meshes` data-blocks across repeated elements (streetlights, trees, mullions, skyline blocks, fasteners) via `bpy.data.objects.new(name, shared_mesh)`.
- **Exception (Pitfall #6)**: If an instance needs a different material slot assignment, copy the mesh data (`obj.data = src.data.copy()`) or drive per-object variation via `ShaderNodeObjectInfo -> Random / Color`!
- Keep Workbench clay legibility high: split massive batched city/foliage meshes into `6–12` named buckets so Workbench `RANDOM` clay views read with crisp architectural color separation.

---

## 5. Hybrid Modeling Boundary (Know When NOT to Pure-Box-Model)

Choose the modeling strategy that wins on final photographic truth, not ideological purity:

| Subject Type | Best Programmatic Strategy |
| :--- | :--- |
| **Architecture, bridges, towers, interiors, industrial products, machinery, vehicles, watches, geometric jewelry** | Pure parametric `bmesh` + modifiers (`Bevel`, `Subsurf`, `Array`, `Boolean`) + procedural PBR shaders. |
| **Landscapes, coastal islands, mountain ranges, urban dioramas** | Real DEM/heightmap or layered procedural `Noise`/`Voronoi` displacement mesh + `bmesh`/Geometry Nodes instanced urban blocks, roads, and multi-tier tree clusters. |
| **Fluids, water ripples, glass caustics, mist, fire/embers, thin-film optics** | Pure Cycles physical optics, analytical waves / Mantaflow / animated displacement + volumetric shaders. |
| **Ornate organic carvings, fine calligraphy, silk embroidery, painterly murals, intricate portraits** | High-resolution 2K/4K orthographic textures (albedo + height/normal + alpha cutout) mounted onto real beveled 3D carrier geometry with physical relief displacement and parallax layers — never crude primitive approximations. |
