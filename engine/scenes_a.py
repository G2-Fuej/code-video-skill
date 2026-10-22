"""scenes_a.py -- acts 1-7 of the 19-style reel.

Every act reads its copy from the beat spec, so one engine serves any topic.
"""
from __future__ import annotations

import numpy as np
import cv2

from core import (W, H, TAU, COORDS, bg_canvas, over, stroke, fill_poly, disc,
                  smoothstep, ease_out, ease_in_out, window, hash01, hash_grid,
                  noise_field, fbm, grain, vignette, clamp01, unit_coords, polar,
                  arc, Lines)
from typekit import text, mask, tracked_mask, blit, measure, rule, block, fit_mask
from stage import Scene


# --------------------------------------------------------------------------
# 01 PHYLLOTAXIS -- golden angle seed head
# --------------------------------------------------------------------------
class Phyllotaxis(Scene):
    name = "PHYLLOTAXIS"
    style = "phyllotaxis"

    def __init__(self, beat, spec):
        self.beat = beat
        self.spec = spec
        n = 2600
        i = np.arange(n)
        ang = i * 2.399963229728653
        # 0.28H radius keeps the head clear of the caption block at 0.765H
        r = np.sqrt(i / n) * 0.28
        self.px = (W * 0.5 + np.cos(ang) * r * H).astype(np.float32)
        # the head sits in the upper half so the title has clear space below it
        self.py = (H * 0.37 + np.sin(ang) * r * H).astype(np.float32)
        self.rad = (1.0 + 4.0 * np.sqrt(i / n)).astype(np.float32)
        self.seed = int(spec.get("seed", 7))

    def render(self, ctx):
        pal = ctx.pal
        c = bg_canvas(pal)
        t = ctx.t_local
        grow = ease_out(clamp01(t / 2.4))
        n = int(len(self.px) * grow)
        yy, xx = COORDS
        # seeds: one batched mask, then a bloom pass. Drawing 2.6k circles into
        # a full-frame mask per frame is the only affordable way at 60 fps.
        m = np.zeros((H, W), np.uint8)
        for k in range(n):
            cv2.circle(m, (int(self.px[k]), int(self.py[k])),
                       max(1, int(self.rad[k])), 255, -1, cv2.LINE_AA)
        a = m.astype(np.float32) / 255.0
        bloom = cv2.GaussianBlur(a, (0, 0), 9)
        c += pal.ramp(np.clip(yy / H, 0, 1)) * bloom[..., None] * 1.5
        c *= 1.0 - a[..., None] * 0.85
        c += pal.ink * a[..., None] * 0.95
        # rim light on the outer seeds
        rim = np.clip(np.hypot(xx - W * 0.5, yy - H * 0.40) / (H * 0.36) - 0.55, 0, 1)
        c += pal.accent * cv2.GaussianBlur(a * rim, (0, 0), 5)[..., None] * 1.2

        # headline sits in the space below the head
        tw = window(t, 0.55, ctx.duration, 0.35)
        if tw > 0.01:
            title = self.beat.get("headline", "")
            if title:
                s = clamp01((tw - 0.1) / 0.7)
                size = int(54 + 16 * ease_out(s))
                m2 = fit_mask(title, "display_b", size, W * 0.84, 5.0)
                ty = H * 0.765
                blit(c, m2, W * 0.5 - m2.shape[1] / 2, ty, pal.ink, ease_out(s))
                rule(c, W * 0.5 - m2.shape[1] / 2, ty + m2.shape[0] + 14,
                     W * 0.5 + m2.shape[1] / 2, ty + m2.shape[0] + 14,
                     pal.accent, tw, 3)
        kicker = self.beat.get("kicker", "")
        if kicker:
            ka = window(t, 0.3, ctx.duration, 0.3)
            km = fit_mask(kicker, "mono", 24, W * 0.62, 7.0)
            blit(c, km, W * 0.5 - km.shape[1] / 2, H * 0.905, pal.accent, ka * 0.9)
        return c


