"""Stars and moon: painted cores + animated glow, halos, pulses and sparks."""
import math

import numpy as np
import pygame

from .composition import STARS, MOON
from .paint import glow_sprite, surf_from_rgb
from .palette import SKY_RAMP, GOLD_RAMP


class Add:
    """Additive sprite on black + its per-channel peak (for cheap dimming)."""
    __slots__ = ("surf", "peak")

    def __init__(self, surf):
        a = pygame.surfarray.pixels3d(surf)
        self.peak = tuple(int(a[..., i].max()) for i in range(3))
        del a
        self.surf = surf


_CONST = None


def blit_add(dst, surf, peak, cx, cy, k, owned=False):
    """Additive blit with brightness k.  Dimming = proportional subtraction
    (fast SIMD path) instead of the slow BLEND_RGB_MULT fill."""
    global _CONST
    if k <= 0.02:
        return
    w, h = surf.get_size()
    if k < 0.985:
        if _CONST is None:
            _CONST = pygame.Surface((900, 900)).convert()
        if not owned:
            surf = surf.copy()
        q = 1.0 - k
        _CONST.fill((int(peak[0] * q), int(peak[1] * q), int(peak[2] * q)), (0, 0, w, h))
        surf.blit(_CONST, (0, 0), (0, 0, w, h), special_flags=pygame.BLEND_RGB_SUB)
    dst.blit(surf, (int(cx - w / 2), int(cy - h / 2)), special_flags=pygame.BLEND_RGB_ADD)


def _apply_radial_alpha(surf, radius_fn):
    size = surf.get_width()
    Y, X = np.mgrid[0:size, 0:size].astype(np.float32)
    mask = radius_fn(X + 0.5, Y + 0.5)
    a = pygame.surfarray.pixels_alpha(surf)
    a[:] = (a * mask.T).astype(np.uint8)
    del a


def make_core(brush, r, rng):
    """Painted star: pale centre, golden concentric brush rings."""
    size = 2 * (r + 4)
    c = size / 2
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    ssz = (max(8, int(r * 0.9)), max(3, int(r * 0.24)))
    for rho in np.arange(1.0, r + 1.0, 2.0):
        n = max(6, int(2 * math.pi * rho / 5.0))
        t = rho / r
        for j in range(n):
            phi = 2 * math.pi * j / n + rng.uniform(-0.2, 0.2)
            gi = int(np.clip(11 - t * 6 + rng.normal(0, 0.8), 3, 11))
            spr = brush.get(GOLD_RAMP[gi], ssz, phi + math.pi / 2)
            surf.blit(spr, (c + rho * math.cos(phi) - spr.get_width() / 2,
                            c + rho * math.sin(phi) - spr.get_height() / 2))
    pygame.draw.circle(surf, (255, 250, 228, 255), (c, c), max(2, int(r * 0.32)))
    _apply_radial_alpha(surf, lambda X, Y: np.clip((r + 1.5 - np.hypot(X - c, Y - c)) / 2.2, 0, 1))
    return surf.convert_alpha()


def make_halo(brush, r_in, R, colour_fn, rng, spacing=5.5, skip_every=3):
    """Concentric rings of tangential brush strokes on black (additive)."""
    size = 2 * R
    c = R
    surf = pygame.Surface((size, size))
    surf.fill((0, 0, 0))
    for i, rho in enumerate(np.arange(r_in, R - 4, spacing)):
        if skip_every and i % skip_every == skip_every - 1:
            continue
        n = int(2 * math.pi * rho / 9)
        t = (rho - r_in) / max(1.0, R - r_in)
        for j in range(n):
            phi = 2 * math.pi * j / n + rng.uniform(-0.1, 0.1)
            spr = brush.get(colour_fn(t, rng), (18, 5), phi + math.pi / 2)
            surf.blit(spr, (c + rho * math.cos(phi) - spr.get_width() / 2,
                            c + rho * math.sin(phi) - spr.get_height() / 2))
    arr = pygame.surfarray.pixels3d(surf)
    X, Y = np.mgrid[0:size, 0:size].astype(np.float32)
    fall = np.clip(1 - np.hypot(X + 0.5 - c, Y + 0.5 - c) / R, 0, 1) ** 0.9
    arr[:] = (arr * fall[:, :, None]).astype(np.uint8)
    del arr
    return surf.convert()


def star_colour(t, rng):
    if t < 0.35:
        return GOLD_RAMP[int(rng.integers(6, 11))]
    if t < 0.70:
        return SKY_RAMP[int(rng.integers(24, 29))]
    return SKY_RAMP[int(rng.integers(16, 24))]


def moon_colour(t, rng):
    if t < 0.30:
        return GOLD_RAMP[int(rng.integers(8, 12))]
    if t < 0.65:
        return GOLD_RAMP[int(rng.integers(3, 8))]
    return SKY_RAMP[int(rng.integers(20, 27))]


def make_ring(size=240, radius=100, width=7):
    Y, X = np.mgrid[0:size, 0:size].astype(np.float32)
    d = np.hypot(X + 0.5 - size / 2, Y + 0.5 - size / 2)
    inten = np.exp(-((d - radius) / width) ** 2)
    arr = (inten[..., None] * np.array((255, 224, 130), np.float32)).astype(np.uint8)
    return surf_from_rgb(arr)


