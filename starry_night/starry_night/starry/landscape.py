"""Static painted landscape: mountains, hills, village, church, field.

Everything is painted with brush strokes into one RGBA layer.  The layer is
then split into an alpha strip (ridges) and an opaque bottom (cheap blit).
Windows are recorded so they can be animated every frame.
"""
import math

import numpy as np
import pygame

from .config import W, H
from .noise import fbm1d, fbm2d
from .paint import paint_poly, ramp_pick, ellipse_poly
from .palette import make_ramp
from .post import apply_factor

MOUNT = make_ramp([(16, 30, 88), (28, 50, 122), (46, 76, 156), (76, 108, 186), (114, 146, 206)], 12)
HILL = make_ramp([(10, 24, 60), (16, 38, 84), (26, 60, 108), (44, 92, 130), (76, 128, 150)], 12)
VILL = make_ramp([(10, 26, 46), (16, 40, 64), (28, 64, 80), (52, 92, 86), (92, 120, 90)], 12)
FIELD = make_ramp([(8, 18, 26), (14, 32, 38), (26, 52, 42), (52, 76, 48), (94, 98, 52), (130, 112, 60)], 14)
TREE = make_ramp([(8, 22, 18), (14, 38, 26), (26, 62, 38), (54, 92, 50), (96, 120, 60)], 10)
WALLS = [
    make_ramp([(40, 50, 78), (70, 84, 112), (104, 118, 140), (140, 150, 164), (176, 176, 172)], 8),
    make_ramp([(50, 40, 38), (88, 70, 52), (124, 100, 62), (156, 128, 72), (190, 158, 90)], 8),
    make_ramp([(60, 64, 80), (96, 100, 116), (128, 132, 142), (158, 160, 160), (190, 188, 176)], 8),
]
ROOFS = [
    make_ramp([(10, 16, 40), (18, 28, 64), (30, 44, 92), (54, 72, 124)], 8),
    make_ramp([(40, 16, 20), (70, 28, 28), (102, 42, 34), (132, 62, 40)], 8),
    make_ramp([(12, 30, 44), (20, 50, 64), (34, 76, 84), (60, 104, 100)], 8),
]


