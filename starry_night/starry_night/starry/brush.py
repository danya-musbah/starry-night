"""Procedural oil-paint brush strokes.

Each stroke is a small RGBA sprite with bristle streaks, dry-brush gaps,
a tapered tail and a slight ridge highlight.  Rotated variants are cached
(24 angles) so thousands of strokes can be blitted cheaply.
"""
import math
import random

import numpy as np
import pygame


def make_stroke(L, Wd, color, rng):
    xs = (np.arange(L) + 0.5) / L * 2 - 1
    ys = (np.arange(Wd) + 0.5) / Wd * 2 - 1
    X, Y = np.meshgrid(xs, ys)
    tail = (X + 1) / 2                                  # 0 head -> 1 tail
    taper = 0.62 + 0.38 * (1 - tail)
    ny = np.abs(Y) / taper
    edge = np.clip((1 - ny ** 2.4) * 2.6, 0, 1)
    cap = np.clip(1 - np.abs(X) ** 3, 0, 1) ** 0.6
    alpha = edge * cap

    rowv = rng.uniform(0.80, 1.16, (Wd, 1))             # bristle brightness
    ph = rng.uniform(0, 6.28, (Wd, 1))
    fr = rng.uniform(2.0, 7.0, (Wd, 1))
    along = 1 + 0.07 * np.sin(X * fr + ph)
    ridge = 1 + 0.12 * np.clip(-Y, 0, 1)                # paint ridge highlight
    bright = rowv * along * ridge

    gap = rng.random((Wd, 1)) < 0.22                    # dry-brush gaps
    dry = np.where(gap, np.clip(1.0 - (tail - 0.35) * 2.2, 0, 1), 1.0)
    alpha = alpha * rng.uniform(0.82, 1.0, (Wd, 1)) * dry

    col = np.array(color, np.float32)[None, None, :]
    rgb = np.clip(col * bright[..., None], 0, 255)
    arr = np.dstack([rgb, alpha * 245]).astype(np.uint8)
    surf = pygame.image.frombuffer(arr.tobytes(), (L, Wd), "RGBA").copy()
    return surf.convert_alpha()


class BrushLibrary:
    def __init__(self, n_angles=24, variants=2, seed=11):
        self.n = n_angles
        self.variants = variants
        self._base = {}
        self._rot = {}
        self._np = np.random.default_rng(seed)
        self._py = random.Random(seed)

    def _base_stroke(self, rgb, size, v):
        key = (rgb, size, v)
        s = self._base.get(key)
        if s is None:
            s = make_stroke(size[0], size[1], rgb, self._np)
            self._base[key] = s
        return s

    def get_idx(self, rgb, size, idx, v=None):
        if v is None:
            v = self._py.randrange(self.variants)
        key = (rgb, size, v, idx)
        s = self._rot.get(key)
        if s is None:
            deg = -math.degrees(idx * math.pi / self.n)
            s = pygame.transform.rotozoom(self._base_stroke(rgb, size, v), deg, 1.0)
            self._rot[key] = s
        return s

    def get(self, rgb, size, angle):
        """Stroke whose long axis follows `angle` (radians, screen coords)."""
        idx = int(round((angle % math.pi) / math.pi * self.n)) % self.n
        return self.get_idx(rgb, size, idx)
