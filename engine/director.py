"""director.py -- the render pipeline.

Frames are produced by numpy/OpenCV, piped as raw RGB into ffmpeg, and the
procedural score is muxed in. Nothing is downloaded; nothing is sampled.
"""
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core import W, H, FPS, Palette, u8, finish  # noqa: E402
from stage import Ctx, Flash  # noqa: E402
import score as score_mod  # noqa: E402

import scenes_a  # noqa: E402
import scenes_b  # noqa: E402

SCENES = [
    scenes_a.Phyllotaxis, scenes_a.Truchet, scenes_a.FlowField, scenes_a.Voronoi,
    scenes_a.AsciiTorus, scenes_a.Halftone, scenes_a.SwissGrid,
    scenes_b.CRT, scenes_b.Kaleido, scenes_b.Oscilloscope, scenes_b.Blueprint,
    scenes_b.Terrain, scenes_b.Editorial, scenes_b.Galaxy, scenes_b.DeStijl,
    scenes_b.PixelSort, scenes_b.Plotter, scenes_b.Metaballs, scenes_b.Matrix,
    scenes_b.EndCard,
]


def ffmpeg_exe() -> str:
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        for c in ("ffmpeg", "ffmpeg.exe"):
            from shutil import which
            p = which(c)
            if p:
                return p
        raise RuntimeError("ffmpeg not found: pip install imageio-ffmpeg")


def build_timeline(spec) -> list[dict]:
    """Normalise the spec timeline into concrete (scene, start, end) slots."""
    tl = spec.get("timeline")
    if not tl:
        raise ValueError("spec has no timeline")
    out = []
    for item in tl:
        out.append({
            "style": item.get("style", "scene"),
            "start": float(item.get("start", 0)),
            "end": float(item.get("end", 0)),
            "beat": item.get("beat", {}) or {},
            "caption": item.get("caption", ""),
            "flash": item.get("flash"),
        })
    return out


