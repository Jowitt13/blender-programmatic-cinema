"""Final delivery auditor for rendered stills (PNG/JPG) and encoded videos (MP4/MOV).

Runs outside Blender using standard Python (+ optional Pillow/NumPy + FFmpeg/ffprobe for video):
  - Still mode: verifies dimensions, file integrity, luminance percentiles, and clipping %.
  - Video mode: runs ffprobe metadata check, optional adjacent-frame MAD continuity scan (detecting
    stale-frame pops or resume seams), and optional contact-sheet extraction using FFmpeg 8+ `-fps_mode vfr`.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from typing import Any, Dict, List


def audit_still(image_path: str) -> Dict[str, Any]:
    path = os.path.abspath(image_path)
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Still image not found: {path}")

    size_bytes = os.path.getsize(path)
    report: Dict[str, Any] = {"type": "still", "path": path, "size_bytes": size_bytes}

    try:
        from PIL import Image
        import numpy as np

        with Image.open(path) as im:
            rgb = im.convert("RGB")
            w, h = rgb.size
            arr = np.asarray(rgb, dtype=np.float32) / 255.0
            luma = 0.2126 * arr[:, :, 0] + 0.7152 * arr[:, :, 1] + 0.0722 * arr[:, :, 2]
            report.update(
                {
                    "width": w,
                    "height": h,
                    "luma_mean": round(float(luma.mean()), 4),
                    "p01": round(float(np.percentile(luma, 1)), 4),
                    "p50": round(float(np.percentile(luma, 50)), 4),
                    "p99": round(float(np.percentile(luma, 99)), 4),
                    "clipped_white_pct": round(float(np.mean(luma >= 0.99) * 100.0), 2),
                    "crushed_black_pct": round(float(np.mean(luma <= 0.01) * 100.0), 2),
                }
            )
    except ImportError:
        report["note"] = "Pillow/NumPy not installed; pixel stats skipped."

    return report


def _run_ffprobe(video_path: str) -> Dict[str, Any]:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        raise RuntimeError("ffprobe not found on PATH.")
    cmd = [
        ffprobe,
        "-v",
        "error",
        "-show_format",
        "-show_streams",
        "-of",
        "json",
        video_path,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return json.loads(proc.stdout)


def _scan_video_mad(video_path: str, spike_threshold: float = 18.0, scan_width: int = 160) -> Dict[str, Any]:
    """Decode scaled grayscale frames via FFmpeg pipe and measure adjacent-frame MAD spikes."""
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return {"skipped": "ffmpeg not found on PATH"}
    try:
        import numpy as np
    except ImportError:
        return {"skipped": "numpy not installed"}

    info = _run_ffprobe(video_path)
    vstream = next((s for s in info.get("streams", []) if s.get("codec_type") == "video"), None)
    if not vstream:
        return {"error": "No video stream found"}
    w = int(vstream["width"])
    h = int(vstream["height"])
    sh = max(2, int(round(h * (scan_width / float(w)))) & ~1)
    frame_bytes = scan_width * sh

    cmd = [
        ffmpeg,
        "-v",
        "error",
        "-i",
        video_path,
        "-vf",
        f"scale={scan_width}:{sh},format=gray",
        "-f",
        "rawvideo",
        "-",
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    prev = None
    mads: List[float] = []
    spikes: List[Dict[str, Any]] = []
    idx = 0
    assert proc.stdout is not None
    while True:
        buf = proc.stdout.read(frame_bytes)
        if len(buf) < frame_bytes:
            break
        cur = np.frombuffer(buf, dtype=np.uint8).astype(np.float32)
        if prev is not None:
            mad = float(np.mean(np.abs(cur - prev)))
            mads.append(mad)
            if mad >= spike_threshold:
                spikes.append({"frame_transition": f"{idx}->{idx+1}", "mad": round(mad, 2)})
        prev = cur
        idx += 1
    proc.wait()

    return {
        "frames_scanned": idx,
        "mad_mean": round(sum(mads) / max(1, len(mads)), 3),
        "mad_max": round(max(mads) if mads else 0.0, 3),
        "spike_threshold": spike_threshold,
        "spikes": spikes[:20],
        "total_spikes": len(spikes),
    }


def _extract_storyboard(video_path: str, out_path: str, cols: int = 4, rows: int = 2, tile_w: int = 360) -> str:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg not found on PATH.")
    info = _run_ffprobe(video_path)
    vstream = next((s for s in info.get("streams", []) if s.get("codec_type") == "video"), None)
    nb_frames = int(vstream.get("nb_frames") or 0)
    total_tiles = cols * rows
    step = max(1, nb_frames // total_tiles) if nb_frames > total_tiles else 1

    out_abs = os.path.abspath(out_path)
    os.makedirs(os.path.dirname(out_abs), exist_ok=True)
    vf = f"select='not(mod(n\\,{step}))',scale={tile_w}:-1,tile={cols}x{rows}:padding=6:margin=6:color=0x0a0a0c"
    cmd = [
        ffmpeg,
        "-y",
        "-v",
        "error",
        "-i",
        video_path,
        "-fps_mode",
        "vfr",
        "-vf",
        vf,
        "-frames:v",
        "1",
        out_abs,
    ]
    subprocess.run(cmd, check=True)
    return out_abs


def audit_video(
    video_path: str,
    run_mad: bool = True,
    mad_threshold: float = 18.0,
    storyboard_out: str = "",
) -> Dict[str, Any]:
    path = os.path.abspath(video_path)
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Video not found: {path}")

    info = _run_ffprobe(path)
    vstream = next((s for s in info.get("streams", []) if s.get("codec_type") == "video"), {})
    astream = next((s for s in info.get("streams", []) if s.get("codec_type") == "audio"), None)
    fmt = info.get("format", {})

    report: Dict[str, Any] = {
        "type": "video",
        "path": path,
        "size_mb": round(os.path.getsize(path) / (1024 * 1024), 2),
        "video": {
            "codec": vstream.get("codec_name"),
            "profile": vstream.get("profile"),
            "level": vstream.get("level"),
            "pix_fmt": vstream.get("pix_fmt"),
            "width": vstream.get("width"),
            "height": vstream.get("height"),
            "r_frame_rate": vstream.get("r_frame_rate"),
            "nb_frames": vstream.get("nb_frames"),
            "duration_s": round(float(fmt.get("duration", 0.0)), 3),
            "bit_rate_mbps": round(int(fmt.get("bit_rate", 0)) / 1_000_000, 2),
        },
        "has_audio": astream is not None,
    }
    if run_mad:
        report["mad_continuity"] = _scan_video_mad(path, spike_threshold=mad_threshold)
    if storyboard_out:
        report["storyboard"] = _extract_storyboard(path, storyboard_out)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(prog="delivery_audit.py", description="Audit rendered stills or final MP4 deliverables.")
    parser.add_argument("--input", required=True, help="Path to rendered PNG/JPG still or MP4/MOV video.")
    parser.add_argument("--mad", action="store_true", help="Run adjacent-frame MAD continuity scan on video.")
    parser.add_argument("--mad-threshold", type=float, default=18.0, help="MAD spike reporting threshold (default: 18.0).")
    parser.add_argument("--storyboard", default="", help="Optional output PNG/JPG path to extract video contact sheet.")
    parser.add_argument("--json-out", default="", help="Optional path to save audit JSON.")
    args = parser.parse_args()

    ext = os.path.splitext(args.input)[1].lower()
    if ext in (".png", ".jpg", ".jpeg", ".tif", ".tiff", ".exr"):
        report = audit_still(args.input)
    else:
        report = audit_video(args.input, run_mad=args.mad, mad_threshold=args.mad_threshold, storyboard_out=args.storyboard)

    print(json.dumps(report, indent=2), flush=True)
    if args.json_out:
        out_abs = os.path.abspath(args.json_out)
        os.makedirs(os.path.dirname(out_abs), exist_ok=True)
        with open(out_abs, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=2)


if __name__ == "__main__":
    main()
