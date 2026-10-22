"""smoke.py -- fast engine check on a 4 second, 4 act spec.

Builds the spec through brief.build_spec() so the same code path used in
production gets exercised: brief -> timeline -> frames -> mp4.
"""
from __future__ import annotations

import json
import os
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "engine"))

import brief as brief_mod
import director


SMOKE_BRIEF = {
    "title": "SMOKE TEST",
    "subtitle": "engine check",
    "duration": 4.0,
    "fps": 60,
    "seed": 7,
    "output": "smoke.mp4",
    "palette": {
        "primary": "#2563EB", "accent": "#14B8A6", "danger": "#E11D48",
        "bg": "#08090C", "ink": "#E8EAF0", "sub": "#8A93A6",
        "paper": "#F2EFE6", "warm": "#F5A524",
    },
    "music": {"enabled": True, "bpm": 96},
    "data": {"heights": [28, 84, 252, 30, 71, 47, 295, 31, 83, 542, 289, 216]},
    "endcard_seconds": 1.0,
    "beats": [
        {"role": "title", "headline": "SMOKE TEST", "tags": ["title"]},
        {"role": "mechanics", "headline": "TRUCHET WEAVE", "tags": ["mechanics"]},
        {"role": "problem", "headline": "SIGNAL LOST", "tags": ["problem"]},
        {"role": "payoff", "payoff": "OK", "headline": "VERIFIED", "tags": ["payoff"]},
    ],
    "endcard": {"signature": "written, rendered and scored in code"},
    "endcard_lines": [["written, rendered and scored in code", "display_b", 46]],
}


def main():
    spec = brief_mod.build_spec(SMOKE_BRIEF)
    out = HERE.parent / "out" / "smoke.mp4"
    out.parent.mkdir(parents=True, exist_ok=True)
    print(json.dumps([{"style": i["style"], "start": i["start"], "end": i["end"]}
                      for i in spec["timeline"]], indent=2))
    director.render(spec, str(out), workdir=str(out.parent / "_work"))
    info = director.probe(out)
    for k, v in info.items():
        print(f"{k}: {v}")
    print("size:", out.stat().st_size)


if __name__ == "__main__":
    main()
