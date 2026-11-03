"""Painting helpers: polygon fills made of brush strokes, sprite builders."""
import math

import numpy as np
import pygame


def surf_from_rgb(arr):
    """(h, w, 3) uint8 -> Surface (display format)."""
    arr = np.ascontiguousarray(arr)
    h, w, _ = arr.shape
    return pygame.image.frombuffer(arr.tobytes(), (w, h), "RGB").copy().convert()


def surf_from_rgba(arr):
    arr = np.ascontiguousarray(arr)
    h, w, _ = arr.shape
    return pygame.image.frombuffer(arr.tobytes(), (w, h), "RGBA").copy().convert_alpha()


def ramp_pick(ramp, s, rng, jitter=0.0):
    n = len(ramp)
    v = np.asarray(s, dtype=np.float32) * (n - 1)
    if jitter:
        v = v + rng.normal(0, jitter, v.shape)
    idx = np.clip(np.rint(v), 0, n - 1).astype(np.int32)
    return [ramp[i] for i in idx.tolist()]


def ellipse_poly(cx, cy, rx, ry, rng=None, n=28, wobble=0.0):
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n
        k = 1 + (rng.uniform(-wobble, wobble) if (rng is not None and wobble) else 0.0)
        pts.append((cx + math.cos(a) * rx * k, cy + math.sin(a) * ry * k))
    return pts


def glow_sprite(R, color, power=2.0):
    """Additive radial glow on black, size 2R x 2R."""
    Y, X = np.mgrid[0:2 * R, 0:2 * R].astype(np.float32)
    d = np.hypot(X + 0.5 - R, Y + 0.5 - R) / R
    inten = np.clip(1 - d, 0, 1) ** power
    arr = (inten[..., None] * np.array(color, np.float32)).astype(np.uint8)
    return surf_from_rgb(arr)


def paint_poly(target, pts, brush, rng, grad, strokes, aa=2):
    """Fill polygon `pts` with a vertical gradient + brush strokes.

    grad    : (top_rgb, bottom_rgb) or None
    strokes : list of (size, density, color_fn, angle_fn, jitter)
              color_fn(xs, ys) -> list of rgb tuples (from a ramp)
              angle_fn(xs, ys) -> radians array
    """
    tw, th = target.get_size()
    x0 = max(0, int(math.floor(min(p[0] for p in pts))))
    y0 = max(0, int(math.floor(min(p[1] for p in pts))))
    x1 = min(tw, int(math.ceil(max(p[0] for p in pts))))
    y1 = min(th, int(math.ceil(max(p[1] for p in pts))))
    bw, bh = x1 - x0, y1 - y0
    if bw <= 1 or bh <= 1:
        return
    layer = pygame.Surface((bw, bh), pygame.SRCALPHA)
    if grad is not None:
        t = np.linspace(0, 1, bh, dtype=np.float32)[:, None, None]
        top = np.array(grad[0], np.float32)[None, None, :]
        bot = np.array(grad[1], np.float32)[None, None, :]
        rgb = np.broadcast_to(top * (1 - t) + bot * t, (bh, bw, 3))
        arr = np.dstack([rgb, np.full((bh, bw), 255, np.float32)]).astype(np.uint8)
        layer.blit(pygame.image.frombuffer(np.ascontiguousarray(arr).tobytes(),
                                           (bw, bh), "RGBA"), (0, 0))
    for size, density, color_fn, angle_fn, jitter in strokes:
        n = int(bw * bh * density)
        if n <= 0:
            continue
        xs = rng.uniform(0, bw, n)
        ys = rng.uniform(0, bh, n)
        cols = color_fn(xs + x0, ys + y0)
        angs = angle_fn(xs + x0, ys + y0) + rng.normal(0, jitter, n)
        for x, y, c, a in zip(xs.tolist(), ys.tolist(), cols, angs.tolist()):
            spr = brush.get(c, size, a)
            layer.blit(spr, (int(x - spr.get_width() / 2), int(y - spr.get_height() / 2)))
    m = pygame.Surface((bw * aa, bh * aa), pygame.SRCALPHA)
    m.fill((255, 255, 255, 0))
    pygame.draw.polygon(m, (255, 255, 255, 255),
                        [((px - x0) * aa, (py - y0) * aa) for px, py in pts])
    m = pygame.transform.smoothscale(m, (bw, bh))
    layer.blit(m, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    target.blit(layer, (x0, y0))
