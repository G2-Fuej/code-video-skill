"""typekit.py -- text rasterisation and layout helpers.

All glyphs are rendered at init and cached as float masks; nothing is sampled
from disk except the OS fonts themselves (never counted as video material).
"""
from __future__ import annotations

import functools
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from core import W, H, over, COORDS

FONT_DIR = "C:/Windows/Fonts/"

# role -> candidate filenames, first hit wins
FACES = {
    "display": ["georgia.ttf", "times.ttf", "segoeui.ttf"],
    "display_b": ["georgiab.ttf", "georgia.ttf", "arialbd.ttf"],
    "sans": ["segoeui.ttf", "calibri.ttf", "arial.ttf"],
    "sans_b": ["segoeuib.ttf", "seguisb.ttf", "arialbd.ttf"],
    "sans_sb": ["seguisb.ttf", "segoeui.ttf"],
    "mono": ["consola.ttf", "cour.ttf"],
    "mono_b": ["consolab.ttf", "consola.ttf"],
    "black": ["impact.ttf", "arialbd.ttf"],
    "cjk": ["msyh.ttc", "simhei.ttf"],
    "cjk_b": ["msyhbd.ttc", "msyh.ttc", "simhei.ttf"],
    "swiss": ["bahnschrift.ttf", "segoeui.ttf"],
}

_resolved: dict[str, str] = {}
_CJK_ROLES = ("cjk", "cjk_b")


def _has_cjk(s: str) -> bool:
    return any("\u3400" <= ch <= "\u9fff" or "\uff00" <= ch <= "\uffef" for ch in s)


def face_for(role: str, text: str = "") -> str:
    """Resolve a role to a font, falling back to a CJK face when needed.

    Bahnschrift, Georgia and Consolas carry no CJK glyphs, so a mixed-language
    brief would render tofu boxes. Any role asked to draw CJK gets the CJK face
    of matching weight instead.
    """
    if text and _has_cjk(text) and role not in _CJK_ROLES:
        role = "cjk_b" if role.endswith("_b") or role in ("black", "swiss") else "cjk"
    return face(role)


def face(role: str) -> str:
    if role not in _resolved:
        for cand in FACES.get(role, FACES["sans"]):
            import os
            p = FONT_DIR + cand
            if os.path.exists(p):
                _resolved[role] = p
                break
        else:
            _resolved[role] = FONT_DIR + "segoeui.ttf"
    return _resolved[role]


@functools.lru_cache(maxsize=512)
def _font(role: str, size: int, text: str = ""):
    return ImageFont.truetype(face_for(role, text), size)


@functools.lru_cache(maxsize=2048)
def mask(text: str, role: str, size: int, tracking: int = 0) -> tuple[np.ndarray, int]:
    """Return (alpha mask 0..1, advance width). Cached -- text is baked once."""
    f = _font(role, size, text)
    if tracking:
        text = (" " * 0).join(text)
    l, t, r, b = f.getbbox(text)
    pad = size // 3
    w = max(1, r - l + pad * 2)
    h = max(1, b - t + pad * 2)
    img = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(img)
    d.text((pad - l, pad - t), text, font=f, fill=255)
    arr = np.asarray(img, np.float32) / 255.0
    return arr, r - l


