"""Cross-platform automated regression & smoke test suite for blender-programmatic-studio.

Tests docs/links/syntax, all 5 scene presets, all 16 material_library presets, environment_kit
(weather, bounded volumetric fog, terrain & scatter), Examples 01 & 02, scene_auditor.py
(standard + --game-ready), visual_qc_kit.py (clay_4view + cycles_crop), game_asset_pipeline.py
(metallic-safe PBR->ORM+Emissive bake, Lightmap UV, LODs, UCX collision, GLB + FBX export),
cleanup_imported_mesh.py (external .glb cleanup/decimate/re-export), resumable_seq_renderer.py,
and delivery_audit.py.

Usage:
  python tests/run_smoke_test.py [--blender "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe"]
"""

import argparse
import os
import py_compile
import re
import shutil
import subprocess
import sys
import tempfile


REPO_ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))


def find_blender(explicit: str = "") -> str:
    if explicit and os.path.isfile(explicit):
        return explicit
    on_path = shutil.which("blender")
    if on_path:
        return on_path
    candidates = [
        r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe",
        r"C:\Program Files\Blender Foundation\Blender 5.0\blender.exe",
        r"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe",
        r"C:\Program Files\Blender Foundation\Blender 4.2\blender.exe",
        "/Applications/Blender.app/Contents/MacOS/Blender",
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    raise FileNotFoundError("Could not locate Blender executable. Pass --blender <path>.")


def run_cmd(cmd, env=None) -> str:
    proc = subprocess.run(cmd, capture_output=True, text=True, env=env)
    if proc.returncode != 0:
        print("STDOUT:\n" + proc.stdout)
        print("STDERR:\n" + proc.stderr)
        raise RuntimeError(f"Command failed (exit {proc.returncode}): {' '.join(cmd)}")
    return proc.stdout + "\n" + proc.stderr


def check_docs_and_syntax() -> None:
    skill_md = os.path.join(REPO_ROOT, "SKILL.md")
    text = open(skill_md, encoding="utf-8").read()
    assert text.startswith("---\n"), "SKILL.md missing YAML frontmatter"
    fm = text.split("---", 2)[1]
    assert "name: blender-programmatic-studio" in fm, "SKILL.md name mismatch"
    assert "description:" in fm, "SKILL.md missing description"

    md_files = []
    for root, _, files in os.walk(REPO_ROOT):
        if ".git" in root.split(os.sep):
            continue
        for fn in files:
            if fn.endswith(".md"):
                md_files.append(os.path.join(root, fn))

    link_pat = re.compile(
        r"\[[^\]]+\]\((\.\.?/[^)#]+|assets/[^)#]+|references/[^)#]+|scripts/[^)#]+|adapters/[^)#]+|examples/[^)#]+|tests/[^)#]+|install/[^)#]+)\)"
    )
    checked = 0
    for mf in md_files:
        body = open(mf, encoding="utf-8").read()
        for rel in link_pat.findall(body):
            target = os.path.normpath(os.path.join(os.path.dirname(mf), rel))
            assert os.path.exists(target), f"Broken relative link in {mf}: {rel} -> {target}"
            checked += 1

    py_count = 0
    for folder in ("scripts", "examples", "tests"):
        d = os.path.join(REPO_ROOT, folder)
        for fn in os.listdir(d):
            if fn.endswith(".py"):
                py_compile.compile(os.path.join(d, fn), doraise=True)
                py_count += 1

    print(f"[PASS] Docs & Syntax: {len(md_files)} markdown files, {checked} links verified, {py_count} Python files compiled.")


def run_blender_suite(blender_exe: str) -> None:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    scripts_dir = os.path.join(REPO_ROOT, "scripts")

    def bcmd(script_rel: str, *extra: str):
        return [
            blender_exe,
            "-b",
            "--factory-startup",
            "--python-exit-code",
            "1",
            "--python",
            os.path.join(REPO_ROOT, script_rel),
            "--",
            *extra,
        ]

    with tempfile.TemporaryDirectory(prefix="bps_smoke_") as tmp:
        # 1. All 5 scene presets in cinema_rig_kit.py
        for preset in ("studio_product", "arch_exterior", "arch_interior", "diorama_terrain", "cinema_macro"):
            out_b = os.path.join(tmp, f"preset_{preset}.blend")
            out = run_cmd(
                bcmd("scripts/cinema_rig_kit.py", "--out", out_b, "--preset", preset, "--res-x", "256", "--res-y", "256", "--samples", "8", "--compositor"),
                env=env,
            )
            assert "[MASTER_RIG_SAVED]" in out, f"Preset {preset} failed to save"
            assert "DeprecationWarning" not in out, f"DeprecationWarning in preset {preset}:\n{out}"
        print("[PASS] All 5 cinema_rig_kit presets built with zero warnings.")

        # 2. All 16 physical PBR materials + environment_kit (weather, fog, terrain, scatter)
        expr = (
            f"import sys, bpy; sys.path.insert(0, r'{scripts_dir}'); "
            "from material_library import list_materials, make_material; "
            "from environment_kit import apply_weather_preset, generate_terrain_mesh, scatter_instances_on_surface; "
            "s = bpy.context.scene; "
            "mats = [make_material(m, snow_dusting=(0.4 if m=='weathered_concrete' else 0.0)) for m in list_materials()]; "
            "assert len(mats) == 16; "
            "apply_weather_preset(s, 'rainy_night', add_fog=True); "
            "apply_weather_preset(s, 'golden_haze', add_fog=False); "
            "t = generate_terrain_mesh(s, size_xy=(30.0, 30.0), grid_res=24, height_scale=5.0, material=mats[0]); "
            "bpy.ops.mesh.primitive_ico_sphere_add(radius=0.4); proto = bpy.context.active_object.data; "
            "insts = scatter_instances_on_surface(s, t, proto, count=20, min_z=0.1, max_slope_deg=45.0); "
            "assert len(insts) > 0; "
            "print('MAT_ENV_OK', len(mats), len(insts))"
        )
        out = run_cmd([blender_exe, "-b", "--factory-startup", "--python-exit-code", "1", "--python-expr", expr], env=env)
        assert "MAT_ENV_OK 16" in out and "DeprecationWarning" not in out, out
        print("[PASS] material_library.py (16 materials) & environment_kit.py (weather, fog, terrain, scatter) passed.")

        # 3. Build Example 01 (Architectural Bay) & Example 02 (Game Hero Prop)
        ex1_blend = os.path.join(tmp, "arch_bay.blend")
        out = run_cmd(bcmd("examples/01_photoreal_architectural_bay.py", "--out", ex1_blend, "--samples", "12"), env=env)
        assert "[EXAMPLE_SAVED]" in out

        ex2_blend = os.path.join(tmp, "game_crate.blend")
        out = run_cmd(bcmd("examples/02_game_hero_prop.py", "--out", ex2_blend, "--samples", "12"), env=env)
        assert "[EXAMPLE02_SAVED]" in out
        print("[PASS] Examples 01 & 02 built cleanly.")

        # 4. Standard pre-render scene_auditor.py
        audit_json = os.path.join(tmp, "audit.json")
        out = run_cmd(bcmd("scripts/scene_auditor.py", "--blend", ex2_blend, "--json-out", audit_json, "--fail-on-error"), env=env)
        assert "[SCENE_AUDIT] status=PASS" in out or "[SCENE_AUDIT] status=WARN" in out, out
        assert os.path.isfile(audit_json)
        print("[PASS] scene_auditor.py (photoreal mode) passed with zero FAIL issues.")

        # 5. visual_qc_kit.py (clay_4view + cycles_crop)
        clay_png = os.path.join(tmp, "qc_clay.png")
        cyc_png = os.path.join(tmp, "qc_cycles.png")
        out1 = run_cmd(bcmd("scripts/visual_qc_kit.py", "--blend", ex2_blend, "--mode", "clay_4view", "--out", clay_png, "--cell-res", "256"), env=env)
        assert "[CLAY_QC_SAVED]" in out1 and os.path.getsize(clay_png) > 5000
        out2 = run_cmd(bcmd("scripts/visual_qc_kit.py", "--blend", ex2_blend, "--mode", "cycles_crop", "--out", cyc_png, "--res", "320", "--samples", "12"), env=env)
        assert "[CYCLES_QC_SAVED]" in out2 and os.path.getsize(cyc_png) > 5000
        print("[PASS] visual_qc_kit.py generated clay_4view & cycles_crop with zero external dependencies.")

        # 6. Game-Asset Pipeline on Example 02 (PBR->ORM+Emissive Bake, LODs, UCX, GLB + FBX)
        game_blend = os.path.join(tmp, "game_crate_ready.blend")
        tex_dir = os.path.join(tmp, "textures")
        out_glb = os.path.join(tmp, "SupplyCrate.glb")
        out_fbx = os.path.join(tmp, "SupplyCrate.fbx")
        og = run_cmd(
            bcmd(
                "scripts/game_asset_pipeline.py",
                "--blend", ex2_blend,
                "--out-blend", game_blend,
                "--asset-name", "SupplyCrate",
                "--merge-hero",
                "--lightmap-uv",
                "--weighted-normals",
                "--bake",
                "--bake-emissive",
                "--tex-dir", tex_dir,
                "--tex-size", "256",
                "--bake-samples", "4",
                "--normal-format", "opengl",
                "--lods", "0.5,0.2",
                "--collision",
                "--export-glb", out_glb,
                "--export-fbx", out_fbx,
            ),
            env=env,
        )
        assert "[GAME_BAKE_COMPLETE]" in og and "[LOD_CREATED]" in og and "[COLLISION_CREATED]" in og
        for suffix in ("BaseColor", "ORM", "Normal", "Emissive"):
            assert os.path.getsize(os.path.join(tex_dir, f"SupplyCrate_{suffix}.png")) > 512
        assert os.path.getsize(out_glb) > 10000 and os.path.getsize(out_fbx) > 5000
        print("[PASS] game_asset_pipeline.py baked BaseColor/ORM/Normal/Emissive, built LODs + UCX, exported GLB & FBX.")

        # 7. Game-ready audit on exported .blend
        ga = run_cmd(bcmd("scripts/scene_auditor.py", "--blend", game_blend, "--game-ready", "--fail-on-error"), env=env)
        assert "UNBAKED_PROCEDURAL_SHADER" not in ga and "MISSING_UV_MAP" not in ga and "UNAPPLIED_SCALE" not in ga, ga
        print("[PASS] scene_auditor.py (--game-ready mode) passed with zero FAIL and zero unbaked shaders.")

        # 8. cleanup_imported_mesh.py round-trip on exported GLB
        clean_blend = os.path.join(tmp, "cleaned.blend")
        clean_glb = os.path.join(tmp, "CleanedProp.glb")
        oc = run_cmd(
            bcmd(
                "scripts/cleanup_imported_mesh.py",
                "--input", out_glb,
                "--asset-name", "CleanedProp",
                "--target-height", "1.0",
                "--target-tris", "2000",
                "--reunwrap",
                "--lightmap-uv",
                "--lods", "0.5",
                "--collision",
                "--out-blend", clean_blend,
                "--export-glb", clean_glb,
            ),
            env=env,
        )
        assert "[MESH_CLEANED]" in oc and os.path.getsize(clean_glb) > 5000
        gac = run_cmd(bcmd("scripts/scene_auditor.py", "--blend", clean_blend, "--game-ready", "--fail-on-error"), env=env)
        assert "MISSING_UV_MAP" not in gac and "UNAPPLIED_SCALE" not in gac, gac
        print("[PASS] cleanup_imported_mesh.py imported, normalized, decimated, re-exported & passed --game-ready audit.")

        # 9. resumable_seq_renderer.py (fresh -> skip -> overwrite)
        fdir = os.path.join(tmp, "frames")
        o1 = run_cmd(bcmd("scripts/resumable_seq_renderer.py", "--blend", ex1_blend, "--start", "1", "--end", "1", "--out-dir", fdir, "--samples", "8", "--res-x", "256", "--res-y", "256", "--no-prestep", "--min-bytes", "1024"), env=env)
        assert "rendered=1, skipped=0" in o1
        o2 = run_cmd(bcmd("scripts/resumable_seq_renderer.py", "--blend", ex1_blend, "--start", "1", "--end", "1", "--out-dir", fdir, "--samples", "8", "--res-x", "256", "--res-y", "256", "--no-prestep", "--min-bytes", "1024"), env=env)
        assert "rendered=0, skipped=1" in o2
        o3 = run_cmd(bcmd("scripts/resumable_seq_renderer.py", "--blend", ex1_blend, "--start", "1", "--end", "1", "--out-dir", fdir, "--samples", "8", "--res-x", "256", "--res-y", "256", "--overwrite", "--no-prestep", "--min-bytes", "1024"), env=env)
        assert "rendered=1, skipped=0, overwrite=True" in o3
        print("[PASS] resumable_seq_renderer.py passed 3-state (render -> skip -> overwrite) check.")

        # 10. delivery_audit.py on rendered still
        deliv_script = os.path.join(REPO_ROOT, "scripts", "delivery_audit.py")
        out = run_cmd([sys.executable, deliv_script, "--input", os.path.join(fdir, "frame_0001.png")], env=env)
        assert '"type": "still"' in out
        print("[PASS] delivery_audit.py verified rendered still.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run full blender-programmatic-studio smoke test suite.")
    parser.add_argument("--blender", default="", help="Optional path to Blender executable.")
    parser.add_argument("--skip-blender", action="store_true", help="Only run docs, links, and syntax checks.")
    args = parser.parse_args()

    check_docs_and_syntax()
    if not args.skip_blender:
        blender_exe = find_blender(args.blender)
        print(f"[INFO] Using Blender: {blender_exe}")
        run_blender_suite(blender_exe)
    print("\nALL SMOKE TESTS PASSED!")


if __name__ == "__main__":
    main()
