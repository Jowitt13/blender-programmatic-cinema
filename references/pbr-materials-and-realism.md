# Physical PBR Materials & Anti-Plastic Shader Cookbook

Uniform shaders with flat `Roughness = 0.5` and pure-saturated `Base Color` are the #1 giveaway of amateur CG. Use these physical rules and reusable Blender `4.2–5.2+` Principled BSDF recipes on every hero surface.

---

## 1. Four Non-Negotiable Laws of Photorealistic PBR

1. **Energy-Conserving Albedo Bounds**:
   - Real-world diffuse surfaces almost NEVER exceed linear luminance `0.85` (even fresh snow or white plaster sits at `0.65–0.80`; white paper/paint `0.60–0.75`). Values above `0.85` bounce unphysical light, wash out shadows, and clip AgX highlights.
   - Real-world dark materials almost NEVER sit below `0.015–0.025` linear luminance (charcoal/asphalt `0.025–0.05`, dark anodized metal `0.04–0.08`, matte black plastic `0.025–0.04`). Pure `0.0` kills all form modeling.
2. **Mandatory Roughness Breakup (Kill CG Plastic)**:
   - Never leave `Roughness` as a single constant float on any prominent hero surface (except pristine optical glass/mirrors).
   - Always feed object-space multi-scale `ShaderNodeTexNoise` (high `Detail = 6–10`, `Roughness = 0.55–0.68`) through a `ShaderNodeMapRange` into `Principled BSDF -> Roughness` across a physically realistic narrow band (e.g., brushed metal `0.18–0.32`, painted plaster `0.55–0.80`, damp stone `0.14–0.42`).
3. **Micro-Surface Relief (`Bump`) & Contact Aging (`Ambient Occlusion`)**:
   - Pair roughness variation with a restrained `ShaderNodeBump` (`Strength = 0.04–0.15`, `Distance = 0.003–0.015 m`) so grazing light catches genuine tactile grain.
   - Multiply a subtle `ShaderNodeAmbientOcclusion` (`Distance = 0.25–0.80 m`, blend factor `0.30–0.50`) into `Base Color` on architecture, stone, wood, and painted metal so joints, corners, and under-ledges naturally ground in shadow.
4. **Physical Specular / Coat / IOR Discipline**:
   - Use `Metallic = 1.0` for bare metals (color controls reflection tint) and `Metallic = 0.0` for dielectrics — avoid arbitrary mid-values like `Metallic = 0.4` unless simulating thin dusted/oxidized coatings.
   - Use `Coat Weight` + low `Coat Roughness` (`0.04–0.10`) modulated by `Noise` for wet evening granite, rain-damp asphalt, lacquered wood, glazed porcelain, and automotive clearcoats.

---

## 2. Verified Physical Reference Table (Linear Values for Blender)

| Material | Linear `Base Color` (Approx.) | `Metallic` | `Roughness` Band | `IOR` | Extra Physical Layer |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **Architectural Concrete** | `(0.16–0.32)` cool/warm gray | `0.0` | `0.50–0.80` | `1.50` | AO cavity multiply (`0.40`) + subtle bump (`0.12`) |
| **Damp Evening Granite / Asphalt** | `(0.04–0.09)` slate charcoal | `0.0` | `0.14–0.42` | `1.52` | Noise-masked `Coat Weight` `0.08–0.45`, `Coat Roughness` `0.05–0.09` |
| **Dark Anodized Aluminum** | `(0.04–0.09)` cool charcoal | `0.90–0.95` | `0.20–0.36` | `1.50` | Fine directional/high-scale noise roughness |
| **Brushed Stainless / Chrome** | `(0.58–0.76)` neutral silver | `1.0` | `0.12–0.28` | `1.50` | Stretched UV/object noise (`Anisotropic = 0.4–0.7`) |
| **Aged Brass / Gold Leaf** | `(0.62, 0.45, 0.16)` | `1.0` | `0.18–0.38` | `1.50` | AO patina darkening in crevices |
| **Architectural Curtain Glass** | `(0.68, 0.78, 0.84)` slight cyan | `0.0` | `0.015–0.04` | `1.52` | `Transmission Weight = 0.80–0.90`, `Coat = 0.35` |
| **Calm Coastal Water** | `(0.015, 0.035, 0.055)` deep teal | `0.0` | `0.02–0.06` | `1.333` | Multi-frequency wave bump (`0.04–0.10`), glossy-safe sun |
| **Matte Plaster / Limewash** | `(0.55–0.74)` warm off-white | `0.0` | `0.62–0.85` | `1.48` | Low-frequency tonal blotch + fine grain bump (`0.06`) |
| **Oiled Walnut / Oak Timber** | `(0.08–0.24)` warm brown | `0.0` | `0.28–0.52` | `1.50` | Stretched wave+noise grain + subtle `Coat = 0.15` |
| **Glazed Porcelain / Jade** | `(0.55–0.76)` ivory / celadon | `0.0` | `0.06–0.18` | `1.54` | `Subsurface Weight = 0.15–0.45` + `Coat = 0.60` |
| **Woven Linen / Wool** | `(0.12–0.55)` desaturated | `0.0` | `0.78–0.95` | `1.50` | `Sheen Weight = 0.35–0.65`, fine weave bump |

---

## 3. Cross-Version Principled BSDF Socket Safety (`4.2–5.2+`)

Always use `set_principled_input()` and `ensure_material_node_tree()` from [scripts/blender_compat.py](../scripts/blender_compat.py) when setting modern sockets so scripts remain compatible across Blender 4.2, 4.5, 5.0, and 5.2+:
- `("Coat Weight", "Clearcoat")` and `("Coat Roughness", "Clearcoat Roughness")`
- `("Transmission Weight", "Transmission")`
- `("Subsurface Weight", "Subsurface")`
- `("Specular IOR Level", "Specular")`
- `("Emission Color", "Emission")` and `("Emission Strength",)`

---

## 4. Edge-Wear & Micro-Bevel Shader Pattern (Instant Hero Polish)

For machined metal, painted hardware, or carved stone close-ups, wire two lightweight shader enhancers into your `Principled BSDF`:
1. **`ShaderNodeBevel` (`Samples = 4`, `Radius = 0.004–0.012 m`)** -> plug into `Principled BSDF -> Normal` (or combine with `Bump`) to catch soft optical micro-highlights on crisp intersections without exploding polygon counts.
2. **Crevice Darkening (`ShaderNodeAmbientOcclusion`)**: Multiply `AO -> Color` into `Base Color` (`Factor = 0.35–0.50`) and raise `Roughness` slightly in occluded crevices so dust and patina settle where real physics deposits them.
