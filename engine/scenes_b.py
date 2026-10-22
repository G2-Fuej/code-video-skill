"""scenes_b.py -- acts 8-19 of the 19-style reel."""
from __future__ import annotations

import numpy as np
import cv2

from core import (W, H, TAU, COORDS, bg_canvas, over, stroke, fill_poly, disc,
                  smoothstep, ease_out, ease_in_out, window, hash01, hash_grid,
                  noise_field, fbm, clamp01, polar, Lines)
from typekit import text, mask, tracked_mask, blit, rule, block, fit_mask
from stage import Scene


# --------------------------------------------------------------------------
# 08 CRT / VHS -- a signal that is losing sync
# --------------------------------------------------------------------------
class CRT(Scene):
    name = "CRT / VHS"
    style = "crt"

    def __init__(self, beat, spec):
        self.beat = beat
        self.checks = beat.get("claims", ["0 VIRUS", "0 AD", "0 TRACKER"])

    def render(self, ctx):
        pal = ctx.pal
        t = ctx.t_local
        c = bg_canvas(pal, 0.10)
        yy, xx = COORDS
        bars = np.floor(xx / (W / 8)).astype(int) % 8
        tint = np.array([0.55, 0.75, 0.35, 0.9, 0.25, 0.6, 0.45, 0.2], np.float32)[bars]
        c += pal.primary * (tint[..., None] * 0.18)
        c += pal.accent * (np.clip(1 - np.abs(yy / H - 0.5) * 2, 0, 1)[..., None] * 0.25)

        cy, cx = H * 0.42, W * 0.5
        d, th = polar()
        ring = np.clip(1 - np.abs((d - 260 - 18 * np.sin(th * 8 + t * 3)) / 6), 0, 1)
        c += pal.ink * ring[..., None] * 0.7

        for i, s in enumerate(self.checks):
            a = ease_out(clamp01((t - 0.35 - i * 0.45) / 0.35))
            if a > 0:
                m = tracked_mask(s, "mono_b", 54, 4.0)
                blit(c, m, W * 0.5 - m.shape[1] / 2, H * 0.62 + i * 78, pal.accent, a)

        sl = np.sin(yy * np.pi * 0.5) * 0.5 + 0.5
        c *= (0.82 + 0.18 * sl)[..., None]

        k = int(t * 60)
        shift = int(np.sin(k * 0.7) * 2 + np.sin(k * 2.3) * 1.2)
        r = np.roll(c[..., 0], shift + 3, axis=1)
        b = np.roll(c[..., 2], shift - 3, axis=1)
        c = np.stack([r, c[..., 1], b], -1)

        band_y = int(((t * 0.35) % 1.2 - 0.1) * H)
        if 0 <= band_y < H - 26:
            c[band_y:band_y + 26] = c[band_y:band_y + 26] * 0.35 + pal.ink * 0.18
        return c


# --------------------------------------------------------------------------
# 09 KALEIDOSCOPE
# --------------------------------------------------------------------------
class Kaleido(Scene):
    name = "KALEIDOSCOPE"
    style = "kaleidoscope"

    def __init__(self, beat, spec):
        self.beat = beat
        self.src = fbm(int(spec.get("seed", 7)) + 61, octaves=4, gh=8, gw=8)
        self.fold = 12

    def render(self, ctx):
        pal = ctx.pal
        t = ctx.t_local
        d, th = polar()
        seg = TAU / self.fold
        a = np.mod(th + t * 0.25, seg)
        a = np.abs(a - seg / 2)
        rad = d / (H * 0.62)
        xs = np.clip((np.cos(a) * rad * 0.8 + 0.5) * (W - 1), 0, W - 1).astype(np.int32)
        ys = np.clip((np.sin(a) * rad * 0.8 + 0.25) * (H - 1), 0, H - 1).astype(np.int32)
        tex = self.src[ys, xs]
        c = pal.ramp(tex) * (0.22 + 0.8 * tex[..., None])
        edge = np.clip(1 - np.abs(np.mod(th + t * 0.25, seg) - seg / 2) * 22, 0, 1)
        c += pal.ink * (edge * 0.18)[..., None]
        c *= np.clip(1.25 - rad, 0.15, 1.2)[..., None]
        cap = self.beat.get("caption", "")
        a2 = window(t, 0.7, ctx.duration, 0.4)
        if cap and a2 > 0.02:
            m = tracked_mask(cap, "cjk_b", 52, 5.0)
            blit(c, m, W * 0.5, H - 170, pal.ink, a2 * 0.95)
        return c