class StarLayer:
    def __init__(self, brush, rng):
        self.ring_src = make_ring()
        self.ring_peak = (255, 224, 130)
        base = glow_sprite(5, (255, 236, 150), 1.4)
        self.spark_lv = []
        for i in range(8):
            g = base.copy()
            v = int(255 * (0.15 + 0.85 * i / 7))
            g.fill((v, v, v), special_flags=pygame.BLEND_RGB_MULT)
            self.spark_lv.append(g)
        self.stars = []
        for (x, y, r, f, ph) in STARS:
            halo = make_halo(brush, 1.35 * r, int(4.3 * r), star_colour, rng)
            self.stars.append(dict(
                x=x, y=y, r=r, f=f, ph=ph,
                core=make_core(brush, r, rng),
                halo=Add(halo),
                glow=Add(glow_sprite(int(4.4 * r), (255, 196, 64), 2.8)),
                dir=1 if rng.random() < 0.5 else -1,
                ring_rate=rng.uniform(0.10, 0.20),
                sparks=[(rng.uniform(0, 6.28), rng.uniform(1.5, 3.2) * r,
                         rng.uniform(0.25, 0.7) * (1 if rng.random() < 0.5 else -1),
                         rng.uniform(0.6, 2.2)) for _ in range(5)],
            ))

    @staticmethod
    def pulse(t, f, ph):
        a = 2 * math.pi * f * t * 0.35 + ph
        v = 0.62 * math.sin(a) + 0.38 * math.sin(1.73 * a + 1.1)
        return 0.5 + 0.5 * v

    def draw(self, dst, t, glow=True):
        for s in self.stars:
            p = self.pulse(t, s["f"], s["ph"])
            x, y, r = s["x"], s["y"], s["r"]
            if glow:
                blit_add(dst, s["glow"].surf, s["glow"].peak, x, y, 0.16 + 0.30 * p)
                hal = pygame.transform.rotate(s["halo"].surf, (t * 9.0 * s["dir"]) % 360)
                blit_add(dst, hal, s["halo"].peak, x, y, 0.20 + 0.30 * p, owned=True)
                u = (t * s["ring_rate"] + s["ph"] * 0.17) % 1.0
                rad = int(r * (1.2 + 3.6 * u))
                if rad > 4:
                    ring = pygame.transform.smoothscale(self.ring_src, (rad * 2, rad * 2))
                    blit_add(dst, ring, self.ring_peak, x, y, 0.45 * (1 - u) ** 1.5 * (0.5 + 0.5 * p), owned=True)
            sc = 0.94 + 0.12 * p
            cs = int(s["core"].get_width() * sc)
            core = pygame.transform.smoothscale(s["core"], (cs, cs))
            dst.blit(core, (int(x - cs / 2), int(y - cs / 2)))
            if glow:
                for a0, rad0, w, fl in s["sparks"]:
                    a = a0 + w * t
                    rr = rad0 * (1 + 0.12 * math.sin(t * fl + a0))
                    k = 0.35 + 0.65 * (0.5 + 0.5 * math.sin(t * fl * 2.1 + a0 * 3))
                    kk = k * (0.5 + 0.5 * p)
                    g = self.spark_lv[min(7, int(kk * 7.99))]
                    dst.blit(g, (int(x + rr * math.cos(a) - 5), int(y + rr * math.sin(a) - 5)), special_flags=pygame.BLEND_RGB_ADD)


class Moon:
    def __init__(self, brush, rng):
        mx, my, R = MOON
        self.x, self.y, self.R = mx, my, R
        D = 2 * (R + 6)
        c = D / 2
        surf = pygame.Surface((D, D), pygame.SRCALPHA)
        for _ in range(900):
            ang = rng.uniform(0, 2 * math.pi)
            rr = R * math.sqrt(rng.uniform(0, 1))
            px, py = c + rr * math.cos(ang), c + rr * math.sin(ang)
            cut = math.hypot(px - (c - 24), py - (c - 17))
            tcol = np.clip((cut - 52) / 26 + rng.normal(0, 0.18), 0, 1)     # nearer to the cut = paler
            col = GOLD_RAMP[int(np.clip(11 - tcol * 8, 2, 11))]
            spr = brush.get(col, (24, 7), ang + math.pi / 2 + rng.normal(0, 0.5))
            surf.blit(spr, (px - spr.get_width() / 2, py - spr.get_height() / 2))
        cx2, cy2 = c - 24, c - 17

        def mask(X, Y):
            a = np.clip((R - np.hypot(X - c, Y - c)) / 1.6, 0, 1)
            b = np.clip((np.hypot(X - cx2, Y - cy2) - 54) / 1.6, 0, 1)
            return a * b
        _apply_radial_alpha(surf, mask)
        self.core = surf.convert_alpha()
        self.glow = Add(glow_sprite(int(R * 4.0), (255, 186, 56), 2.6))
        self.halo1 = Add(make_halo(brush, R * 1.25, int(R * 3.3), moon_colour, rng, spacing=6.5))
        self.halo2 = Add(make_halo(brush, R * 1.55, int(R * 2.6), moon_colour, rng, spacing=7.5, skip_every=2))

    def draw(self, dst, t, glow=True):
        k = 0.80 + 0.14 * math.sin(0.9 * t) + 0.06 * math.sin(2.2 * t + 1.3)
        if glow:
            blit_add(dst, self.glow.surf, self.glow.peak, self.x, self.y, 0.34 * k)
            h1 = pygame.transform.rotate(self.halo1.surf, (t * 4.0) % 360)
            blit_add(dst, h1, self.halo1.peak, self.x, self.y, 0.36 * k, owned=True)
            h2 = pygame.transform.rotate(self.halo2.surf, (-t * 6.5) % 360)
            blit_add(dst, h2, self.halo2.peak, self.x, self.y, 0.30 * k, owned=True)
        dst.blit(self.core, (int(self.x - self.core.get_width() / 2), int(self.y - self.core.get_height() / 2)))
        if glow:
            blit_add(dst, self.glow.surf, self.glow.peak, self.x + 6, self.y + 5, 0.08 * k)
