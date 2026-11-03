"""The dark cypress — painted as flame-like strokes, swayed per strip."""
import math

import numpy as np
import pygame

from .config import W, H
from .noise import fbm2d
from .paint import paint_poly, ramp_pick
from .palette import make_ramp
from .post import apply_factor

CYP = make_ramp([(5, 10, 12), (8, 20, 18), (14, 36, 28), (26, 58, 40),
                 (48, 82, 52), (82, 104, 62), (112, 110, 60)], 14)
CW = 300
X0 = 8             # sprite x position on screen
STRIP = 4


class Cypress:
    def __init__(self, brush, rng):
        surf = pygame.Surface((CW, H), pygame.SRCALPHA)
        noise = fbm2d(CW, H, rng, scale=34, octaves=3)
        ts = np.linspace(0, 1, 300)
        ys = H + 6 - ts * (H - 6 - 14)
        axis = 150 + 20 * np.sin(ts * 4.4 + 0.7) + 24 * ts + 34 * ts ** 3
        p = (1 - ts) ** 0.85 * (0.72 + 0.28 * np.sin(np.pi * np.clip(ts * 2.4, 0, 1) ** 0.9))
        p *= 1 + 0.20 * np.sin(ts * 24 + 1.3) * (1 - ts * 0.5) + 0.10 * np.sin(ts * 51 + 0.4)
        half = 92 * p
        fl = (ts * 9.0 + 0.15) % 1.0                     # flame-lick sawtooth (left edge)
        fr = (ts * 8.0 + 0.55) % 1.0                     # (right edge, other phase)
        left = axis - half * (1 + 0.17 * (fl - 0.5) * (1 - ts * 0.4) + 0.04 * np.sin(ts * 71))
        right = axis + half * (1 + 0.17 * (fr - 0.5) * (1 - ts * 0.4) + 0.04 * np.sin(ts * 63 + 2))
        pts = list(zip(left.tolist(), ys.tolist())) + list(zip(right[::-1].tolist(), ys[::-1].tolist()))

        yrow = np.arange(H, dtype=np.float32)
        ax_y = np.interp(yrow, ys[::-1], axis[::-1])
        hf_y = np.interp(yrow, ys[::-1], half[::-1]) + 1

        def nf(x, y):
            return noise[np.clip(y.astype(np.int32), 0, H - 1), np.clip(x.astype(np.int32), 0, CW - 1)]

        def col(xs, ys_):
            yi = np.clip(ys_.astype(np.int32), 0, H - 1)
            u = (xs - ax_y[yi]) / hf_y[yi]
            s = 0.10 + 0.50 * nf(xs, ys_) + 0.12 * u + rng.normal(0, 0.07, len(xs))
            s = np.where(rng.random(len(xs)) < 0.11, s + 0.38, s)
            return ramp_pick(CYP, np.clip(s, 0, 1), rng, 0.4)

        def ang(xs, ys_):
            yi = np.clip(ys_.astype(np.int32), 0, H - 1)
            u = (xs - ax_y[yi]) / hf_y[yi]
            return -math.pi / 2 + 0.45 * u + 0.5 * np.sin(ys_ * 0.03 + u * 3.0 + xs * 0.01)

        paint_poly(surf, pts, brush, rng, ((12, 28, 24), (5, 12, 14)), [
            ((72, 14), 1 / 220, col, ang, 0.12),
            ((40, 9), 1 / 48, col, ang, 0.18),
            ((15, 5), 1 / 19, col, ang, 0.3),
        ])
        apply_factor(surf, x0=X0)
        self.strips = [(y, surf.subsurface((0, y, CW, min(STRIP, H - y))).copy())
                       for y in range(0, H, STRIP)]

    def draw(self, dst, t):
        for y, strip in self.strips:
            h = 1 - y / H                       # 0 at the ground, 1 at the tip
            amp = 7.0 * h ** 1.6 + 0.6 * h
            dx = amp * (math.sin(0.85 * t + 1.9 * h) + 0.45 * math.sin(1.7 * t + 5.0 * h + 1.0))
            dst.blit(strip, (X0 + int(round(dx)), y))
