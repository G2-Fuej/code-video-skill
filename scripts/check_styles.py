"""check_styles.py -- render one frame of every style and save a contact sheet.

This is the fast correctness gate: it proves all 19 engine styles execute,
return the right shape, and carry no NaNs, without paying for a full render.
"""
from __future__ import annotations

import pathlib
import sys

import numpy as np
import cv2

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "engine"))

import brief as brief_mod          # noqa: E402
import director                    # noqa: E402
from core import Palette, W, H      # noqa: E402
from stage import Ctx               # noqa: E402

# a neutral brief: no project data, so this tests the engine, not the content
BRIEF = {
    "title": "STYLE CHECK",
    "subtitle": "one frame per style",
    "duration": 61.0, "fps": 60, "seed": 11,
    "palette": {
        "primary": "#2563EB", "accent": "#14B8A6", "danger": "#E11D48",
        "bg": "#08090C", "ink": "#E8EAF0", "sub": "#8A93A6",
        "paper": "#F2EFE6", "warm": "#F5A524",
    },
    "music": {"enabled": False, "bpm": 96},
    "data": {"heights": [28, 84, 252, 30, 71, 47, 295, 31, 83, 542, 289, 216,
                         23, 46, 16, 176, 353, 14, 230, 173]},
    "endcard_seconds": 2.0,
    "beats": [
        {"role": "title", "headline": "STYLE CHECK", "tags": ["title"]},
        {"role": "mechanics", "headline": "MECHANICS", "tags": ["mechanics"]},
        {"role": "problem", "headline": "THE PROBLEM", "tags": ["problem"]},
        {"role": "repair", "headline": "THE FIX", "tags": ["repair"]},
        {"role": "code", "headline": "CODE", "tags": ["code"]},
        {"role": "features", "headline": "FEATURES", "tags": ["features"]},
        {"role": "components", "headline": "COMPONENTS", "tags": ["components"]},
        {"role": "trust", "headline": "TRUST", "tags": ["trust"]},
        {"role": "ecosystem", "headline": "ECOSYSTEM", "tags": ["ecosystem"]},
        {"role": "flow", "headline": "FLOW", "tags": ["flow"]},
        {"role": "architecture", "headline": "ARCHITECTURE", "tags": ["architecture"]},
        {"role": "scale", "headline": "SCALE", "tags": ["scale"]},
        {"role": "legal", "headline": "LEGAL", "tags": ["legal"]},
        {"role": "community", "headline": "COMMUNITY", "tags": ["community"]},
        {"role": "recompose", "headline": "RECOMPOSE", "tags": ["recompose"]},
        {"role": "progress", "headline": "PROGRESS", "tags": ["progress"]},
        {"role": "action", "headline": "ACTION", "tags": ["action"]},
        {"role": "fusion", "headline": "FUSION", "tags": ["fusion"]},
        {"role": "payoff", "headline": "PAYOFF", "payoff": "19", "tags": ["payoff"]},
    ],
    "endcard_lines": [["written, rendered and scored in code", "display_b", 46]],
}

PROBES = {  # style -> local time to sample (fraction of the act)
    "phyllotaxis": 0.85, "truchet": 0.6, "flow": 0.7, "voronoi": 0.45,
    "ascii": 0.9, "halftone": 0.8, "swiss": 0.4, "crt": 0.85,
    "kaleidoscope": 0.6, "xy": 0.7, "blueprint": 0.95, "terrain": 0.7,
    "editorial": 0.9, "galaxy": 0.7, "destijl": 0.3, "pixelsort": 0.8,
    "plotter": 0.9, "metaballs": 0.6, "matrix": 0.95, "endcard": 0.8,
}


def main():
    spec = brief_mod.build_spec(BRIEF)
    pal = Palette(spec["palette"])
    out = ROOT / "out"
    out.mkdir(parents=True, exist_ok=True)

    instances = []
    for item in spec["timeline"]:
        cls = next(s for s in director.SCENES if getattr(s, "style", "") == item["style"])
        instances.append((cls, item, cls(item["beat"], spec)))

    # one context carrying the data the terrain style needs
    tiles = []
    report = []
    for idx, (cls, item, inst) in enumerate(instances):
        style = item["style"]
        dur = item["end"] - item["start"]
        t_local = dur * PROBES.get(style, 0.7)
        ctx = Ctx(pal=pal, spec=spec, scene_index=idx,
                  scene_name=getattr(cls, "name", style),
                  t_global=item["start"] + t_local, t_local=t_local,
                  duration=dur, beat=item["beat"], beat_phase=0.5,
                  seed=spec["seed"], data=spec.get("data", {}))
        canvas = inst.render(ctx)
        assert canvas.shape == (H, W, 3), f"{style}: bad shape {canvas.shape}"
        assert np.isfinite(canvas).all(), f"{style}: NaN/inf in frame"
        frame = np.clip(canvas, 0, 1)
        # label tile
        small = cv2.resize((frame * 255).astype(np.uint8), (480, 270),
                           interpolation=cv2.INTER_AREA)
        cv2.rectangle(small, (0, 0), (479, 269), (40, 40, 40), 1)
        cv2.putText(small, f"{idx+1:02d} {style.upper()}", (10, 254),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
        tiles.append(small)
        report.append((style, float(frame.mean()), float(frame.std())))

    rows = []
    per_row = 4
    for i in range(0, len(tiles), per_row):
        chunk = tiles[i:i + per_row]
        while len(chunk) < per_row:
            chunk.append(np.zeros((270, 480, 3), np.uint8))
        rows.append(np.hstack(chunk))
    sheet = np.vstack(rows)
    path = out / "style-check.png"
    cv2.imwrite(str(path), sheet)
    print(f"wrote {path} ({sheet.shape[1]}x{sheet.shape[0]})")
    for style, mean, std in report:
        flag = "  <-- FLAT" if std < 0.02 else ""
        print(f"{style:<14} mean={mean:.3f} std={std:.3f}{flag}")


if __name__ == "__main__":
    main()