# --------------------------------------------------------------------------
# 10 OSCILLOSCOPE XY -- Lissajous
# --------------------------------------------------------------------------
class Oscilloscope(Scene):
    name = "OSCILLOSCOPE XY"
    style = "xy"

    def __init__(self, beat, spec):
        self.beat = beat
        self.labels = beat.get("steps", ["VERSION", "LOADER", "DOWNLOAD"])

    def render(self, ctx):
        pal = ctx.pal
        c = bg_canvas(pal, 0.02)
        t = ctx.t_local
        cx, cy = W * 0.5, H * 0.5
        grid = Lines()
        for gx in range(int(cx - 620), int(cx + 621), 62):
            grid.line(gx, cy - 380, gx, cy + 380, 1)
        for gy in range(int(cy - 380), int(cy + 381), 62):
            grid.line(cx - 620, gy, cx + 620, gy, 1)
        grid.draw(c, pal.primary, 0.13)
        axis = Lines()
        axis.line(cx - 620, cy, cx + 620, cy, 1)
        axis.line(cx, cy - 380, cx, cy + 380, 1)
        axis.draw(c, pal.accent, 0.30)

        k = int(t * 60)
        cycles = 3 + (k // 40) % 4
        phase = t * 1.8
        s = np.linspace(0, TAU, 4200, dtype=np.float32)
        x = cx + np.sin(cycles * s + phase) * 540
        y = cy + np.sin((cycles + 1) * s + phase * 0.7) * 340
        m = np.zeros((H, W), np.uint8)
        cv2.polylines(m, [np.stack([x, y], 1).astype(np.int32).reshape(-1, 1, 2)],
                      False, 255, 3, cv2.LINE_AA)
        a = m.astype(np.float32) / 255.0
        c += pal.accent * a[..., None] * 1.1
        c += pal.accent * cv2.GaussianBlur(a, (0, 0), 16)[..., None] * 0.9
        di = int((t * 900) % len(s))
        disc(c, x[di], y[di], 7, (1, 1, 1), 1.0, soft=2.0)
        for i, sname in enumerate(self.labels):
            a3 = smoothstep(0.6 + i * 0.8, 1.0 + i * 0.8, t)
            text(c, sname, 150, 150 + i * 64, "mono_b", 34, pal.ink, a3, tracking=4)
        return c


# --------------------------------------------------------------------------
# 11 BLUEPRINT -- a drawing that draws itself
# --------------------------------------------------------------------------
class Blueprint(Scene):
    name = "BLUEPRINT"
    style = "blueprint"

    def __init__(self, beat, spec):
        self.beat = beat
        self.mods = beat.get("modules", [
            {"name": "WPF SHELL", "sub": "XAML"},
            {"name": "VB MODULES", "sub": ".vb"},
            {"name": "PCLCS", "sub": ".cs"},
            {"name": "CI", "sub": "Actions"},
        ])

    def render(self, ctx):
        c = np.empty((H, W, 3), np.float32)
        c[:] = np.array([0.05, 0.13, 0.32], np.float32)
        t = ctx.t_local
        accent = ctx.pal.accent
        grid = Lines()
        for gx in range(0, W, 40):
            grid.line(gx, 0, gx, H, 1)
        for gy in range(0, H, 40):
            grid.line(0, gy, W, gy, 1)
        grid.draw(c, (0.55, 0.72, 0.95), 0.10)

        boxes = []
        bx, by, bw, bh = 210, 320, 300, 140
        for i in range(len(self.mods)):
            boxes.append((bx + (i % 2) * 520, by + (i // 2) * 250, bw, bh))

        prog = clamp01(t / (ctx.duration * 0.72))
        segs = []
        for (x, y, w, h) in boxes:
            segs += [((x, y), (x + w, y)), ((x + w, y), (x + w, y + h)),
                     ((x + w, y + h), (x, y + h)), ((x, y + h), (x, y))]
        n = max(1, int(prog * len(segs)))
        outline = Lines()
        for a_, b_ in segs[:n]:
            outline.line(a_[0], a_[1], b_[0], b_[1], 2)
        outline.draw(c, (0.82, 0.93, 1.0), 0.95)

        if prog > 0.6:
            p2 = clamp01((prog - 0.6) / 0.4)
            wire = [((bx + bw, by + bh / 2), (bx + 520, by + bh / 2)),
                    ((bx + 260, by + bh), (bx + 260, by + 250)),
                    ((bx + 520, by + 250 + bh / 2), (bx + 900, by + 250 + bh / 2))]
            wl = Lines()
            for i, (a_, b_) in enumerate(wire):
                if p2 * len(wire) > i:
                    wl.line(a_[0], a_[1], b_[0], b_[1], 2)
            wl.draw(c, accent, 0.9)

        for i, ((x, y, w, h), mod) in enumerate(zip(boxes, self.mods)):
            if prog > (i + 1) / max(1, len(boxes)) * 0.7:
                text(c, mod["name"], x + 24, y + 44, "mono_b", 30, (0.92, 0.97, 1.0), 0.95, tracking=3)
                text(c, mod["sub"], x + 24, y + 90, "mono", 24, accent, 0.85, tracking=2)

        text(c, self.beat.get("title", "DRAWING"), 210, 150, "mono_b", 40,
             (0.92, 0.97, 1.0), 0.9, tracking=8)
        rule(c, 210, 216, 760, 216, accent, 0.8, 3)
        text(c, self.beat.get("sheet", "REV A / 1:1"), W - 470, H - 110, "mono", 26,
             (0.75, 0.88, 1.0), 0.8, tracking=3)
        return c


# --------------------------------------------------------------------------
# 12 TERRAIN -- wireframe landscape whose heights are real source line counts
# --------------------------------------------------------------------------
class Terrain(Scene):
    name = "TERRAIN"
    style = "terrain"

    def __init__(self, beat, spec):
        self.beat = beat
        heights = (spec.get("data") or {}).get("heights") or [12, 40, 80, 30, 120, 60]
        h = np.asarray(heights, np.float32)
        h = h / (h.max() + 1e-6)
        self.grid_w = 150
        self.rows = 66
        u = np.linspace(0, 1, self.grid_w)
        self.prof = np.interp(u * (len(h) - 1), np.arange(len(h)), h).astype(np.float32)

    def render(self, ctx):
        pal = ctx.pal.warm
        c = bg_canvas(ctx.pal)
        t = ctx.t_local
        yy, xx = COORDS
        horizon = H * 0.56
        sky = np.clip(yy / horizon, 0, 1)
        c += np.array([0.16, 0.03, 0.24], np.float32) * (1 - sky)[..., None] * 1.3

        sun = Lines()
        for gy in range(int(horizon) - 180, int(horizon) + 40, 9):
            sun.line(W * 0.5 - 230, gy, W * 0.5 + 230, gy, 5)
        sun.draw(c, pal, 0.16)
        d, _ = polar()
        sunmask = np.clip(1 - (d - 200) / 3, 0, 1) * (yy < horizon - 30)
        c += np.array([1.0, 0.55, 0.35], np.float32) * sunmask[..., None] * 0.8

        cam = t * 0.55
        rows = []
        for r in range(self.rows):
            depth = 1.0 + (self.rows - 1 - r) * 0.16
            base_y = horizon + (H - horizon) * ((r / (self.rows - 1)) ** 2.1) * (6.5 / depth)
            row = []
            for i in range(self.grid_w):
                u = i / (self.grid_w - 1)
                hx = self.prof[(i + int(cam * 26)) % len(self.prof)]
                hgt = (hx * 0.9 + 0.14 * np.sin(u * 17 + cam * 2.4)
                       + 0.07 * np.sin(u * 43 - cam * 3.3))
                row.append((u * W * 1.42 - W * 0.21, base_y - hgt * 300 / depth))
            rows.append(row)

        # one mask per band of rows: depth fade is per-row, so bands keep the
        # 60 fps budget while still reading as continuous perspective
        band = 6
        for b0 in range(0, len(rows), band):
            layer = Lines()
            fade = clamp01(1.0 - (b0 / self.rows) * 0.95)
            for r in range(b0, min(b0 + band, len(rows))):
                row = rows[r]
                for i in range(len(row) - 1):
                    layer.line(row[i][0], row[i][1], row[i + 1][0], row[i + 1][1], 2)
                if r + 1 < len(rows):
                    for i in range(0, self.grid_w, 2):
                        layer.line(rows[r][i][0], rows[r][i][1],
                                   rows[r + 1][i][0], rows[r + 1][i][1], 1)
            layer.draw(c, pal, 0.55 * fade)
        return c


# --------------------------------------------------------------------------
# 13 EDITORIAL -- magazine spread
# --------------------------------------------------------------------------
class Editorial(Scene):
    name = "EDITORIAL"
    style = "editorial"

    def __init__(self, beat, spec):
        self.beat = beat
        body = beat.get("body", "")
        self.body = [x for x in body.split("\n") if x] or ["."]

    def render(self, ctx):
        pal = ctx.pal
        c = np.empty((H, W, 3), np.float32)
        c[:] = pal.paper
        t = ctx.t_local
        ink = np.array([0.08, 0.07, 0.06], np.float32)

        # left page: drop cap + a wrapped body column, measured so it cannot spill
        x0, col_w = 130, 690
        rule(c, x0, 150, x0 + col_w, 150, ink, 0.9, 3)
        text(c, self.beat.get("kicker", "COLOPHON"), x0, 178, "sans_b", 26,
             pal.primary, 1.0, tracking=6)
        head, rest = self.body[0], self.body[1:]
        y = 290
        cap = mask(head[:1], "display_b", 132)[0]
        blit(c, cap, x0, y - 36, ink, 0.95)
        cap_w = cap.shape[1] + 14
        # drop-cap paragraph: first line beside the cap, then full width
        first_line = head[1:]
        fm = fit_mask(first_line, "display", 32, col_w - cap_w)
        blit(c, fm, x0 + cap_w, y, ink, 0.95)
        y += max(cap.shape[0], fm.shape[0]) + 26
        # the body column: wrapped, and spread down the page so the spread
        # reads as a real layout instead of a corner of text
        col_lines: list[str] = []
        for line in rest:
            col_lines.extend(_wrap(line, 17))
        avail = (H - 200) - y
        if col_lines:
            lh = min(52, max(38, avail / max(1, len(col_lines))))
            for chunk in col_lines:
                m = fit_mask(chunk, "cjk", 30, col_w)
                blit(c, m, x0, y, ink, 0.88)
                y += lh
                if y > H - 200:
                    break
        rule(c, x0, H - 150, x0 + col_w, H - 150, ink, 0.25, 1)

        # right page: the pull quote, revealed line by line
        qx, qw = 1010, 760
        rule(c, qx, 150, qx + qw, 150, pal.primary, 0.9, 3)
        quote = self.beat.get("quote") or self.beat.get("headline") or ""
        lines = _wrap(quote, 11)
        # reveal is complete by the first third of the act, so the page is read
        # rather than caught mid-type
        reveal = clamp01((t - 0.25) / max(0.6, ctx.duration * 0.30))
        shown = max(1, int(round(reveal * len(lines))))
        qy = 268
        for line in lines[:shown]:
            m = fit_mask(line, "cjk_b", 52, qw)
            blit(c, m, qx, qy, ink, 0.95)
            qy += m.shape[0] + 18
        rule(c, qx, qy + 26, qx + 220, qy + 26, pal.primary, 1.0, 4)
        # a short standfirst under the quote so the page is not half empty
        stand = self.beat.get("standfirst") or self.beat.get("kicker") or ""
        if stand:
            text(c, str(stand), qx, qy + 56, "sans", 24, ink, 0.55, tracking=4)
        text(c, self.beat.get("folio", "- 01 -"), qx, H - 120, "display", 26, ink, 0.6)
        rule(c, W / 2, 120, W / 2, H - 120, ink, 0.18, 1)
        return c


def _wrap(s: str, width: int) -> list[str]:
    """Break a CJK/Latin string into column-width chunks."""
    return [s[i:i + width] for i in range(0, len(s), width)] if s else []


# --------------------------------------------------------------------------
# 14 GALAXY -- 46k stars in a spiral
# --------------------------------------------------------------------------
class Galaxy(Scene):
    name = "GALAXY"
    style = "galaxy"

    def __init__(self, beat, spec):
        self.beat = beat
        n = 46000
        rng = np.random.default_rng(int(spec.get("seed", 7)) + 91)
        arms = 4
        r = np.sqrt(rng.random(n)).astype(np.float32)
        arm = rng.integers(0, arms, n)
        th = arm * TAU / arms + r * 3.4 + rng.normal(0, 0.22, n) * (1.2 - r * 0.6)
        self.x = (r * np.cos(th)).astype(np.float32)
        self.y = (r * np.sin(th) * 0.55).astype(np.float32)
        self.r = r

    def render(self, ctx):
        pal = ctx.pal
        c = bg_canvas(pal)
        t = ctx.t_local
        rot = t * 0.12
        cs, sn = np.cos(rot), np.sin(rot)
        x = self.x * cs - self.y * sn
        y = self.x * sn + self.y * cs
        px = (W * 0.5 + x * H * 0.72).astype(np.int32)
        py = (H * 0.45 + y * H * 0.72).astype(np.int32)
        ok = (px >= 0) & (px < W) & (py >= 0) & (py < H)
        lay = np.zeros((H, W), np.float32)
        np.add.at(lay, (py[ok], px[ok]), (0.35 + 0.65 * (1 - self.r[ok])))
        lay = cv2.GaussianBlur(lay, (0, 0), 1.4)
        bright = cv2.GaussianBlur(lay, (0, 0), 9) * 3.0
        c += pal.ink * lay[..., None] * 0.95
        c += pal.primary * bright[..., None] * 0.55
        c += pal.accent * cv2.GaussianBlur(lay, (0, 0), 40)[..., None] * 0.55
        disc(c, W * 0.5, H * 0.45, 26 + 3 * np.sin(t * 4), (1, 1, 1), 0.95, soft=3)
        s = 44
        ang = t * 0.8
        pts = [(W * 0.5 + s * np.cos(ang + k * np.pi / 2),
                H * 0.45 + s * np.sin(ang + k * np.pi / 2)) for k in range(4)]
        stroke(c, pts, pal.ink, 3, 0.9, glow=6, closed=True)
        cap = self.beat.get("caption")
        if cap:
            a = window(t, 0.8, ctx.duration, 0.4)
            m = tracked_mask(cap, "cjk_b", 44, 5.0)
            blit(c, m, W * 0.5, H - 130, pal.ink, a * 0.9)
        return c


# --------------------------------------------------------------------------
# 15 DE STIJL -- the layout is re-cut on every beat
# --------------------------------------------------------------------------
class DeStijl(Scene):
    name = "DE STIJL"
    style = "destijl"

    def __init__(self, beat, spec):
        self.beat = beat
        rng = np.random.default_rng(int(spec.get("seed", 7)) + 101)
        self.layouts = []
        for _ in range(6):
            xs = sorted(np.concatenate([[0, W], rng.choice(np.arange(240, W - 240, 40), 3, replace=False)]))
            ys = sorted(np.concatenate([[0, H], rng.choice(np.arange(180, H - 180, 30), 2, replace=False)]))
            cells = []
            for i in range(len(xs) - 1):
                for j in range(len(ys) - 1):
                    cells.append((xs[i], ys[j], xs[i + 1] - xs[i], ys[j + 1] - ys[j]))
            self.layouts.append(cells)

    def render(self, ctx):
        pal = ctx.pal
        c = np.empty((H, W, 3), np.float32)
        c[:] = pal.paper
        t = ctx.t_local
        idx = int(t / 0.6) % len(self.layouts)
        cells = self.layouts[idx]
        rng = np.random.default_rng(idx * 7919 + 3)
        choice = rng.random(len(cells))
        fills = [pal.primary, pal.danger, pal.warm, np.array([0.05, 0.05, 0.06], np.float32)]
        for (x, y, w, h), r in zip(cells, choice):
            if r > 0.70:
                block(c, x, y, w, h, fills[int(r * 100) % 4], 0.95)
        ink = np.array([0.04, 0.04, 0.05], np.float32)
        # one thick-line mask for every cell edge: mondrian's black grid
        edges = Lines()
        for (x, y, w, h) in cells:
            edges.line(x, y, x + w, y, 10)
            edges.line(x, y, x, y + h, 10)
        edges.line(W - 6, 0, W - 6, H, 10)
        edges.line(0, H - 6, W, H - 6, 10)
        edges.draw(c, ink, 1.0)
        word = self.beat.get("caption", "")
        if word:
            text(c, word, W - 80, H - 90, "cjk_b", 40, ink, 0.9, anchor="rb")
        return c


# --------------------------------------------------------------------------
# 16 PIXELSORT
# --------------------------------------------------------------------------
class PixelSort(Scene):
    name = "PIXELSORT"
    style = "pixelsort"

    def __init__(self, beat, spec):
        self.beat = beat
        field = fbm(int(spec.get("seed", 7)) + 111, octaves=5, gh=6, gw=9)
        yy, xx = COORDS
        base = 0.5 + 0.5 * np.sin(xx * 0.004 + np.sin(yy * 0.0022) * 6.0)
        self.src = np.clip(field * 0.6 + base * 0.4, 0, 1).astype(np.float32)

    def render(self, ctx):
        pal = ctx.pal
        t = ctx.t_local
        prog = ease_in_out(clamp01(t / (ctx.duration * 0.75)))
        order = np.argsort(self.src, axis=0)
        sorted_c = np.take_along_axis(self.src, order, axis=0)
        blended = self.src * (1 - prog) + sorted_c * prog
        order2 = np.argsort(blended, axis=1)
        sorted_r = np.take_along_axis(blended, order2, axis=1)
        b2 = blended * (1 - prog * 0.55) + sorted_r * (prog * 0.55)
        # quantise into bands so the sort reads as stripes, not a smooth wash
        banded = np.floor(b2 * 14) / 14.0
        c = pal.ramp(banded) * (0.08 + 0.62 * banded[..., None])
        # the sorted streaks: brighten every row boundary
        streak = np.abs(np.diff(banded, axis=1, prepend=banded[:, :1]))
        c += pal.ink * (streak > 0.02)[..., None] * 0.35
        k = int(t * 60)
        rng = np.random.default_rng(k // 4)
        for _ in range(3):
            y0 = int(rng.uniform(0, H - 80))
            hgt = int(rng.uniform(10, 70))
            sh = int(rng.normal(0, 40))
            c[y0:y0 + hgt] = np.roll(c[y0:y0 + hgt], sh, axis=1)
        block(c, 120, H - 120, (W - 240) * prog, 6, pal.ink, 0.9)
        cap = self.beat.get("caption")
        if cap:
            text(c, cap, 120, H - 190, "mono_b", 30, pal.ink, 0.85, tracking=4)
        return c


# --------------------------------------------------------------------------
# 17 PLOTTER
# --------------------------------------------------------------------------
class Plotter(Scene):
    name = "PLOTTER"
    style = "plotter"

    def __init__(self, beat, spec):
        self.beat = beat
        rose = beat.get("rose") or {"n": 6, "d": 5}
        a, b = rose.get("n", 6), rose.get("d", 5)
        s = np.linspace(0, TAU * b, 12000, dtype=np.float32)
        r = np.cos(a / b * s)
        self.x = W * 0.5 + np.cos(s) * r * H * 0.34
        self.y = H * 0.50 + np.sin(s) * r * H * 0.34
        # a second, rotated rose fills the empty sheet like a real plotter run
        s2 = np.linspace(0, TAU * (b + 2), 9000, dtype=np.float32)
        r2 = np.cos(a / (b + 2) * s2)
        self.x2 = W * 0.5 + np.cos(s2 + 0.7) * r2 * H * 0.20
        self.y2 = H * 0.50 + np.sin(s2 + 0.7) * r2 * H * 0.20

    def render(self, ctx):
        pal = ctx.pal
        c = np.empty((H, W, 3), np.float32)
        c[:] = pal.paper
        t = ctx.t_local
        ink = np.array([0.08, 0.09, 0.12], np.float32)
        faint = np.array([0.62, 0.60, 0.56], np.float32)

        # the plotter's own sheet: frame, axes and tick marks
        frame = Lines()
        frame.line(90, 90, W - 90, 90, 2)
        frame.line(90, H - 90, W - 90, H - 90, 2)
        frame.line(90, 90, 90, H - 90, 2)
        frame.line(W - 90, 90, W - 90, H - 90, 2)
        frame.draw(c, ink, 0.55)
        ticks = Lines()
        for i in range(1, 12):
            x = 90 + (W - 180) * i / 12
            ticks.line(x, 90, x, 104, 1)
            ticks.line(x, H - 90, x, H - 104, 1)
        for i in range(1, 8):
            y = 90 + (H - 180) * i / 8
            ticks.line(90, y, 104, y, 1)
            ticks.line(W - 90, y, W - 104, y, 1)
        ticks.draw(c, ink, 0.35)

        prog = ease_in_out(clamp01(t / (ctx.duration * 0.80)))
        # the inner rose is plotted first and fades to grey
        m2 = np.zeros((H, W), np.uint8)
        p2 = np.stack([self.x2, self.y2], 1).astype(np.int32).reshape(-1, 1, 2)
        cv2.polylines(m2, [p2], False, 255, 2, cv2.LINE_AA)
        a2 = m2.astype(np.float32) / 255.0
        over(c, faint, a2 * 0.75)

        # the main rose draws itself, leaving the full path faintly visible
        n = max(2, int(len(self.x) * prog))
        ghost = np.stack([self.x, self.y], 1).astype(np.int32).reshape(-1, 1, 2)
        mg = np.zeros((H, W), np.uint8)
        cv2.polylines(mg, [ghost], False, 255, 1, cv2.LINE_AA)
        over(c, faint, mg.astype(np.float32) / 255.0 * 0.45)

        m = np.zeros((H, W), np.uint8)
        pts = ghost[:n]
        cv2.polylines(m, [pts], False, 255, 3, cv2.LINE_AA)
        a = m.astype(np.float32) / 255.0
        over(c, ink, a * 0.95)
        # the pen head, with a little bloom so it reads on paper
        if n < len(self.x):
            pen = np.zeros((H, W), np.float32)
            cv2.circle(pen, (int(self.x[n - 1]), int(self.y[n - 1])), 11, 1.0, -1,
                       cv2.LINE_AA)
            c += pal.danger * cv2.GaussianBlur(pen, (0, 0), 7)[..., None] * 0.85
            cv2.circle(c, (int(self.x[n - 1]), int(self.y[n - 1])), 9,
                       tuple(float(v) for v in pal.danger), -1, cv2.LINE_AA)

        # sheet metadata, bottom corners
        text(c, self.beat.get("kicker", "PLOT NO. 17"), 118, 78, "mono", 22, ink,
             0.7, tracking=4)
        text(c, f"{int(prog*100):03d}%", W - 210, 78, "mono", 22, ink, 0.7, tracking=3)
        cap = self.beat.get("headline") or self.beat.get("caption", "")
        if cap:
            cm = fit_mask(str(cap), "cjk_b", 40, W - 420, 4.0)
            blit(c, cm, W * 0.5 - cm.shape[1] / 2, H - 165, ink, 0.9)
        return c


# --------------------------------------------------------------------------
# 18 METABALLS
# --------------------------------------------------------------------------
class Metaballs(Scene):
    name = "METABALLS"
    style = "metaballs"

    def __init__(self, beat, spec):
        self.beat = beat
        rng = np.random.default_rng(int(spec.get("seed", 7)) + 121)
        k = 9
        self.cx = W * 0.5 + rng.normal(0, 220, k)
        self.cy = H * 0.5 + rng.normal(0, 140, k)
        self.rr = rng.uniform(90, 170, k)
        self.ph = rng.uniform(0, TAU, k)
        self.k = k

    def render(self, ctx):
        pal = ctx.pal
        c = bg_canvas(pal)
        t = ctx.t_local
        yy, xx = COORDS
        f = np.zeros((H, W), np.float32)
        for i in range(self.k):
            cx = self.cx[i] + np.sin(t * 1.1 + self.ph[i]) * 210
            cy = self.cy[i] + np.cos(t * 0.9 + self.ph[i] * 1.7) * 140
            r = self.rr[i] * (0.85 + 0.25 * np.sin(t * 1.6 + self.ph[i]))
            f += r * r / ((xx - cx) ** 2 + (yy - cy) ** 2 + 1e-3)
        iso = smoothstep(0.95, 1.05, f)
        rim = np.clip(1 - np.abs(f - 1.0) * 3.2, 0, 1)
        col = pal.ramp(np.clip((f - 0.4) / 1.4, 0, 1))
        c += col * iso[..., None] * 0.75
        c += pal.ink * rim[..., None] * 0.35
        cap = self.beat.get("caption")
        if cap:
            a = window(t, 1.0, ctx.duration, 0.4)
            m = tracked_mask(cap, "cjk_b", 44, 5.0)
            blit(c, m, W * 0.5, H - 120, pal.ink, a * 0.85)
        return c


# --------------------------------------------------------------------------
# 19 MATRIX -- code rain collapses into the payoff word
# --------------------------------------------------------------------------
class Matrix(Scene):
    name = "MATRIX"
    style = "matrix"

    # column pitch, line pitch and glyph size are deliberately decoupled: a
    # square glyph mask at a tight line pitch reads as a smear, not as rain.
    COLS = 32
    CW = 58
    LH = 50
    GLYPH = 32

    def __init__(self, beat, spec):
        self.beat = beat
        self.word = beat.get("payoff", "")
        rng = np.random.default_rng(int(spec.get("seed", 7)) + 131)
        self.head = rng.uniform(0, H, self.COLS).astype(np.float32)
        self.speed = rng.uniform(260, 720, self.COLS).astype(np.float32)
        self.chars = "0123456789ABCDEFGHJKLMNPQRSTUVWXYZ<>[]{}$%#*+=-"
        self.glyphs = {}

    def _g(self, ch):
        if ch not in self.glyphs:
            self.glyphs[ch] = mask(ch, "mono_b", self.GLYPH)[0]
        return self.glyphs[ch]

    def render(self, ctx):
        pal = ctx.pal
        c = bg_canvas(pal)
        t = ctx.t_local
        pitch = self.CW
        span = self.COLS * pitch
        x_base = (W - span) / 2
        tm = np.zeros((H, W), np.float32)
        wm = None
        if self.word:
            wm = tracked_mask(self.word, "mono_b", 200, 26.0)
            x0 = int(W * 0.5 - wm.shape[1] / 2)
            y0 = int(H * 0.5 - wm.shape[0] / 2)
            tm[y0:y0 + wm.shape[0], x0:x0 + wm.shape[1]] = wm
        converge = smoothstep(ctx.duration * 0.40, ctx.duration * 0.88, t)

        for col in range(self.COLS):
            x = int(x_base + col * pitch)
            head = (self.head[col] + self.speed[col] * t) % (H + 600) - 300
            for j in range(22):
                y = head - j * self.LH
                k = int((y + t * 400) // self.LH + col * 7)
                ch = self.chars[(k * 31 + col * 17) % len(self.chars)]
                g = self._g(ch)
                bright = max(0.0, 1.0 - j / 22) ** 1.7
                if converge > 0.02:
                    yi = int(np.clip(y + self.GLYPH * 0.5, 0, H - 1))
                    xi = int(np.clip(x + self.GLYPH * 0.5, 0, W - 1))
                    bright = bright * (1 - converge) + float(tm[yi, xi]) * converge * 2.4
                if bright <= 0.03:
                    continue
                blit(c, g, x, y, pal.ink if j == 0 else pal.accent, min(1.0, bright * 0.9))

        # the payoff word resolves out of the rain
        if wm is not None and converge > 0.25:
            a = smoothstep(0.25, 1.0, converge)
            x0 = W * 0.5 - wm.shape[1] / 2
            y0 = H * 0.5 - wm.shape[0] / 2
            blit(c, wm, x0, y0, pal.ink, a)
            c += pal.accent * 0.0
        return c


# --------------------------------------------------------------------------
# 20 END CARD -- the sign-off
# --------------------------------------------------------------------------
class EndCard(Scene):
    name = "END CARD"
    style = "endcard"

    def __init__(self, beat, spec):
        self.beat = beat

    def render(self, ctx):
        pal = ctx.pal
        c = np.empty((H, W, 3), np.float32)
        c[:] = np.array([0.015, 0.017, 0.022], np.float32)
        t = ctx.t_local
        lines = self.beat.get("lines") or []
        y = H * 0.30
        for i, (s, role, size) in enumerate(lines):
            a = ease_out(clamp01((t - 0.05 - i * 0.10) / 0.35))
            if a <= 0:
                continue
            m = fit_mask(s, role, size, W * 0.78, 4.0 if size < 40 else 2.0)
            blit(c, m, W * 0.5 - m.shape[1] / 2, y, pal.ink, a * 0.95)
            y += m.shape[0] * 0.78 + 18
        # hairline rule above the signature block
        sig_a = ease_out(clamp01((t - 0.1) / 0.4))
        rule(c, W * 0.5 - 210, H * 0.30 - 46, W * 0.5 + 210, H * 0.30 - 46,
             pal.accent, sig_a * 0.9, 3)
        return c
