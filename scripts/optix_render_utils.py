"""Cross-platform Cycles GPU activator and sharpness/denoising configuration (Blender 4.2–5.2+)."""

from typing import Optional, Sequence, Tuple
import bpy


DEFAULT_BACKENDS: Tuple[str, ...] = ("OPTIX", "CUDA", "HIP", "ONEAPI", "METAL")


def activate_optix_gpu(
    scene,
    tile_size: int = 1024,
    samples: Optional[int] = None,
    res_percent: Optional[int] = None,
    adaptive_threshold: float = 0.015,
    adaptive_min_samples: int = 16,
    use_oidn_cpu: bool = False,
    denoiser: str = "OPENIMAGEDENOISE",
    denoising_prefilter: str = "ACCURATE",
    pixel_filter_type: str = "BLACKMAN_HARRIS",
    filter_width: float = 1.25,
    preferred_backends: Sequence[str] = DEFAULT_BACKENDS,
) -> bool:
    """Activate Cycles GPU rendering inside headless/--factory-startup Blender sessions.

    Probes GPU compute backends in priority order (OPTIX -> CUDA -> HIP -> ONEAPI -> METAL)
    with clean CPU fallback, enables auto-tiling and adaptive sampling, configures crisp
    Blackman-Harris pixel reconstruction, and selects GPU-accelerated OIDN or OptiX denoising.

    Returns True if a GPU compute device was activated, False if running on CPU.
    """
    scene.render.engine = "CYCLES"
    prefs = bpy.context.preferences.addons["cycles"].preferences

    gpu_found = False
    chosen_backend = "CPU"

    for backend in preferred_backends:
        try:
            prefs.compute_device_type = backend
            prefs.get_devices()
        except Exception:
            continue

        matched = [dev for dev in prefs.devices if dev.type == backend]
        if matched:
            for dev in prefs.devices:
                dev.use = dev.type == backend
            gpu_found = True
            chosen_backend = backend
            break

    if not gpu_found:
        try:
            prefs.compute_device_type = "NONE"
            prefs.get_devices()
        except Exception:
            pass

    scene.cycles.device = "GPU" if gpu_found else "CPU"
    scene.cycles.use_auto_tile = True
    scene.cycles.tile_size = int(tile_size)
    scene.cycles.use_adaptive_sampling = True
    scene.cycles.adaptive_threshold = float(adaptive_threshold)

    if samples is not None:
        scene.cycles.samples = int(samples)
    if res_percent is not None:
        scene.render.resolution_percentage = int(res_percent)

    if adaptive_min_samples and adaptive_min_samples > 0:
        min_spp = min(int(adaptive_min_samples), int(scene.cycles.samples))
        if hasattr(scene.cycles, "adaptive_min_samples"):
            scene.cycles.adaptive_min_samples = max(1, min_spp)

    # Sharp pixel reconstruction (avoids default 1.5px smearing on mullions/fine relief)
    try:
        scene.cycles.pixel_filter_type = pixel_filter_type
        scene.cycles.filter_width = float(filter_width)
    except Exception:
        pass

    # Denoiser configuration
    scene.cycles.use_denoising = True
    req_denoiser = "OPENIMAGEDENOISE" if use_oidn_cpu else denoiser.upper()
    if req_denoiser == "AUTO":
        req_denoiser = "OPENIMAGEDENOISE"

    active_denoiser = req_denoiser
    try:
        scene.cycles.denoiser = req_denoiser
        if hasattr(scene.cycles, "denoising_use_gpu"):
            scene.cycles.denoising_use_gpu = (not use_oidn_cpu) and gpu_found
        if req_denoiser == "OPENIMAGEDENOISE" and hasattr(scene.cycles, "denoising_prefilter"):
            scene.cycles.denoising_prefilter = denoising_prefilter.upper()
    except Exception:
        if chosen_backend == "OPTIX":
            try:
                scene.cycles.denoiser = "OPTIX"
                active_denoiser = "OPTIX"
            except Exception:
                active_denoiser = "UNKNOWN"
        else:
            active_denoiser = "UNKNOWN"

    active_devs = [f"{d.name} ({d.type})" for d in prefs.devices if d.use]
    denoise_gpu = getattr(scene.cycles, "denoising_use_gpu", False)
    prefilter = getattr(scene.cycles, "denoising_prefilter", "N/A")
    print(
        f"[GPU_ACTIVE] engine={scene.render.engine} backend={chosen_backend} "
        f"device={scene.cycles.device} devs={active_devs} "
        f"denoiser={active_denoiser}(gpu={denoise_gpu},prefilter={prefilter}) "
        f"filter={pixel_filter_type}({filter_width:.2f}) "
        f"res={scene.render.resolution_x}x{scene.render.resolution_y}@{scene.render.resolution_percentage}% "
        f"spp={scene.cycles.samples} tile={scene.cycles.tile_size}",
        flush=True,
    )
    return gpu_found
