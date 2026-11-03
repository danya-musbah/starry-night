"""Composition of the painting: where the swirls, stars and moon live."""
import numpy as np

from .config import W, H

# cx, cy, radius, spin(+1 clockwise / -1 counter), inward, weight
VORTICES = [
    (0.405 * W, 0.300 * H, 135, +1, 0.30, 1.6),   # big left eye of the swirl
    (0.600 * W, 0.315 * H, 120, -1, 0.30, 1.5),   # big right eye
    (0.115 * W, 0.150 * H,  85, -1, 0.15, 1.0),
    (0.800 * W, 0.365 * H,  95, +1, 0.15, 0.9),
    (0.530 * W, 0.085 * H,  80, +1, 0.10, 0.8),
]

# x, y, core radius, pulse frequency, phase
STARS = [
    (0.205 * W, 0.215 * H, 15, 0.82, 0.3),
    (0.320 * W, 0.118 * H, 18, 1.10, 1.9),
    (0.455 * W, 0.078 * H, 14, 0.93, 4.1),
    (0.575 * W, 0.150 * H, 17, 1.31, 2.6),
    (0.690 * W, 0.085 * H, 14, 0.74, 5.2),
    (0.715 * W, 0.290 * H, 16, 1.05, 0.9),
    (0.350 * W, 0.385 * H, 14, 1.42, 3.3),
    (0.520 * W, 0.455 * H, 13, 0.88, 1.2),
    (0.180 * W, 0.440 * H, 15, 1.18, 4.7),
    (0.815 * W, 0.435 * H, 13, 0.97, 2.2),
    (0.640 * W, 0.470 * H, 12, 1.25, 5.8),
]

MOON = (0.865 * W, 0.155 * H, 60)     # x, y, radius


def band_y(x):
    u = x / W * 2 * np.pi
    return H * (0.405 + 0.060 * np.sin(u * 1.5 + 0.35) + 0.028 * np.sin(u * 3.4 + 1.2))


def band_slope(x):
    u = x / W * 2 * np.pi
    k = 2 * np.pi / W
    return H * (0.060 * 1.5 * k * np.cos(u * 1.5 + 0.35) + 0.028 * 3.4 * k * np.cos(u * 3.4 + 1.2))


def compute_flow(X, Y):
    """Velocity field (vx, vy): swirls + the long sinuous 'milky way' band."""
    vx = np.zeros(X.shape, np.float32)
    vy = np.zeros(X.shape, np.float32)

    def vortex(cx, cy, R, spin, inward, wt):
        dx, dy = X - cx, Y - cy
        r = np.sqrt(dx * dx + dy * dy) + 1e-3
        w = wt / (1 + (r / R) ** 2) ** 1.4
        vx[...] += w * (-dy / r * spin - dx / r * inward)
        vy[...] += w * (dx / r * spin - dy / r * inward)

    for v in VORTICES:
        vortex(*v)
    vortex(MOON[0], MOON[1], MOON[2] * 1.7, -1, 0.0, 1.5)
    for i, (sx, sy, sr, _, _) in enumerate(STARS):
        vortex(sx, sy, sr * 2.2, +1 if i % 2 == 0 else -1, 0.0, 1.3)

    d = Y - band_y(X)
    wb = 0.95 * np.exp(-(d / (0.07 * H)) ** 2)
    sl = band_slope(X)
    n = np.sqrt(1 + sl * sl)
    vx += wb / n
    vy += wb * sl / n

    th = 0.35 * np.sin(X * 0.006 + Y * 0.004) + 0.18 * np.sin(Y * 0.011 + 1.0)
    vx += 0.38 * np.cos(th)
    vy += 0.38 * np.sin(th)
    return vx, vy


class FlowField:
    def __init__(self, cell=8):
        self.cell = cell
        self.gw = W // cell + 2
        self.gh = H // cell + 2
        xs = np.arange(self.gw, dtype=np.float32) * cell
        ys = np.arange(self.gh, dtype=np.float32) * cell
        X, Y = np.meshgrid(xs, ys)
        self.vx, self.vy = compute_flow(X, Y)

    def sample(self, x, y):
        c = self.cell
        fx = np.clip(np.asarray(x, np.float32) / c, 0, self.gw - 1.001)
        fy = np.clip(np.asarray(y, np.float32) / c, 0, self.gh - 1.001)
        ix, iy = fx.astype(np.int32), fy.astype(np.int32)
        tx, ty = fx - ix, fy - iy

        def bil(a):
            return ((a[iy, ix] * (1 - tx) + a[iy, ix + 1] * tx) * (1 - ty) +
                    (a[iy + 1, ix] * (1 - tx) + a[iy + 1, ix + 1] * tx) * ty)
        return bil(self.vx), bil(self.vy)
