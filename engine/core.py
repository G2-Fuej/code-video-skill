"""core.py -- shared primitives for the pure-code video engine.

Every pixel is computed here with numpy/OpenCV; nothing is sampled or fetched.

Geometry is read from the environment at import time, before any scene class is
defined. Scenes do `from core import W, H`, which binds these values once, so a
caller that wants a different frame size must set the variables and start a new
process (see scripts/render_pcl.py --preview, which re-execs itself).
"""
from __future__ import annotations

import functools
import os
import numpy as np
import cv2

W = int(os.environ.get("CODE_VIDEO_W", "1920"))
H = int(os.environ.get("CODE_VIDEO_H", "1080"))
FPS = int(os.environ.get("CODE_VIDEO_FPS", "60"))
TAU = 2.0 * np.pi


# --------------------------------------------------------------------------
# colour
# --------------------------------------------------------------------------
def hex_rgb(code: str) -> np.ndarray:
    code = code.lstrip("#")
    return np.array([int(code[i:i + 2], 16) for i in (0, 2, 4)], np.float32) / 255.0


def mix(a, b, t: float) -> np.ndarray:
    return a * (1.0 - t) + b * t


class Palette:
    """Colour role map built from the spec; every scene reads from this."""

    def __init__(self, d: dict):
        self.primary = hex_rgb(d.get("primary", "#2563EB"))
        self.accent = hex_rgb(d.get("accent", "#14B8A6"))
        self.danger = hex_rgb(d.get("danger", "#E11D48"))
        self.bg = hex_rgb(d.get("bg", "#08090C"))
        self.ink = hex_rgb(d.get("ink", "#E8EAF0"))
        self.sub = hex_rgb(d.get("sub", "#8A93A6"))
        self.paper = hex_rgb(d.get("paper", "#F2EFE6"))
        self.warm = hex_rgb(d.get("warm", "#F5A524"))

    def ramp(self, x):
        """primary -> accent ramp for a float array in 0..1."""
        x = np.clip(x, 0.0, 1.0)[..., None]
        return self.primary * (1.0 - x) + self.accent * x


# --------------------------------------------------------------------------
# canvas
# --------------------------------------------------------------------------
def bg_canvas(pal: Palette, tint: float = 0.0) -> np.ndarray:
    c = np.empty((H, W, 3), np.float32)
    c[:] = pal.bg
    if tint:
        c += pal.primary * tint
    return c


