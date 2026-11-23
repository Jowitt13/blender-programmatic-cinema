"""Battle-tested Cycles OptiX/CUDA GPU activator for Blender 5.2+ batch rendering."""

import bpy


def activate_optix_gpu(
    scene,
    tile_size=1024,
    samples=None,
    res_percent=None,
    adaptive_threshold=0.015,
    use_oidn_cpu=False,
):
    """MUST be called inside every --factory-startup Blender session so Cycles uses GPU instead of CPU."""
    scene.render.engine = "CYCLES"
    prefs = bpy.context.preferences.addons["cycles"].preferences
    prefs.compute_device_type = "OPTIX"
    prefs.get_devices()

    gpu_found = False
    for dev in prefs.devices:
        if dev.type == "OPTIX":
            dev.use = True
            gpu_found = True
        else:
            dev.use = False

    if not gpu_found:
        prefs.compute_device_type = "CUDA"
        prefs.get_devices()
        for dev in prefs.devices:
            dev.use = dev.type == "CUDA"
            if dev.use:
                gpu_found = True

    scene.cycles.device = "GPU" if gpu_found else "CPU"
    scene.cycles.use_auto_tile = True
    scene.cycles.tile_size = tile_size
    scene.cycles.use_adaptive_sampling = True
    scene.cycles.adaptive_threshold = adaptive_threshold
    scene.cycles.use_denoising = True
    try:
        scene.cycles.denoiser = "OPENIMAGEDENOISE" if use_oidn_cpu else "OPTIX"
        scene.cycles.denoising_use_gpu = not use_oidn_cpu
    except Exception:
        pass

    if samples is not None:
        scene.cycles.samples = samples
    if res_percent is not None:
        scene.render.resolution_percentage = res_percent

    active = [f"{d.name} ({d.type})" for d in prefs.devices if d.use]
    print(
        f"[GPU_ACTIVE] engine={scene.render.engine} device={scene.cycles.device} devs={active} "
        f"res={scene.render.resolution_x}x{scene.render.resolution_y}@{scene.render.resolution_percentage}% "
        f"spp={scene.cycles.samples} tile={scene.cycles.tile_size}",
        flush=True,
    )
    return gpu_found