# --------------------------------------------------------------------------
# 02 TRUCHET -- quarter-arc mosaic, marching, with a missing tile
# --------------------------------------------------------------------------
class Truchet(Scene):
    name = "TRUCHET"
    style = "truchet"

    def __init__(self, beat, spec):
        self.beat = beat
        self.cell = 96
        self.rows = H // self.cell + 2
        self.cols = W // self.cell + 2
        rng = np.random.default_rng(int(spec.get("seed", 7)) + 11)
        self.flip = rng.random((self.rows, self.cols)) > 0.5

    def render(self, ctx):
        pal = ctx.pal
        c = bg_canvas(pal)
        t = ctx.t_local
        march = int(t * 1.8)
        m = np.zeros((H, W), np.uint8)
        gap_at = ctx.duration * 0.62
        gap_r, gap_c = self.rows // 2, self.cols // 2
        for r in range(self.rows):
            for cidx in range(self.cols):
                x = (cidx - 1) * self.cell
                y = (r - 1) * self.cell
                # the "removed feature": one tile is punched out at gap_at
                if (r, cidx) == (gap_r, gap_c) and t > gap_at:
                    continue
                # phase cycles so the weave visibly marches without thinning out
                phase = (r + cidx + march) % 6
                if phase >= 4:
                    continue
                f = self.flip[r, cidx]
                if f:
                    arc(m, x, y, self.cell // 2, 0, 90, 255, 4)
                    arc(m, x + self.cell, y + self.cell, self.cell // 2, 0, 90, 255, 4)
                else:
                    arc(m, x + self.cell, y, self.cell // 2, 90, 180, 255, 4)
                    arc(m, x, y + self.cell, self.cell // 2, 270, 360, 255, 4)
        a = m.astype(np.float32) / 255.0
        mixv = float(smoothstep(0, max(gap_at, 0.1) + 0.8, t))
        col = pal.primary * (1 - mixv) + pal.accent * mixv
        c = c * (1 - a[..., None]) + col * a[..., None]
        cap = self.beat.get("caption")
        if cap:
            ca = window(t, 0.5, ctx.duration, 0.4)
            mm = fit_mask(cap, "mono_b", 30, W * 0.8, 5.0)
            blit(c, mm, W * 0.5 - mm.shape[1] / 2, H - 140, pal.ink, ca * 0.85)
        return c


# --------------------------------------------------------------------------
# 03 FLOW FIELD -- particles following a vector field into a wall
# --------------------------------------------------------------------------
class FlowField(Scene):
    name = "FLOW FIELD"
    style = "flow"

    def __init__(self, beat, spec):
        self.beat = beat
        self.n = 7000
        rng = np.random.default_rng(int(spec.get("seed", 7)) + 23)
        self.pos = np.stack([rng.uniform(0, W, self.n), rng.uniform(0, H, self.n)], 1).astype(np.float32)
        self.life = rng.uniform(0, 6.0, self.n).astype(np.float32)
        self.hue = rng.uniform(0, 1, self.n).astype(np.float32)
        self.field = fbm(101, octaves=3, gh=4, gw=6)
        # gradients are sampled per particle, not per pixel
        self.fx = cv2.Sobel(self.field, cv2.CV_32F, 1, 0, ksize=5)
        self.fy = cv2.Sobel(self.field, cv2.CV_32F, 0, 1, ksize=5)
        self.wall_x = W * 0.72
        self.cache_t = -1.0

    def _advance(self, dt):
        """Move every particle along the local vector field."""
        xi = np.clip(self.pos[:, 0].astype(np.int32), 0, W - 1)
        yi = np.clip(self.pos[:, 1].astype(np.int32), 0, H - 1)
        vx = self.fx[yi, xi]
        vy = self.fy[yi, xi]
        n = np.hypot(vx, vy) + 1e-6
        step = 260.0 * dt
        self.pos[:, 0] += (vx / n) * step
        self.pos[:, 1] += (vy / n) * step
        self.life += dt
        dead = (self.life > 6.0) | (self.pos[:, 0] > W + 40) | (self.pos[:, 1] > H + 40) | (self.pos[:, 1] < -40)
        idx = np.nonzero(dead)[0]
        if len(idx):
            rng = np.random.default_rng(int(self.life.sum() * 1000) + 5)
            self.pos[idx, 0] = rng.uniform(0, W * 0.35, len(idx))
            self.pos[idx, 1] = rng.uniform(0, H, len(idx))
            self.life[idx] = 0.0

    def render(self, ctx):
        pal = ctx.pal
        c = bg_canvas(pal)
        t = ctx.t_local
        dt = 1.0 / 60.0
        if abs(t - self.cache_t) > 1e-6:
            steps = max(1, int(round((t - self.cache_t) / dt))) if self.cache_t >= 0 else 0
            for _ in range(min(steps, 6)):
                self._advance(dt)
            self.cache_t = t
        wall = smoothstep(ctx.duration * 0.35, ctx.duration * 0.55, t)
        alive = self.pos[:, 0] < self.wall_x + 30
        px = np.clip(self.pos[alive, 0], 0, W - 1).astype(np.int32)
        py = np.clip(self.pos[alive, 1], 0, H - 1).astype(np.int32)
        # draw each particle as a short streak against its motion direction --
        # single pixels vanish once the frame is scaled down
        lay = np.zeros((H, W), np.float32)
        np.add.at(lay, (py, px), 1.0)
        core = cv2.GaussianBlur(lay, (0, 0), 1.2)
        halo = cv2.GaussianBlur(lay, (0, 0), 5.0)
        col = pal.ramp(0.35)
        c += col * core[..., None] * 3.4
        c += pal.accent * halo[..., None] * 2.2
        # a faint ambient wash so the field reads even where particles are thin
        c += pal.primary * 0.05
        # the wall the flow cannot cross
        wx = int(self.wall_x + wall * W * 0.16)
        wallmask = np.zeros((H, W), np.float32)
        wallmask[:, wx:wx + 4] = wall
        c += pal.danger * wallmask[..., None] * 1.2
        c += pal.danger * cv2.GaussianBlur(wallmask, (0, 0), 22)[..., None] * 0.7
        cap = self.beat.get("caption")
        if cap:
            a = window(t, 0.5, ctx.duration, 0.4)
            m2 = fit_mask(cap, "mono_b", 32, W * 0.8, 5.0)
            blit(c, m2, W * 0.5 - m2.shape[1] / 2, H - 150, pal.ink, a * 0.9)
        return c


# --------------------------------------------------------------------------
# 04 VORONOI -- glass shards shatter then reassemble
# --------------------------------------------------------------------------
class Voronoi(Scene):
    name = "VORONOI"
    style = "voronoi"

    def __init__(self, beat, spec):
        self.beat = beat
        rng = np.random.default_rng(int(spec.get("seed", 7)) + 31)
        self.sites = np.stack([rng.uniform(0, W, 26), rng.uniform(0, H, 26)], 1).astype(np.float32)

    def render(self, ctx):
        pal = ctx.pal
        t = ctx.t_local
        yy, xx = COORDS
        d = np.full((H, W), 1e9, np.float32)
        labels = np.zeros((H, W), np.int32)
        for i, (sx, sy) in enumerate(self.sites):
            dd = (xx - sx) ** 2 + (yy - sy) ** 2
            upd = dd < d
            d = np.where(upd, dd, d)
            labels = np.where(upd, i, labels)
        # shatter: push each cell away from its site, then spring back
        phase = np.clip((t - 0.4) / (ctx.duration * 0.45), 0, 1)
        push = np.sin(phase * np.pi) * 90.0
        sx = self.sites[labels, 0]
        sy = self.sites[labels, 1]
        ang = np.arctan2(yy - sy, xx - sx)
        px = xx - np.cos(ang) * push
        py = yy - np.sin(ang) * push
        dd = (px - sx) ** 2 + (py - sy) ** 2
        edge = cv2.distanceTransform((dd < np.percentile(dd, 6)).astype(np.uint8) * 255,
                                     cv2.DIST_L2, 3)
        edge = cv2.GaussianBlur(edge, (0, 0), 1.6) / 255.0
        # cell ids are randomly shuffled so neighbouring shards differ in hue,
        # then the hue is pushed toward the blue/teal ramp roles only
        cellid = labels.astype(np.float32) / max(1, len(self.sites) - 1)
        base = pal.ramp(cellid)
        c = base * (0.10 + 0.16 * (1 - edge[..., None]))
        c += pal.ink * np.clip(edge, 0, 1)[..., None] * 0.75
        c += pal.accent * np.clip(1 - edge * 3.2, 0, 1)[..., None] * 0.22
        # a bright rim on the reassembly beat
        settle = smoothstep(ctx.duration * 0.55, ctx.duration * 0.95, t)
        c += pal.ink * (edge * settle)[..., None] * 0.5
        cap = self.beat.get("caption")
        if cap:
            a = window(t, 0.5, ctx.duration, 0.4)
            m2 = fit_mask(cap, "mono_b", 32, W * 0.8, 5.0)
            blit(c, m2, W * 0.5 - m2.shape[1] / 2, H - 140, pal.ink, a * 0.9)
        return c


# --------------------------------------------------------------------------
# 05 ASCII -- torus knot typed out in a terminal
# --------------------------------------------------------------------------
class AsciiTorus(Scene):
    name = "ASCII"
    style = "ascii"

    def __init__(self, beat, spec):
        self.beat = beat
        self.cols = 96
        self.rows = 34
        self.chars = " .:-=+*#%@"
        self.lines = (beat.get("terminal", "") or "").split("\n")
        rng = np.random.default_rng(int(spec.get("seed", 7)) + 41)
        self.noise = rng.random((self.rows, self.cols)).astype(np.float32)
        self.cache = {}
        # glyph size follows the cell, so the terminal fills the frame at any
        # resolution instead of shrinking into a dark postage stamp
        self.cw = W / self.cols
        self.chh = H / self.rows
        self.size = max(10, int(min(self.cw, self.chh) * 1.15))

    def _glyph(self, ch):
        key = (ch, self.size)
        if key not in self.cache:
            self.cache[key] = mask(ch, "mono_b", self.size)[0]
        return self.cache[key]

    def render(self, ctx):
        pal = ctx.pal
        c = bg_canvas(pal, 0.03)
        t = ctx.t_local
        # a torus knot in polar space, then quantised onto a character grid
        u = (np.arange(self.cols)[None, :] - self.cols / 2) / (self.cols * 0.42)
        v = (np.arange(self.rows)[:, None] - self.rows / 2) / (self.rows * 0.42)
        uu, vv = np.meshgrid(u, v)
        r = np.hypot(uu, vv)
        th = np.arctan2(vv, uu)
        p, q = 2, 3
        knot = (np.sin(p * th + 3.0 * r) + np.cos(q * th - 2.0 * r)) * 0.5
        shade = np.clip(0.5 + 0.5 * knot, 0, 1) * np.clip(1.25 - r * 0.85, 0, 1)
        # boost the mid-tones: a terminal reads as lit glyphs, not darkness
        shade = np.clip(shade * 1.7, 0, 1)
        reveal = ease_in_out(clamp01((t - 0.3) / (ctx.duration * 0.6)))

        lines = self.lines or [self.beat.get("headline", "")]
        cw, chh = self.cw, self.chh
        for row in range(self.rows):
            line = lines[row % len(lines)]
            if not line:
                continue
            for col in range(self.cols):
                if (row * self.cols + col) / (self.rows * self.cols) > reveal:
                    continue
                # only cells inside the knot carry text -- that is what makes
                # the shape read instead of turning into a wall of characters
                sh = float(shade[row, col])
                if sh < 0.16:
                    continue
                idx = (row * 7 + col * 3) % len(line)
                ch = line[idx]
                if ch == " ":
                    continue
                g = self._glyph(ch)
                x = col * cw + (cw - g.shape[1]) * 0.5
                y = row * chh + (chh - g.shape[0]) * 0.5
                blit(c, g, x, y, pal.ink if sh > 0.62 else pal.accent,
                     0.18 + 0.82 * sh)
        # the terminal's own frame: a thin border and a cursor
        border = Lines()
        border.line(28, 26, W - 28, 26, 1)
        border.line(28, H - 26, W - 28, H - 26, 1)
        border.draw(c, pal.accent, 0.35)
        cur_on = int(t * 2) % 2 == 0
        if cur_on:
            block(c, 34 + int((t * 40) % 180), H - 58, 14, 22, pal.accent, 0.85)
        return c


# --------------------------------------------------------------------------
# 06 HALFTONE -- three colour plates, deliberately misregistered
# --------------------------------------------------------------------------
class Halftone(Scene):
    name = "HALFTONE"
    style = "halftone"

    CELL = 11

    def __init__(self, beat, spec):
        self.beat = beat
        self.plates = beat.get("plates") or ["A", "B", "C"]
        # Precompute one halftone plate per caption. The artwork is static, so
        # the dot coverage is built once; only the registration offset animates.
        self.plates_masks = []
        for i, title in enumerate(self.plates[:3]):
            self.plates_masks.append(self._build_plate(title, i))

    def _build_plate(self, title: str, index: int) -> np.ndarray:
        """Turn a caption into a dot grid: text -> coverage -> dots."""
        cell = self.CELL
        n = len(self.plates)
        band_h = H / max(3, n)
        # render the caption large inside its band
        m = fit_mask(str(title), "cjk_b" if _has_cjk(str(title)) else "display_b",
                     130, W * 0.80, 6.0)
        gm = np.zeros((H, W), np.float32)
        y0 = int(band_h * (index + 0.5) - m.shape[0] / 2)
        x0 = int(W * 0.5 - m.shape[1] / 2)
        ys, xs = np.nonzero(m > 0.01)
        ys = ys + y0
        xs = xs + x0
        ok = (ys >= 0) & (ys < H) & (xs >= 0) & (xs < W)
        gm[ys[ok], xs[ok]] = m[ys[ok] - y0, xs[ok] - x0]

        # coverage per cell, then a dot whose radius encodes it
        gh, gw = H // cell, W // cell
        cropped = gm[:gh * cell, :gw * cell]
        cov = cropped.reshape(gh, cell, gw, cell).mean(axis=(1, 3))
        plate = np.zeros((H, W), np.float32)
        for gy in range(gh):
            for gx in range(gw):
                cvg = float(cov[gy, gx])
                if cvg < 0.04:
                    continue
                r = cell * 0.62 * np.sqrt(cvg)
                cv2.circle(plate, (int(gx * cell + cell / 2), int(gy * cell + cell / 2)),
                           max(1, int(round(r))), cvg, -1, cv2.LINE_AA)
        return plate

    def render(self, ctx):
        pal = ctx.pal
        c = bg_canvas(pal, 0.02)
        t = ctx.t_local
        inks = [pal.primary, pal.accent, pal.danger]
        # deliberate misregistration: each plate is a few px off and drifts
        base = [(-7, -5), (8, 6), (0, 0)]
        for i, plate in enumerate(self.plates_masks):
            enter = smoothstep(0.35 + i * 0.42, 0.9 + i * 0.42, t)
            if enter <= 0.01:
                continue
            dx = base[i % len(base)][0] + int(np.sin(t * 1.7 + i) * 9)
            dy = base[i % len(base)][1] + int(np.cos(t * 1.3 + i) * 6)
            shifted = np.roll(np.roll(plate, dy, axis=0), dx, axis=1)
            # multiply-blend so overlapping inks darken like real overprint
            c += inks[i % 3] * (shifted * enter)[..., None] * 0.85
        return c


def _has_cjk(s: str) -> bool:
    return any("\u4e00" <= ch <= "\u9fff" for ch in s)


# --------------------------------------------------------------------------
# 07 SWISS GRID -- typographic grid that rewrites itself on the beat
# --------------------------------------------------------------------------
class SwissGrid(Scene):
    name = "SWISS GRID"
    style = "swiss"

    def __init__(self, beat, spec):
        self.beat = beat
        self.rows = beat.get("rows", ["Forge", "Fabric", "NeoForge", "OptiFine", "整合包"])

    def render(self, ctx):
        pal = ctx.pal
        c = bg_canvas(pal, 0.04)
        t = ctx.t_local
        step = 0.62
        idx = int(t / step) % len(self.rows)
        local = (t % step) / step

        grid = Lines()
        for i in range(1, 6):
            grid.line(W * i / 6, 0, W * i / 6, H, 1)
        for i in range(1, 4):
            grid.line(0, H * i / 4, W, H * i / 4, 1)
        grid.draw(c, pal.sub, 0.10)
        frame_lines = Lines()
        frame_lines.line(120, 180, 120, H - 180, 4)
        frame_lines.line(120, 180, W - 120, 180, 4)
        frame_lines.draw(c, pal.primary, 0.85)

        # headline crossfades between the grid rows, always fitted to the column
        cur = self.rows[idx]
        nxt = self.rows[(idx + 1) % len(self.rows)]
        y = H * 0.46
        max_w = W - 260
        if local < 0.62:
            m = fit_mask(cur, "swiss", 108, max_w, 6.0)
            blit(c, m, 120, y, pal.ink, ease_out(local * 3))
            rule(c, 120, y + m.shape[0] + 10, 120 + m.shape[1], y + m.shape[0] + 10,
                 pal.accent, 0.9, 5)
        else:
            m = fit_mask(nxt, "swiss", 108, max_w, 6.0)
            blit(c, m, 120, y, pal.ink, ease_out((local - 0.62) * 3))
            rule(c, 120, y + m.shape[0] + 10, 120 + m.shape[1], y + m.shape[0] + 10,
                 pal.accent, 0.9, 5)

        # corner meta, kept inside the margin
        text(c, self.beat.get("kicker", "COMPONENT"), 120, 118, "mono", 26,
             pal.accent, 0.9, tracking=5)
        text(c, f"{idx + 1:02d}/{len(self.rows):02d}", W - 260, H - 150, "mono", 30,
             pal.sub, 0.9, tracking=3)
        return c