def u8(canvas: np.ndarray) -> np.ndarray:
    return (np.clip(canvas, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8)


def add(canvas: np.ndarray, colour, mask) -> None:
    """Additive light: colour (3,) or (H,W,3), mask (H,W) or float."""
    canvas += colour * mask[..., None] if np.ndim(colour) == 1 else colour * mask[..., None]


def over(canvas: np.ndarray, colour, alpha) -> None:
    """Alpha-composite colour over canvas in place."""
    if np.ndim(colour) == 1:
        canvas *= (1.0 - alpha)[..., None]
        canvas += colour * alpha[..., None]
    else:
        canvas *= (1.0 - alpha)[..., None]
        canvas += colour * alpha[..., None]


def stroke(canvas, pts, colour, thickness=2, alpha=1.0, glow=0.0, closed=False):
    """Anti-aliased polyline via a uint8 mask (cv2 AA needs 8-bit)."""
    arr = np.asarray(pts, np.int32).reshape(-1, 1, 2)
    m = np.zeros((H, W), np.uint8)
    cv2.polylines(m, [arr], closed, 255, thickness, cv2.LINE_AA)
    a = m.astype(np.float32) * (alpha / 255.0)
    if glow:
        g = cv2.GaussianBlur(a, (0, 0), glow)
        canvas += colour * g[..., None] * 1.6
    over(canvas, colour, a)


def fill_poly(canvas, poly, colour, alpha=1.0, edge=None, thickness=2):
    m = np.zeros((H, W), np.uint8)
    cv2.fillPoly(m, [np.asarray(poly, np.int32)], 255, cv2.LINE_AA)
    if edge is not None:
        cv2.polylines(m, [np.asarray(poly, np.int32)], True, 200, thickness, cv2.LINE_AA)
    a = m.astype(np.float32) * (alpha / 255.0)
    over(canvas, colour, a)


def disc(canvas, cx, cy, r, colour, alpha=1.0, soft=0.0):
    if soft > 0:
        yy, xx = COORDS
        d = np.hypot(xx - cx, yy - cy)
        a = np.clip((r - d) / max(soft, 1e-3), 0.0, 1.0) * alpha
        over(canvas, colour, a)
    else:
        m = np.zeros((H, W), np.uint8)
        cv2.circle(m, (int(cx), int(cy)), int(r), 255, -1, cv2.LINE_AA)
        over(canvas, colour, m.astype(np.float32) * (alpha / 255.0))


@functools.lru_cache(maxsize=4)
def _coords():
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    return yy, xx


COORDS = _coords()


def unit_coords():
    yy, xx = COORDS
    return xx / (W - 1), yy / (H - 1)


@functools.lru_cache(maxsize=4)
def polar():
    yy, xx = COORDS
    dx = xx - W * 0.5
    dy = yy - H * 0.5
    return np.hypot(dx, dy), np.arctan2(dy, dx)


# --------------------------------------------------------------------------
# easing / timing
# --------------------------------------------------------------------------
def clamp01(x):
    return np.clip(x, 0.0, 1.0)


def smoothstep(e0, e1, x):
    t = np.clip((np.asarray(x, np.float32) - e0) / (e1 - e0 + 1e-9), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def ease_out(x):
    x = float(np.clip(x, 0.0, 1.0))
    return 1.0 - (1.0 - x) ** 3


def ease_in_out(x):
    x = float(np.clip(x, 0.0, 1.0))
    return x * x * (3.0 - 2.0 * x)


def window(t, a, b, fade=0.35):
    """1 inside [a,b] with soft edges, used for beat-synced reveals."""
    return smoothstep(a - fade, a, t) * (1.0 - smoothstep(b, b + fade, t))


# --------------------------------------------------------------------------
# deterministic noise
# --------------------------------------------------------------------------
def hash01(*idx):
    """Deterministic scalar hash in [0,1) from integer or float indices."""
    h = np.uint64(1469598103934665603)
    for v in idx:
        h = (h ^ np.uint64(int(v) & 0xFFFFFFFF)) * np.uint64(1099511628211)
        h ^= h >> np.uint64(13)
    return float(h % np.uint64(1000000)) / 1000000.0


def hash_grid(shape, seed) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.random(shape).astype(np.float32)


def noise_field(seed, gh=12, gw=24, smooth=True) -> np.ndarray:
    """Smooth value noise stretched to full frame."""
    g = np.random.default_rng(seed).random((gh, gw)).astype(np.float32)
    f = cv2.resize(g, (W, H), interpolation=cv2.INTER_CUBIC)
    if smooth:
        f = cv2.GaussianBlur(f, (0, 0), 12)
    return np.clip(f, 0.0, 1.0)


def fbm(seed, octaves=4, gh=6, gw=10) -> np.ndarray:
    acc = np.zeros((H, W), np.float32)
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        acc += amp * noise_field(seed + o * 977, gh * 2 ** o, gw * 2 ** o, smooth=False)
        tot += amp
        amp *= 0.5
    acc /= tot
    return cv2.GaussianBlur(acc, (0, 0), 1.5)


def grain(seed, amount=0.02) -> np.ndarray:
    rng = np.random.default_rng(seed)
    g = rng.standard_normal((H, W), dtype=np.float32) * amount
    return g


class Lines:
    """Batch many segments into one mask, then composite once.

    Drawing 10k individual rules through stroke() would allocate 10k full-frame
    buffers; this keeps a single uint8 mask and lets cv2 rasterise into it.
    """

    def __init__(self):
        self.mask = np.zeros((H, W), np.uint8)

    def line(self, x0, y0, x1, y1, thickness=1):
        cv2.line(self.mask, (int(x0), int(y0)), (int(x1), int(y1)), 255,
                 thickness, cv2.LINE_AA)

    def poly(self, pts, thickness=1, closed=False):
        cv2.polylines(self.mask, [np.asarray(pts, np.int32).reshape(-1, 1, 2)],
                      closed, 255, thickness, cv2.LINE_AA)

    def draw(self, canvas, colour, alpha=1.0, glow=0.0):
        a = self.mask.astype(np.float32) * (alpha / 255.0)
        if glow:
            canvas += np.asarray(colour, np.float32) * cv2.GaussianBlur(a, (0, 0), glow)[..., None] * 1.5
        over(canvas, colour, a)


_GRAIN_CACHE: list[np.ndarray] = []


def arc(mask: np.ndarray, cx, cy, r, a0, a1, colour=255, thickness=1):
    """Quarter/eighth circle on a uint8 mask.

    cv2 >= 5 dropped cv2.arc(); cv2.ellipse uses the same angle convention
    (0 deg = 3 o'clock, clockwise because y points down), so this is a
    drop-in replacement that keeps every call site readable.
    """
    cv2.ellipse(mask, (int(cx), int(cy)), (int(r), int(r)), 0.0, float(a0),
                float(a1), colour, thickness, cv2.LINE_AA)


def grain_cycle(n=24, amount=0.012) -> np.ndarray:
    """Precompute a short loop of grain so finish() costs no RNG per frame."""
    if not _GRAIN_CACHE:
        for i in range(n):
            rng = np.random.default_rng(90001 + i)
            _GRAIN_CACHE.append(rng.standard_normal((H, W), dtype=np.float32) * amount)
    return _GRAIN_CACHE[int(n) % len(_GRAIN_CACHE)]


@functools.lru_cache(maxsize=2)
def vignette() -> np.ndarray:
    yy, xx = COORDS
    dx = (xx - W / 2) / (W / 2)
    dy = (yy - H / 2) / (H / 2)
    r = np.sqrt(dx * dx * 0.85 + dy * dy)
    return np.clip(1.15 - 0.55 * r, 0.12, 1.0).astype(np.float32)


def finish(canvas, seed, grain_amt=0.012, vig=1.0) -> np.ndarray:
    """Global grain + vignette so every scene shares one emulsion."""
    if grain_amt:
        g = grain_cycle(amount=grain_amt)
        canvas += g[..., None] if seed % 3 else grain(seed, grain_amt)[..., None]
    if vig:
        v = vignette()
        canvas *= (1.0 - vig) + vig * v[..., None]
    return canvas


# --------------------------------------------------------------------------
# beat grid
# --------------------------------------------------------------------------
def beat(t: float, bpm: float) -> float:
    return t * bpm / 60.0
