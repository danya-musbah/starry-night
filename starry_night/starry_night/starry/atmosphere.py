"""Night mist, animated windows and the bloom post-effect."""
import math

import numpy as np
import pygame

from .config import W, H
from .paint import glow_sprite, surf_from_rgba


def make_mist_sprite(w, h, color, peak):
    Y, X = np.mgrid[0:h, 0:w].astype(np.float32)
    a = np.exp(-((((X - w / 2) / (w / 2)) ** 2) * 2.2 + (((Y - h / 2) / (h / 2)) ** 2) * 3.0)) * peak
    arr = np.zeros((h, w, 4), np.uint8)
    arr[..., 0], arr[..., 1], arr[..., 2] = color
    arr[..., 3] = a.astype(np.uint8)
    return surf_from_rgba(arr)


class Mist:
    def __init__(self, rng):
        self.layers = []
        for ycenter, n, peak, speed, scale in ((655, 6, 46, 7.0, 1.0), (770, 5, 34, 11.0, 1.2)):
            items = []
            for i in range(n):
                w = int(rng.uniform(420, 640) * scale)
                h = int(rng.uniform(70, 120) * scale)
                col = (70 + int(rng.integers(0, 25)), 104 + int(rng.integers(0, 24)), 150 + int(rng.integers(0, 25)))
                items.append(dict(spr=make_mist_sprite(w, h, col, peak),
                                  x0=rng.uniform(0, W + w), y=ycenter + rng.uniform(-35, 35) - h / 2,
                                  v=speed * rng.uniform(0.6, 1.4), bob=rng.uniform(0, 6.28), w=w))
            self.layers.append(items)

    def draw(self, dst, t, layer):
        for m in self.layers[layer]:
            span = W + m["w"]
            x = (m["x0"] + m["v"] * t) % span - m["w"]
            y = m["y"] + 5 * math.sin(0.3 * t + m["bob"])
            dst.blit(m["spr"], (int(x), int(y)))


class Windows:
    def __init__(self, windows):
        self.w = windows
        base = glow_sprite(20, (255, 170, 60), 1.8)
        self.levels = []
        for i in range(12):
            g = base.copy()
            v = int(255 * (0.20 + 0.45 * i / 11))
            g.fill((v, v, v), special_flags=pygame.BLEND_RGB_MULT)
            self.levels.append(g)

    def draw(self, dst, t):
        for w in self.w:
            if not w["on"]:
                continue
            b = 0.80 + 0.12 * math.sin(t * w["f"] + w["ph"]) + 0.08 * math.sin(t * w["f"] * 2.7 + w["ph"] * 2)
            b = max(0.45, min(1.0, b))
            col = (int(255 * b), int(200 * b), int(84 * b))
            pygame.draw.rect(dst, col, (w["x"], w["y"], w["w"], w["h"]))
            pygame.draw.rect(dst, (int(255 * b), int(236 * b), int(150 * b)),
                             (w["x"] + 1, w["y"] + 1, max(1, w["w"] - 2), max(1, w["h"] // 2)))
            g = self.levels[int((b - 0.45) / 0.55 * 11)]
            dst.blit(g, (w["x"] + w["w"] // 2 - 20, w["y"] + w["h"] // 2 - 20), special_flags=pygame.BLEND_RGB_ADD)


class Bloom:
    """Cheap multi-scale bloom over the sky region, refreshed every 3rd frame."""

    def __init__(self, height):
        self.h = height
        self.ready = False
        self.tick = 0

    def _init(self, src):
        mk = lambda size: pygame.Surface(size, 0, src)
        h = self.h
        self.sw, self.sh = 300, max(8, int(round(h / 4)))
        self.small = mk((self.sw, self.sh))
        self.b1 = mk((150, max(4, self.sh // 2)))
        self.b2 = mk((38, max(2, self.sh // 8)))
        self.b2u = mk(self.b1.get_size())
        self.out = mk((W, h))
        self.ready = True

    def update(self, region):
        if not self.ready:
            self._init(region)
        pygame.transform.smoothscale(region, self.small.get_size(), self.small)
        self.small.fill((176, 176, 176), special_flags=pygame.BLEND_RGB_SUB)
        self.small.blit(self.small.copy(), (0, 0), special_flags=pygame.BLEND_RGB_ADD)
        pygame.transform.smoothscale(self.small, self.b1.get_size(), self.b1)
        pygame.transform.smoothscale(self.small, self.b2.get_size(), self.b2)
        pygame.transform.smoothscale(self.b2, self.b2u.get_size(), self.b2u)
        self.b1.blit(self.b2u, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
        pygame.transform.smoothscale(self.b1, self.out.get_size(), self.out)

    def apply(self, screen, refresh=True):
        self.tick += 1
        region = screen.subsurface((0, 0, W, self.h))
        if refresh and (self.tick % 3 == 0 or not self.ready):
            self.update(region)
        if self.ready:
            region.blit(self.out, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
