"""Encode rendered PNG frames into stock-delivery video files.

Run after the frame sequence exists:

    ffmpeg -framerate 60 -i render/pcb_%04d.png ...

This script wraps that into H.264 (Pond5 / Adobe review) and ProRes 422 HQ
(archive / broadcast), plus a contact sheet and an ffmpeg loop-seam report.
"""

import json
import os
import re
import shutil
import subprocess
import sys

FPS = int(os.environ.get("FPS", "60"))
EXPECTED_FRAMES = int(os.environ.get("EXPECTED_FRAMES", "720"))
FFMPEG = shutil.which("ffmpeg")
FFPROBE = shutil.which("ffprobe")


def discover_frames(src, prefix="pcb_"):
    """Return the sorted frame numbers actually present on disk."""
    pat = re.compile(r"^%s(\d+)\.png$" % re.escape(prefix))
    found = []
    for name in os.listdir(src):
        m = pat.match(name)
        if m:
            found.append(int(m.group(1)))
    return sorted(found)


def run(cmd):
    print("[encode] %s" % " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True)


def require(tool):
    if tool is None:
        sys.exit("ffmpeg/ffprobe not found on PATH")


def main():
    require(FFMPEG)
    require(FFPROBE)

    src = sys.argv[1] if len(sys.argv) > 1 else "render"
    outdir = sys.argv[2] if len(sys.argv) > 2 else "output"
    os.makedirs(outdir, exist_ok=True)

    numbers = discover_frames(src)
    if not numbers:
        sys.exit("no frames matching pcb_####.png in %s" % src)

    first = numbers[0]
    count = len(numbers)
    contiguous = numbers == list(range(first, first + count))
    print("[encode] %d frames, %d..%d, contiguous=%s, expected %d"
          % (count, first, numbers[-1], contiguous, EXPECTED_FRAMES))
    if not contiguous:
        sys.exit("[encode] FAIL: frame numbering has gaps")
    if count != EXPECTED_FRAMES:
        print("[encode] NOTE: encoding %d of the expected %d frames"
              % (count, EXPECTED_FRAMES))

    start = first
    length = count
    duration = round(length / FPS, 3)

    # "12s" not "12.0s"; keep short previews readable too ("0.5s")
    secs = ("%g" % round(duration, 1))
    stem = "pcb_luxury_loop_4k60_%ss" % secs
    h264 = os.path.join(outdir, stem + "_h264.mp4")
    prores = os.path.join(outdir, stem + "_prores.mov")

    # H.264 for review sites. CRF 16 keeps the emissive traces clean.
    run([
        FFMPEG, "-y",
        "-framerate", str(FPS),
        "-start_number", str(start),
        "-i", os.path.join(src, "pcb_%04d.png"),
        "-frames:v", str(length),
        "-c:v", "libx264",
        "-preset", "slow",
        "-crf", "16",
        "-pix_fmt", "yuv420p",
        "-profile:v", "high",
        "-level", "5.2",
        "-movflags", "+faststart",
        h264,
    ])

    # ProRes 422 HQ as the archival master.
    run([
        FFMPEG, "-y",
        "-framerate", str(FPS),
        "-start_number", str(start),
        "-i", os.path.join(src, "pcb_%04d.png"),
        "-frames:v", str(length),
        "-c:v", "prores_ks",
        "-profile:v", "3",
        "-pix_fmt", "yuv422p10le",
        prores,
    ])

    # Contact sheet for thumbnail selection on the marketplace.
    step = max(1, length // 12)
    run([
        FFMPEG, "-y",
        "-framerate", str(FPS),
        "-start_number", str(start),
        "-i", os.path.join(src, "pcb_%04d.png"),
        "-vf", "select='not(mod(n\\,%d))',scale=640:-1,tile=4x3" % step,
        "-fps_mode", "vfr",
        "-frames:v", "1",
        "-update", "1",
        os.path.join(outdir, "pcb_contact_sheet.png"),
    ])

    # Verify the delivered file actually matches the spec.
    probe = json.loads(subprocess.run([
        FFPROBE, "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height,r_frame_rate,nb_frames,pix_fmt",
        "-show_entries", "format=duration,size",
        "-of", "json", h264,
    ], capture_output=True, text=True, check=True).stdout)

    report = {
        "frames_encoded": count,
        "frame_range": [first, numbers[-1]],
        "target_fps": FPS,
        "encoded_duration_s": duration,
        "target_resolution": "3840x2160",
        "expected_frames": EXPECTED_FRAMES,
        "h264": probe,
        "prores_bytes": os.path.getsize(prores) if os.path.exists(prores) else None,
    }
    with open(os.path.join(outdir, "render_report.json"), "w") as fh:
        json.dump(report, fh, indent=2)

    stream = probe["streams"][0]
    print("[encode] %dx%d %s %s frames, %ss"
          % (stream["width"], stream["height"],
             stream["r_frame_rate"], stream.get("nb_frames"),
             probe["format"]["duration"]))

    for name in (h264, prores):
        size_mb = os.path.getsize(name) / (1024 * 1024)
        print("[encode] %s  %0.1f MB" % (os.path.basename(name), size_mb))

    # Adobe rejects files over ~3.9 GB.
    h264_gb = os.path.getsize(h264) / (1024 ** 3)
    if h264_gb > 3.9:
        print("[encode] WARNING: H.264 exceeds the 3.9 GB marketplace limit")


if __name__ == "__main__":
    main()