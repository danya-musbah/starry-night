"""The swirling sky.

* three pre-painted variants (thousands of brush strokes, following a flow
  field of swirls) are cross-faded slowly -> shimmering brushwork;
* ~1500 live brush strokes drift along the same flow field;
* a low-res light map rotates around the two big vortices.
"""
import math

import numpy as np
import pygame

from .composition import VORTICES, STARS, MOON, band_y, band_slope
from .config import W, H
from .noise import fbm2d
from .palette import SKY_RAMP, GOLD_RAMP, ALL_COLORS, GOLD_OFFSET
from .post import apply_factor

PASSES = [  # size, count (for a 1200x620 sky), angle jitter, only-bright
    ((84, 22), 1500, 0.16, False),
    ((46, 12), 6500, 0.20, False),
    ((26, 7), 12500, 0.26, False),
    ((14, 4), 7500, 0.32, True),
]


class Sky:
    PERIOD = 9.0

    def __init__(self, brush, flow, sky_h, rng):
        self.brush, self.flow, self.h, self.rng = brush, flow, sky_h, rng
        self.noise = fbm2d(W, sky_h, rng, scale=90, octaves=3)
        self._make_passes()
        self.variants = [self._paint(k) for k in range(3)]
        self._init_light()

    # ----------------------------------------------------------- colouring
    def _shade(self, x, y):
        rng = self.rng
        nz = self.noise[np.clip(y.astype(np.int32), 0, self.h - 1),
                        np.clip(x.astype(np.int32), 0, W - 1)]
        s = 0.20 + 0.20 * nz
        hz = np.clip((y / H - 0.30) / 0.35, 0, 1)
        s = s + 0.20 * hz * hz * (0.5 + nz)
        gold = np.zeros_like(s)

        for cx, cy, R, spin, _, _ in VORTICES[:4]:
            dx, dy = x - cx, y - cy
            r = np.hypot(dx, dy) + 1e-3
            th = np.arctan2(dy, dx)
            w = np.exp(-(r / (1.9 * R)) ** 2)
            arms = 0.5 + 0.5 * np.sin(2.0 * th - spin * 5.5 * np.log(r / R + 0.12) + nz * 1.6)
            s = s * (1 - w) + w * (0.16 + 0.76 * arms ** 1.6)
            s = s + 0.28 * np.exp(-(r / (0.35 * R)) ** 2)

        d = y - band_y(x)
        wb = np.exp(-(d / (0.07 * H)) ** 2)
        s = s * (1 - 0.6 * wb) + wb * (0.42 + 0.40 * (0.5 + 0.5 * np.sin(d * 0.09 + x * 0.01 + nz * 3)))

        mx, my, mr = MOON
        r = np.hypot(x - mx, y - my)
        wm = np.exp(-(r / (4.5 * mr)) ** 2)
        s = s * (1 - wm) + wm * (0.50 + 0.40 * np.cos(r / 11.0))
        gold = np.maximum(gold, np.exp(-(r / (2.4 * mr)) ** 2))

        for sx, sy, sr, _, _ in STARS:
            r = np.hypot(x - sx, y - sy)
            ws = np.exp(-(r / (3.3 * sr)) ** 2)
            s = s * (1 - ws) + ws * (0.55 + 0.40 * (0.5 + 0.5 * np.cos(r / 7.0)))
            gold = np.maximum(gold, np.exp(-(r / (1.9 * sr)) ** 2))

        n = len(x)
        bi = np.clip(np.rint(s * (len(SKY_RAMP) - 1) + rng.normal(0, 0.9, n)), 0, len(SKY_RAMP) - 1).astype(np.int32)
        use_gold = rng.random(n) < gold * 1.05
        gi = np.clip(np.rint(gold * 9 + rng.normal(0, 1.6, n)) + 2, 2, len(GOLD_RAMP) - 1).astype(np.int32)
        cidx = np.where(use_gold, GOLD_OFFSET + gi, bi)
        return cidx, s, use_gold

    def _make_passes(self):
        rng = self.rng
        area = W * self.h / (W * 620.0)
        self.passes = []
        for size, cnt, jit, bright in PASSES:
            n = max(10, int(cnt * area))
            m = n * 3 if bright else n
            x = rng.uniform(-10, W + 10, m)
            y = rng.uniform(-10, self.h + 10, m)
            cidx, s, g = self._shade(x, y)
            if bright:
                keep = np.where((s > 0.52) | g)[0][:n]
                x, y, cidx = x[keep], y[keep], cidx[keep]
            vx, vy = self.flow.sample(x, y)
            ang = np.arctan2(vy, vx) + rng.normal(0, jit, len(x))
            self.passes.append(dict(size=size, x=x, y=y, c=cidx, a=ang))
            if size == (46, 12):
                self.passes.extend(self._curve_passes())

    def _curve_passes(self):
        """Brush strokes laid along explicit parametric curves:
        logarithmic spirals r = r0 * e^(b*theta) around each big vortex, and
        offset copies of the sinuous 'milky way' curve y = f(x)."""
        rng = self.rng
        out = []
        b = 0.21
        for size, step in (((34, 9), 20.0), ((20, 6), 11.0)):
            xs, ys, an, cs = [], [], [], []
            for cx, cy, R, spin, _, _ in VORTICES[:4]:
                for arm in range(4):
                    th0 = arm * 2 * math.pi / 4 + rng.uniform(0, 0.4)
                    th = 0.0
                    light = arm % 2 == 0
                    while True:
                        r = 0.10 * R * math.exp(b * th)
                        if r > 1.7 * R:
                            break
                        a = th0 + spin * th
                        dx = b * r * math.cos(a) - r * spin * math.sin(a)
                        dy = b * r * math.sin(a) + r * spin * math.cos(a)
                        ang = math.atan2(dy, dx)
                        nx, ny = -math.sin(ang), math.cos(ang)
                        off = rng.normal(0, 2.6)
                        xs.append(cx + r * math.cos(a) + nx * off)
                        ys.append(cy + r * math.sin(a) + ny * off)
                        an.append(ang + rng.normal(0, 0.05))
                        cs.append(int(rng.integers(17, 27)) if light else int(rng.integers(6, 12)))
                        th += min(0.22, step / (r * math.sqrt(1 + b * b) + 1e-3))
            for off in (-0.040, -0.016, 0.010, 0.034):
                x = -10.0
                while x < W + 10:
                    yy = band_y(x) + H * off + 7 * math.sin(x * 0.05 + off * 90)
                    xs.append(x)
                    ys.append(yy)
                    an.append(math.atan(band_slope(x)) + rng.normal(0, 0.06))
                    cs.append(int(rng.integers(15, 26)) if off > 0 else int(rng.integers(8, 15)))
                    x += step
            keep = [i for i, y in enumerate(ys) if y < self.h + 20]
            out.append(dict(size=size, x=np.array(xs)[keep], y=np.array(ys)[keep],
                            c=np.array(cs, np.int32)[keep], a=np.array(an)[keep]))
        return out

    def _base(self):
        h = self.h
        yy = np.linspace(0, 1, h, dtype=np.float32)
        cols = np.stack([np.interp(yy, [0, 0.5, 1], [a, b, c])
                         for a, b, c in zip((7, 15, 50), (14, 34, 92), (30, 70, 128))], axis=1)  # (h,3)
        arr = np.broadcast_to(cols[:, None, :], (h, W, 3)).copy()
        arr += ((self.noise - 0.5) * 18)[..., None]
        arr = np.clip(arr, 0, 255).astype(np.uint8)
        return pygame.image.frombuffer(arr.tobytes(), (W, h), "RGB").copy().convert()

    def _paint(self, k):
        surf = self._base()
        shift_f = (0.0, 0.42, -0.42)[k]
        cshift = (0, 1, -1)[k]
        for p in self.passes:
            size = p["size"]
            sh = shift_f * size[0]
            x = p["x"] + np.cos(p["a"]) * sh
            y = p["y"] + np.sin(p["a"]) * sh
            c = p["c"]
            if cshift:
                c = np.where(c < GOLD_OFFSET, np.clip(c + cshift, 0, GOLD_OFFSET - 1), c)
            for xi, yi, ci, ai in zip(x.tolist(), y.tolist(), c.tolist(), p["a"].tolist()):
                spr = self.brush.get(ALL_COLORS[ci], size, ai)
                surf.blit(spr, (int(xi - spr.get_width() / 2), int(yi - spr.get_height() / 2)))
        apply_factor(surf)
        return surf

    # ----------------------------------------------------------- light map
    def _init_light(self):
        self.gw = 120
        self.cellw = W / self.gw
        self.gh = int(math.ceil(self.h / self.cellw))
        gx = (np.arange(self.gw) + 0.5) * self.cellw
        gy = (np.arange(self.gh) + 0.5) * self.cellw
        X, Y = np.meshgrid(gx, gy)
        self.LX, self.LY = X.astype(np.float32), Y.astype(np.float32)
        self.polar = []
        for cx, cy, R, spin, _, _ in VORTICES[:2]:
            dx, dy = X - cx, Y - cy
            r = np.hypot(dx, dy) + 1e-3
            self.polar.append((np.arctan2(dy, dx), np.log(r / R + 0.12), np.exp(-(r / (1.9 * R)) ** 2), spin))
        d = Y - band_y(X)
        self.band_w = np.exp(-(d / (0.09 * H)) ** 2)
        self.tint = np.array((24, 44, 60), np.float32)
        self._light_surf, self._lf = None, 0
        self.light_size = (W, self.gh * int(round(self.cellw)))

    def _light(self, t):
        L = np.zeros((self.gh, self.gw), np.float32)
        for k, (th, lnr, w, spin) in enumerate(self.polar):
            L += w * (0.5 + 0.5 * np.sin(2.0 * th - spin * 5.5 * lnr - spin * (0.9 + 0.2 * k) * t))
        L += 0.7 * self.band_w * (0.5 + 0.5 * np.sin(self.LX * 0.012 - 0.8 * t + self.LY * 0.01))
        L += 0.30 * (0.5 + 0.5 * np.sin(0.35 * t + self.LX * 0.003 + self.LY * 0.002))
        L = np.clip(L * 0.55, 0, 1) ** 1.4
        arr = (L[..., None] * self.tint).astype(np.uint8)
        small = pygame.image.frombuffer(arr.tobytes(), (self.gw, self.gh), "RGB")
        return pygame.transform.smoothscale(small, self.light_size)

    # --------------------------------------------------------------- draw
    def draw(self, dst, t):
        dst.blit(self.variants[0], (0, 0))
        ph = t / self.PERIOD
        k = int(ph) % 2
        f = 0.5 - 0.5 * math.cos(2 * math.pi * (ph - int(ph)))
        v = self.variants[1 + k]
        v.set_alpha(int(255 * f))
        dst.blit(v, (0, 0))
        self._lf += 1
        if self._light_surf is None or self._lf % 2 == 0:
            self._light_surf = self._light(t)
        dst.blit(self._light_surf, (0, 0), special_flags=pygame.BLEND_RGB_ADD)