class Land:
    def __init__(self, brush, rng):
        self.brush, self.rng = brush, rng
        self.surf = pygame.Surface((W, H), pygame.SRCALPHA)
        self.windows = []
        self.noise = fbm2d(W, H, rng, scale=60, octaves=3)
        self.noise_big = fbm2d(W, H, rng, scale=210, octaves=2)
        xs = np.arange(W)
        self.xs = xs
        self._mountains()
        self._hills()
        self._village_hill()
        self._village()
        self._foreground()
        apply_factor(self.surf)
        self._split()

    # ---------------------------------------------------------------- utils
    def nf(self, x, y):
        return self.noise[np.clip(y.astype(np.int32), 0, H - 1),
                          np.clip(x.astype(np.int32), 0, W - 1)]

    def _ridge_layer(self, ridge, ramp, grad, specs, light, depth, wave, bottom=None, patch=0.0, rj=0.45):
        rng = self.rng
        bottom = H if bottom is None else min(H, int(bottom))
        pts = [(float(x), float(ridge[x])) for x in range(0, W, 5)]
        pts += [(W, float(ridge[-1])), (W, bottom), (0, bottom)]
        slope = np.gradient(np.convolve(ridge, np.ones(9) / 9, mode="same"))

        def color_fn(xs, ys):
            r = ridge[np.clip(xs.astype(np.int32), 0, W - 1)]
            d = np.clip((ys - r) / depth, 0, 4)
            s = light * np.exp(-d * 1.2) + 0.30 * self.nf(xs, ys) + rng.normal(0, 0.05, len(xs))
            if patch:
                s = s + patch * (self.noise_big[np.clip(ys.astype(np.int32), 0, H - 1), np.clip(xs.astype(np.int32), 0, W - 1)] - 0.45)
            return ramp_pick(ramp, np.clip(s, 0, 1), rng, rj)

        def angle_fn(xs, ys):
            sl = slope[np.clip(xs.astype(np.int32), 0, W - 1)]
            return np.arctan2(sl, 1.0) * 1.3 + wave * np.sin(xs * 0.025 + ys * 0.045)

        strokes = [(sz, dn, color_fn, angle_fn, jt) for sz, dn, jt in specs]
        paint_poly(self.surf, pts, self.brush, rng, grad, strokes)

    # ------------------------------------------------------------- layers
    def _mountains(self):
        n = fbm1d(W, self.rng, scale=230, octaves=4)
        self.far = 470 - 95 * (n - 0.25).clip(0, 1) ** 1.1
        self._ridge_layer(self.far, MOUNT, ((52, 76, 150), (24, 40, 104)),
                          [((40, 11), 1 / 260, 0.16), ((22, 6), 1 / 70, 0.28), ((12, 4), 1 / 36, 0.35)],
                          light=0.72, depth=90, wave=0.35, bottom=640, patch=0.25, rj=0.6)

    def _hills(self):
        n = fbm1d(W, self.rng, scale=190, octaves=4)
        self.mid = 538 - 52 * n
        self._ridge_layer(self.mid, HILL, ((34, 74, 120), (12, 28, 66)),
                          [((40, 11), 1 / 230, 0.18), ((22, 6), 1 / 60, 0.3), ((12, 4), 1 / 34, 0.38)],
                          light=0.8, depth=70, wave=0.4, bottom=700, patch=0.35, rj=0.8)

    def _village_hill(self):
        n = fbm1d(W, self.rng, scale=260, octaves=3)
        self.vy = 600 + 17 * np.sin(self.xs / W * 2 * math.pi * 0.9 + 0.6) + (n - 0.5) * 34
        self._ridge_layer(self.vy, VILL, ((22, 54, 76), (8, 22, 38)),
                          [((36, 10), 1 / 200, 0.2), ((20, 6), 1 / 55, 0.3), ((11, 4), 1 / 30, 0.38)],
                          light=0.62, depth=60, wave=0.45, patch=0.95, rj=1.0)

    def _foreground(self):
        rng = self.rng
        n = fbm1d(W, rng, scale=200, octaves=3)
        fy = 690 + 15 * np.sin(self.xs / W * 2 * math.pi * 1.3 + 2.0) + (n - 0.5) * 24
        self._ridge_layer(fy, FIELD, ((22, 44, 40), (6, 14, 20)),
                          [((38, 10), 1 / 220, 0.18), ((20, 6), 1 / 50, 0.3), ((11, 4), 1 / 26, 0.4)],
                          light=0.50, depth=70, wave=0.5, patch=1.1, rj=1.1)

    # ------------------------------------------------------------ village
    def _poly(self, pts, grad, strokes):
        paint_poly(self.surf, pts, self.brush, self.rng, grad, strokes)

    def _window(self, x, y, w, h):
        pygame.draw.rect(self.surf, (22, 26, 48), (x, y, w, h))
        self.windows.append(dict(
            x=x, y=y, w=w, h=h,
            f=self.rng.uniform(0.25, 0.7), ph=self.rng.uniform(0, 6.28),
            on=self.rng.random() < 0.88))

    def _house(self, cx, base, w, h, roof_h):
        rng = self.rng
        wall = WALLS[rng.integers(len(WALLS))]
        roof = ROOFS[rng.integers(len(ROOFS))]
        x0, x1 = cx - w / 2, cx + w / 2
        top = base - h
        lit = rng.uniform(0.10, 0.36)

        def wcol(xs, ys):
            s = lit + 0.35 * (xs - x0) / w * 0.0 + 0.25 * self.nf(xs, ys) + rng.normal(0, 0.06, len(xs))
            return ramp_pick(wall, np.clip(s, 0, 1), rng, 0.4)
        self._poly([(x0, top), (x1, top), (x1, base), (x0, base)], (wall[2], wall[0]),
                   [((13, 4), 1 / 9, wcol, lambda x, y: np.zeros(len(x)), 0.14),
                    ((7, 3), 1 / 14, wcol, lambda x, y: np.full(len(x), 1.5708), 0.2)])

        def rcol(xs, ys):
            return ramp_pick(roof, np.clip(0.2 + 0.7 * self.nf(xs, ys) + rng.normal(0, 0.1, len(xs)), 0, 1), rng, 0.4)
        left = rng.random() < 0.5
        apex = (cx + rng.uniform(-w * 0.2, w * 0.2), top - roof_h)
        pts = [(x0 - 5, top + 1), apex, (x1 + 5, top + 1)]
        slope_a = math.atan2(roof_h, w / 2)
        self._poly(pts, (roof[2], roof[0]),
                   [((13, 4), 1 / 9, rcol,
                     lambda x, y: np.where(x < apex[0], -slope_a, slope_a), 0.18)])

        nwin = int(rng.integers(1, 4))
        ww, wh = 6, 8
        gap = w / (nwin + 1)
        for i in range(nwin):
            self._window(int(x0 + gap * (i + 1) - ww / 2), int(top + h * 0.25), ww, wh)
        pygame.draw.rect(self.surf, (18, 20, 34), (int(cx - 3), int(base - 14), 7, 14))

    def _tree(self, cx, base, rx, ry):
        rng = self.rng

        def col(xs, ys):
            s = 0.15 + 0.55 * self.nf(xs, ys) + rng.normal(0, 0.1, len(xs))
            return ramp_pick(TREE, np.clip(s, 0, 1), rng, 0.4)
        self._poly(ellipse_poly(cx, base - ry, rx, ry, rng, 22, 0.14), (TREE[3], TREE[0]),
                   [((14, 5), 1 / 18, col, lambda x, y: -0.9 + 0.7 * np.sin(x * 0.2), 0.4)])

    def _church(self, cx, base):
        rng = self.rng
        tw, th = 30, 92
        # nave
        nave = [(cx - 78, base - 44), (cx - 14, base - 44), (cx - 14, base), (cx - 78, base)]

        def ncol(xs, ys):
            return ramp_pick(WALLS[2], np.clip(0.16 + 0.3 * self.nf(xs, ys) + rng.normal(0, 0.06, len(xs)), 0, 1), rng, 0.4)
        self._poly(nave, (WALLS[2][3], WALLS[2][1]), [((15, 5), 1 / 22, ncol, lambda x, y: np.zeros(len(x)), 0.12)])
        self._poly([(cx - 82, base - 43), (cx - 46, base - 72), (cx - 10, base - 43)],
                   (ROOFS[0][2], ROOFS[0][0]),
                   [((14, 5), 1 / 16, lambda xs, ys: ramp_pick(ROOFS[0], np.clip(0.2 + 0.6 * self.nf(xs, ys), 0, 1), rng, 0.4),
                     lambda x, y: np.where(x < cx - 46, -0.68, 0.68), 0.15)])
        # tower
        tower = [(cx - tw / 2, base - th), (cx + tw / 2, base - th), (cx + tw / 2, base), (cx - tw / 2, base)]

        def tcol(xs, ys):
            return ramp_pick(WALLS[0], np.clip(0.26 + 0.3 * self.nf(xs, ys) + rng.normal(0, 0.06, len(xs)), 0, 1), rng, 0.4)
        self._poly(tower, (WALLS[0][4], WALLS[0][2]), [((15, 5), 1 / 20, tcol, lambda x, y: np.zeros(len(x)), 0.1)])
        # spire
        apex = (cx, base - th - 128)
        spire = [(cx - tw / 2 - 3, base - th + 2), apex, (cx + tw / 2 + 3, base - th + 2)]

        def scol(xs, ys):
            s = 0.18 + 0.5 * np.clip((xs - cx) / 30 + 0.3, 0, 1) * self.nf(xs, ys) + rng.normal(0, 0.06, len(xs))
            return ramp_pick(ROOFS[0], np.clip(s, 0, 1), rng, 0.4)
        sa = math.atan2(128, tw / 2 + 3)
        self._poly(spire, (ROOFS[0][3], ROOFS[0][0]),
                   [((16, 5), 1 / 16, scol, lambda x, y: np.where(x < cx, -sa, sa) * 1.0, 0.1)])
        self._window(int(cx - 3), int(base - th + 14), 7, 12)
        self._window(int(cx - 3), int(base - th + 40), 7, 12)
        for k in range(2):
            self._window(int(cx - 64 + k * 30), int(base - 32), 8, 14)
        pygame.draw.rect(self.surf, (18, 20, 34), (int(cx - 4), int(base - 18), 9, 18))

    def _village(self):
        rng = self.rng
        church_x = 800
        x = 330
        spots = []
        while x < 1160:
            w = rng.uniform(36, 66)
            if abs(x - church_x) > 105:
                spots.append((x, w))
            x += w + rng.uniform(16, 38)
        for cx, w in spots:
            base = float(self.vy[int(min(W - 1, cx))]) + 12
            self._tree(cx + rng.uniform(-40, 40), base + 4, rng.uniform(14, 24), rng.uniform(20, 34))
        for cx, w in spots:
            base = float(self.vy[int(min(W - 1, cx))]) + 14 + rng.uniform(-2, 8)
            self._house(cx, base, w, rng.uniform(26, 42), rng.uniform(14, 24))
        self._church(church_x, float(self.vy[church_x]) + 12)
        for tx in (545, 1010, 1130):
            self._tree(tx, float(self.vy[tx]) + 22, 20, 36)

    # ------------------------------------------------------------- split
    def _split(self):
        a = pygame.surfarray.array_alpha(self.surf)          # (w, h)
        any_row = a.max(axis=0) > 0
        full_row = a.min(axis=0) == 255
        first = int(np.argmax(any_row))
        notfull = np.where(~full_row)[0]
        r0 = int(notfull.max()) + 1 if len(notfull) else 0
        self.top_y = first
        self.sky_h = r0
        self.top = self.surf.subsurface((0, first, W, r0 - first)).copy().convert_alpha()
        self.bottom = self.surf.subsurface((0, r0, W, H - r0)).copy().convert()

    def draw(self, dst):
        dst.blit(self.top, (0, self.top_y))
        dst.blit(self.bottom, (0, self.sky_h))
