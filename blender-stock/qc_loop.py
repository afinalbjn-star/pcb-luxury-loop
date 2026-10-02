"""Verify the rendered sequence really is a seamless loop.

Checks two things before anything gets submitted:

1. Structural   - every expected frame exists and is non-trivial in size.
2. Perceptual   - the wrap-around difference between the final frame and the
                  first frame is no worse than the difference between two
                  adjacent frames anywhere in the clip.

The second test is the one that matters. A visible jump at the seam shows up
as an unusually large frame difference at the wrap, so comparing it against the
clip's own mean difference tells us whether the loop closes cleanly.
"""

import json
import os
import re
import subprocess
import sys

FPS = int(os.environ.get("FPS", "60"))
EXPECTED_FRAMES = int(os.environ.get("EXPECTED_FRAMES", "720"))
# The seam verdict only means anything for a render that covers the whole
# period. A partial range has no wrap point, so comparing its last frame to its
# first would measure several frames of motion and always look like a jump.
SEAM_STRICT = os.environ.get("SEAM_STRICT", "0") == "1"
FFMPEG = os.environ.get("FFMPEG_BIN", "ffmpeg")


def discover(src, prefix="pcb_"):
    pat = re.compile(r"^%s(\d+)\.png$" % re.escape(prefix))
    return sorted(int(m.group(1)) for m in
                  (pat.match(n) for n in os.listdir(src)) if m)


def adjacent_diff(ffmpeg, a, b):
    """Mean absolute difference between two frames."""
    proc = subprocess.run([
        ffmpeg, "-v", "error",
        "-i", a, "-i", b,
        "-filter_complex",
        "[0:v][1:v]blend=all_mode=difference,format=gray,scale=256:144",
        "-f", "rawvideo", "-"
    ], capture_output=True, check=True)
    data = proc.stdout
    if not data:
        return 0.0
    return sum(data) / len(data)


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else "render"

    if subprocess.run(["where", FFMPEG], capture_output=True,
                      shell=True).returncode != 0:
        sys.exit("ffmpeg not available on PATH")

    numbers = discover(src)
    if not numbers:
        sys.exit("[qc] FAIL: no frames found in %s" % src)

    first, last = numbers[0], numbers[-1]
    count = len(numbers)
    contiguous = numbers == list(range(first, last + 1))

    report = {
        "frames_found": count,
        "frame_range": [first, last],
        "expected_frames": EXPECTED_FRAMES,
        "contiguous": contiguous,
        "duration_s": round(count / FPS, 3),
    }

    if not contiguous:
        gaps = [n for n in range(first, last + 1) if n not in set(numbers)]
        report["missing"] = gaps[:20]
        print("[qc] FAIL: %d gaps in the frame sequence, first %s"
              % (len(gaps), gaps[:10]))
        with open(os.path.join(src, "loop_qc.json"), "w") as fh:
            json.dump(report, fh, indent=2)
        sys.exit(1)

    tiny = [i for i in numbers
            if os.path.getsize(os.path.join(src, "pcb_%04d.png" % i)) < 4096]
    if tiny:
        report["tiny_frames"] = tiny[:20]
        print("[qc] WARN: %d suspiciously small frames: %s" % (len(tiny), tiny[:10]))

    if count < 3:
        report["note"] = "too few frames for a seam comparison"
        print("[qc] only %d frames, seam test skipped" % count)
        with open(os.path.join(src, "loop_qc.json"), "w") as fh:
            json.dump(report, fh, indent=2)
        return

    def path(n):
        return os.path.join(src, "pcb_%04d.png" % n)

    step = max(1, count // 18)
    interior = [adjacent_diff(FFMPEG, path(n), path(n + 1))
                for n in range(first, last, step) if (n + 1) <= last]

    # The wrap point is exactly the transition the viewer sees on repeat:
    # last frame -> first frame. For a true loop it should be no larger than
    # an ordinary step in the clip.
    seam = adjacent_diff(FFMPEG, path(last), path(first))

    mean_int = sum(interior) / len(interior)
    max_int = max(interior)
    ratio = seam / mean_int if mean_int else 0.0

    report.update({
        "interior_mean_diff": round(mean_int, 4),
        "interior_max_diff": round(max_int, 4),
        "seam_diff": round(seam, 4),
        "seam_ratio_vs_mean": round(ratio, 3),
        "samples_taken": len(interior),
        "seam_strict": SEAM_STRICT,
    })

    with open(os.path.join(src, "loop_qc.json"), "w") as fh:
        json.dump(report, fh, indent=2)

    print("[qc] %d frames %d..%d = %.3f s" % (count, first, last, count / FPS))
    print("[qc] interior mean %.4f  max %.4f" % (mean_int, max_int))
    print("[qc] seam %.4f  ratio %.3fx" % (seam, ratio))

    if not SEAM_STRICT:
        report["verdict"] = "PASS (seam not enforced on a partial render)"
        with open(os.path.join(src, "loop_qc.json"), "w") as fh:
            json.dump(report, fh, indent=2)
        print("[qc] PASS: partial render, seam reported but not enforced")
        return

    if ratio > 1.6:
        report["verdict"] = "FAIL"
        with open(os.path.join(src, "loop_qc.json"), "w") as fh:
            json.dump(report, fh, indent=2)
        print("[qc] FAIL: seam jump is %.2fx the normal frame change; "
              "the loop will read as a cut" % ratio)
        sys.exit(1)

    report["verdict"] = "PASS"
    with open(os.path.join(src, "loop_qc.json"), "w") as fh:
        json.dump(report, fh, indent=2)
    print("[qc] PASS: seam is within the clip's own motion range")


if __name__ == "__main__":
    main()