class StrokeSprites:
    """Padded, pre-faded brush sprites for the live particles."""
    SIZES = [(20, 6), (34, 9)]
    ALPHAS = [24, 52, 84, 116, 148, 180]

    def __init__(self, brush):
        self.brush = brush
        self.pad = [int(math.ceil(math.hypot(*s))) + 2 for s in self.SIZES]
        self.half = [p // 2 for p in self.pad]
        self.table = []          # [size][level][color][angle]
        for si, size in enumerate(self.SIZES):
            pad = self.pad[si]
            levels = []
            for a in self.ALPHAS:
                per_color = []
                for rgb in ALL_COLORS:
                    per_angle = []
                    for k in range(brush.n):
                        spr = brush.get_idx(rgb, size, k, v=0)
                        sq = pygame.Surface((pad, pad), pygame.SRCALPHA)
                        sq.blit(spr, ((pad - spr.get_width()) // 2, (pad - spr.get_height()) // 2))
                        sq.fill((255, 255, 255, a), special_flags=pygame.BLEND_RGBA_MULT)
                        per_angle.append(sq)
                    per_color.append(per_angle)
                levels.append(per_color)
            self.table.append(levels)


class Particles:
    N = 2800

    def __init__(self, flow, sprites, sky_h, rng):
        self.flow, self.sp, self.sky_h, self.rng = flow, sprites, sky_h, rng
        N = self.N
        self.pos = np.zeros((N, 2), np.float32)
        self.age = np.zeros(N, np.float32)
        self.life = np.ones(N, np.float32)
        self.col = np.zeros(N, np.int32)
        self.size = np.zeros(N, np.int32)
        self.active = 1500
        self.ang = np.zeros(N, np.float32)
        self.centers = np.array([(s[0], s[1], s[2]) for s in STARS] + [MOON], np.float32)
        self.reset()

    def reset(self):
        self._spawn(np.arange(self.N), randomize_age=True)
        self.step(0.0)

    def _spawn(self, idx, randomize_age=False):
        rng = self.rng
        k = len(idx)
        x = rng.uniform(0, W, k)
        y = rng.uniform(0, self.sky_h, k)
        vx, vy = self.flow.sample(x, y)
        mag = np.hypot(vx, vy)
        bad = rng.random(k) > np.clip(0.25 + 0.55 * mag, 0, 1)
        x[bad] = rng.uniform(0, W, bad.sum())
        y[bad] = rng.uniform(0, self.sky_h, bad.sum())
        vx, vy = self.flow.sample(x, y)
        mag = np.hypot(vx, vy)
        col = np.clip((3 + 19 * np.clip(rng.random(k) * (0.35 + 0.5 * mag), 0, 1)).astype(np.int32), 0, GOLD_OFFSET - 1)

        orb = rng.random(k) < 0.28
        no = int(orb.sum())
        if no:
            c = self.centers[rng.integers(0, len(self.centers), no)]
            rr = rng.uniform(1.3, 3.8, no) * c[:, 2]
            ph = rng.uniform(0, 2 * np.pi, no)
            x[orb] = c[:, 0] + rr * np.cos(ph)
            y[orb] = c[:, 1] + rr * np.sin(ph)
            col[orb] = GOLD_OFFSET + rng.integers(4, 12, no)
        self.pos[idx, 0] = x
        self.pos[idx, 1] = y
        self.col[idx] = col
        self.size[idx] = (rng.random(k) < 0.35).astype(np.int32)
        self.life[idx] = rng.uniform(2.5, 6.0, k)
        self.age[idx] = rng.uniform(0, 1, k) * self.life[idx] if randomize_age else 0.0

    def step(self, dt):
        n = self.active
        p = self.pos[:n]
        vx, vy = self.flow.sample(p[:, 0], p[:, 1])
        mag = np.sqrt(vx * vx + vy * vy) + 1e-4
        self.ang[:n] = np.arctan2(vy, vx)
        if dt <= 0:
            return
        speed = 14.0 + 30.0 * mag
        p[:, 0] += vx / mag * speed * dt
        p[:, 1] += vy / mag * speed * dt
        self.age[:n] += dt
        dead = np.where((self.age[:n] > self.life[:n]) | (p[:, 1] > self.sky_h) |
                        (p[:, 0] < -20) | (p[:, 0] > W + 20) | (p[:, 1] < -20))[0]
        if len(dead):
            self._spawn(dead)

    def draw(self, dst):
        n = self.active
        f = np.sin(np.pi * np.clip(self.age[:n] / self.life[:n], 0, 1))
        vis = np.where(f > 0.06)[0]
        if not len(vis):
            return
        nl = len(self.sp.ALPHAS)
        lvl = np.minimum((f[vis] * nl).astype(np.int32), nl - 1).tolist()
        nang = self.sp.brush.n
        ai = (np.rint((self.ang[vis] % np.pi) / np.pi * nang).astype(np.int32) % nang).tolist()
        si = self.size[vis]
        halves = np.array(self.sp.half)[si]
        px = (self.pos[vis, 0] - halves).astype(np.int32).tolist()
        py = (self.pos[vis, 1] - halves).astype(np.int32).tolist()
        ci = self.col[vis].tolist()
        tbl = self.sp.table
        seq = [(tbl[s][l][c][a], (x, y)) for s, l, c, a, x, y in zip(si.tolist(), lvl, ci, ai, px, py)]
        dst.blits(seq, False)