@functools.lru_cache(maxsize=2048)
def tracked_mask(text: str, role: str, size: int, track_px: float) -> np.ndarray:
    """Letter-spaced text, cropped to its ink so layout coordinates are stable.

    Glyph heights differ (a '/' inside a CJK line is much taller than a comma),
    so the ink is rendered on a scratch canvas, then cropped to its bounding
    box with a constant margin. Every mask therefore reports the same origin
    convention: top-left of the drawing plus `pad` pixels.
    """
    if not text:
        return np.zeros((1, 1), np.float32)
    f = _font(role, size, text)
    pad = max(2, size // 6)
    gap = int(round(track_px))
    # scratch canvas with generous headroom for ascenders/descenders
    cw = int(size * (1.2 * len(text) + 2)) + gap * len(text) + pad * 4
    ch = int(size * 2.2) + pad * 4
    img = Image.new("L", (cw, ch), 0)
    d = ImageDraw.Draw(img)
    x = pad * 2
    base = pad * 2 + int(size * 1.05)
    for c_ in text:
        l, t, r, b = f.getbbox(c_, anchor="ls")
        d.text((x - l, base), c_, font=f, fill=255, anchor="ls")
        x += max(1, r - l) + gap
    arr = np.asarray(img, np.float32) / 255.0
    ys, xs = np.nonzero(arr > 0.02)
    if len(ys) == 0:
        return np.zeros((1, 1), np.float32)
    y0, y1 = ys.min(), ys.max() + 1
    x0, x1 = xs.min(), xs.max() + 1
    crop = arr[max(0, y0 - pad):y1 + pad, max(0, x0 - pad):x1 + pad]
    return np.ascontiguousarray(crop)


def blit(canvas, m: np.ndarray, x: float, y: float, colour, alpha=1.0, anchor="lt"):
    """Composite a cached mask onto the canvas at (x, y)."""
    h, w = m.shape
    if anchor == "ct":
        x -= w / 2
    elif anchor == "rt":
        x -= w
    elif anchor == "lm":
        y -= h / 2
    elif anchor == "cm":
        x -= w / 2
        y -= h / 2
    elif anchor == "rm":
        x -= w
        y -= h / 2
    elif anchor == "cb":
        x -= w / 2
        y -= h
    xi, yi = int(round(x)), int(round(y))
    x0, y0 = max(0, xi), max(0, yi)
    x1, y1 = min(W, xi + w), min(H, yi + h)
    if x1 <= x0 or y1 <= y0:
        return
    sub = m[y0 - yi:y1 - yi, x0 - xi:x1 - xi] * alpha
    over(canvas[y0:y1, x0:x1], colour, sub)


def text(canvas, s, x, y, role="sans", size=40, colour=(1, 1, 1), alpha=1.0,
         tracking=0.0, anchor="lt"):
    m = tracked_mask(s, role, size, tracking) if tracking else mask(s, role, size)[0]
    blit(canvas, m, x, y, np.asarray(colour, np.float32), alpha, anchor)
    return m.shape[1]


def measure(s, role="sans", size=40, tracking=0.0) -> tuple[int, int]:
    m = tracked_mask(s, role, size, tracking) if tracking else mask(s, role, size)[0]
    return m.shape[1], m.shape[0]


def fit_mask(s, role, size, max_w, tracking=0.0, min_size=10):
    """Shrink the type size until the string fits inside max_w pixels.

    Layout is authored in absolute pixels, so long project names or repo URLs
    would otherwise run off the frame; this keeps every line inside its column.
    """
    sz = int(size)
    while sz > min_size:
        m = tracked_mask(s, role, sz, tracking if tracking == 0 else tracking * sz / size)
        if m.shape[1] <= max_w:
            return m
        sz = int(sz * 0.92)
    return tracked_mask(s, role, min_size, 0.0)


def fit_text(canvas, s, x, y, role="sans", size=40, max_w=1600, colour=(1, 1, 1),
             alpha=1.0, tracking=0.0, anchor="lt"):
    m = fit_mask(s, role, size, max_w, tracking)
    blit(canvas, m, x, y, np.asarray(colour, np.float32), alpha, anchor)
    return m.shape[1]


def rule(canvas, x0, y0, x1, y1, colour, alpha=1.0, width=2):
    """Hairline rule, axis aligned or diagonal, anti-aliased."""
    import cv2
    m = np.zeros((H, W), np.uint8)
    cv2.line(m, (int(x0), int(y0)), (int(x1), int(y1)), 255, width, cv2.LINE_AA)
    over(canvas, np.asarray(colour, np.float32), m.astype(np.float32) / 255.0 * alpha)


def block(canvas, x, y, w, h, colour, alpha=1.0):
    x0, y0 = max(0, int(x)), max(0, int(y))
    x1, y1 = min(W, int(x + w)), min(H, int(y + h))
    if x1 <= x0 or y1 <= y0:
        return
    over(canvas[y0:y1, x0:x1], np.asarray(colour, np.float32),
         np.full((y1 - y0, x1 - x0), alpha, np.float32))