def render(spec, out_path: str, workdir: str | None = None, verbose=True) -> str:
    t_start = time.time()
    # The scene modules bound W/H/FPS when they imported core, so the spec must
    # agree with the process it is running in. A mismatch is a real bug (the
    # output would silently ignore the requested resolution), so fail loudly
    # instead of rendering the wrong size.
    want_w, want_h = int(spec.get("width", W)), int(spec.get("height", H))
    want_fps = int(spec.get("fps", FPS))
    if (want_w, want_h, want_fps) != (W, H, FPS):
        raise ValueError(
            f"spec asks for {want_w}x{want_h}@{want_fps} but this process renders "
            f"{W}x{H}@{FPS}. Set CODE_VIDEO_W/H/FPS in the environment before "
            f"starting python (the renderer must run in a fresh process).")
    workdir = pathlib.Path(workdir or (pathlib.Path(out_path).parent / "_work"))
    workdir.mkdir(parents=True, exist_ok=True)
    pal = Palette(spec.get("palette", {}))
    timeline = build_timeline(spec)
    duration = float(spec.get("duration", 61.0))
    total_frames = int(round(duration * FPS))

    # ---- scene instances -------------------------------------------------
    instances = []
    for item in timeline:
        cls = None
        for s in SCENES:
            if getattr(s, "style", "") == item["style"]:
                cls = s
                break
        if cls is None:
            raise ValueError(f"unknown style: {item['style']}")
        instances.append((cls, item, cls(item["beat"], spec)))

    # ---- score -----------------------------------------------------------
    wav = workdir / "score.wav"
    if spec.get("music", {}).get("enabled", True):
        samples = score_mod.build(
            duration=duration,
            bpm=float(spec.get("music", {}).get("bpm", 96)),
            seed=int(spec.get("seed", 7)),
            act_map=score_mod.default_act_map(spec),
        )
        score_mod.write_wav(str(wav), samples)
        if verbose:
            print(f"[score] wrote {wav} ({len(samples)/score_mod.SR:.1f}s)")

    # ---- ffmpeg pipe -----------------------------------------------------
    ff = ffmpeg_exe()
    cmd = [ff, "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "pipe:0"]
    if wav.exists():
        cmd += ["-i", str(wav)]
    cmd += ["-c:v", "libx264", "-preset", "medium", "-crf", "17",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart"]
    if wav.exists():
        cmd += ["-c:a", "aac", "-b:a", "192k", "-shortest"]
    cmd += [str(out_path)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
                            stderr=subprocess.PIPE)

    written = 0
    try:
        for f in range(total_frames):
            t = f / FPS
            canvas = render_at(t, instances, pal, spec, total_frames)
            proc.stdin.write(u8(canvas).tobytes())
            written += 1
            if verbose and written % 60 == 0:
                el = time.time() - t_start
                print(f"[frames] {written}/{total_frames}  "
                      f"{written / max(el, 1e-6):.1f} fps  eta {(total_frames-written)/max(written/max(el,1e-6),1e-6):.0f}s",
                      flush=True)
    finally:
        proc.stdin.close()
        err = proc.stderr.read().decode("utf-8", "replace")
        code = proc.wait()
    if code != 0:
        raise RuntimeError(f"ffmpeg failed ({code}):\n{err[-2500:]}")
    if verbose:
        print(f"[done] {out_path} in {time.time()-t_start:.1f}s")
    return out_path


def render_at(t, instances, pal, spec, total_frames):
    """Pick the active scene for time t and render it."""
    cur = None
    for (cls, item, inst) in instances:
        if item["start"] <= t < item["end"]:
            cur = (cls, item, inst)
            break
    if cur is None:
        # past the end: hold the last scene
        cur = instances[-1]
    cls, item, inst = cur
    local = t - item["start"]
    dur = max(1e-6, item["end"] - item["start"])

    # hard-cut flash frame at the very start of an act that requests it
    if item.get("flash") and local < 1.0 / FPS:
        f = Flash(item["flash"])
        return f.render(Ctx(pal, spec, 0, item["style"], t, local, dur, 0, 0, 0))

    ctx = Ctx(
        pal=pal,
        spec=spec,
        scene_index=instances.index((cls, item, inst)),
        scene_name=getattr(cls, "name", item["style"]),
        t_global=t,
        t_local=local,
        duration=dur,
        beat=item["beat"],
        beat_phase=(local * float(spec.get("music", {}).get("bpm", 96)) / 60.0) % 1.0,
        seed=int(spec.get("seed", 7)),
        data=spec.get("data", {}),
    )
    canvas = inst.render(ctx)
    return finish(canvas, seed=int(spec.get("seed", 7)) + int(t * 1000) % 9973,
                  grain_amt=float(spec.get("grain", 0.012)),
                  vig=float(spec.get("vignette", 1.0)))


def probe(path) -> dict:
    ff = ffmpeg_exe()
    out = subprocess.run([ff, "-i", str(path)], capture_output=True, text=True,
                         encoding="utf-8", errors="replace").stderr
    info = {}
    for line in out.splitlines():
        line = line.strip()
        if line.startswith("Duration:"):
            info["duration"] = line.split(",")[0].replace("Duration:", "").strip()
        if "Video:" in line:
            info["video"] = line
        if "Audio:" in line:
            info["audio"] = line
    return info


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Pure-code video renderer")
    ap.add_argument("spec", help="path to the beat spec JSON")
    ap.add_argument("-o", "--out", default=None, help="output mp4")
    ap.add_argument("--workdir", default=None)
    ap.add_argument("--probe", action="store_true")
    args = ap.parse_args()
    spec = json.loads(pathlib.Path(args.spec).read_text(encoding="utf-8"))
    out = args.out or spec.get("output", "out.mp4")
    render(spec, out, args.workdir)
    if args.probe:
        for k, v in probe(out).items():
            print(f"{k}: {v}")


if __name__ == "__main__":
    main()