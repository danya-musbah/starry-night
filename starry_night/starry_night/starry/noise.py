"""Small smooth-noise helpers (numpy only)."""
import numpy as np


def fbm1d(n, rng, scale=160.0, octaves=4, persistence=0.5):
    xs = np.arange(n, dtype=np.float32)
    out = np.zeros(n, np.float32)
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        s = scale / (2 ** o)
        k = int(n / s) + 3
        pts = rng.random(k).astype(np.float32)
        f = xs / s
        i = f.astype(np.int32)
        t = f - i
        t = t * t * (3 - 2 * t)
        out += amp * (pts[i] * (1 - t) + pts[i + 1] * t)
        tot += amp
        amp *= persistence
    return out / tot


def fbm2d(w, h, rng, scale=64.0, octaves=4, persistence=0.5):
    """Returns an (h, w) float32 array in [0, 1]."""
    xs = np.arange(w, dtype=np.float32)
    ys = np.arange(h, dtype=np.float32)
    out = np.zeros((h, w), np.float32)
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        s = scale / (2 ** o)
        gw, gh = int(w / s) + 3, int(h / s) + 3
        grid = rng.random((gh, gw)).astype(np.float32)
        fx, fy = xs / s, ys / s
        ix, iy = fx.astype(np.int32), fy.astype(np.int32)
        tx, ty = fx - ix, fy - iy
        tx = tx * tx * (3 - 2 * tx)
        ty = ty * ty * (3 - 2 * ty)
        g00 = grid[np.ix_(iy, ix)]
        g01 = grid[np.ix_(iy, ix + 1)]
        g10 = grid[np.ix_(iy + 1, ix)]
        g11 = grid[np.ix_(iy + 1, ix + 1)]
        top = g00 * (1 - tx)[None, :] + g01 * tx[None, :]
        bot = g10 * (1 - tx)[None, :] + g11 * tx[None, :]
        out += amp * (top * (1 - ty)[:, None] + bot * ty[:, None])
        tot += amp
        amp *= persistence
    return out / tot
