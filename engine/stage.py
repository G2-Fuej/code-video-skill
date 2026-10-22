"""stage.py -- scene framework.

A Scene is a pure function of local time: render(ctx, t_local) -> canvas.
The director owns the global clock, beat grid, transitions and the encoder.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import numpy as np

from core import W, H, FPS, Palette, bg_canvas, u8, finish


@dataclass
class Ctx:
    """Everything a scene may read. Immutable facts, plus the palette."""
    pal: Palette
    spec: dict
    scene_index: int
    scene_name: str
    t_global: float
    t_local: float
    duration: float
    beat: float
    beat_phase: float
    seed: int
    data: dict = field(default_factory=dict)


class Scene:
    name = "scene"
    style = ""
    caption = ""

    def render(self, ctx: Ctx) -> np.ndarray:
        raise NotImplementedError


def solid(colour, alpha=1.0):
    """Helper: a flat colour frame."""
    def make(ctx):
        c = np.empty((H, W, 3), np.float32)
        c[:] = np.asarray(colour, np.float32) * alpha
        return c
    return make


class Flash:
    """A single-frame hard cut used between acts -- no tween, one pure colour."""

    def __init__(self, colour):
        self.colour = colour

    def render(self, ctx: Ctx) -> np.ndarray:
        c = np.empty((H, W, 3), np.float32)
        c[:] = np.asarray(self.colour, np.float32)
        return c