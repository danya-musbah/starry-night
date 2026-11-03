"""Baked vignette + canvas-weave factor applied to static layers."""
import numpy as np
import pygame

from .config import W, H

_FACTOR = None


def factor():
    global _FACTOR
    if _FACTOR is None:
        rng = np.random.default_rng(5)
        X, Y = np.mgrid[0:W, 0:H].astype(np.float32)
        cx, cy = W / 2, H / 2
        d = np.sqrt(((X - cx) / cx) ** 2 + ((Y - cy) / cy) ** 2) / 1.4142
        vig = 1 - 0.42 * np.clip(d, 0, 1) ** 2.3
        weave = np.sin(X * 1.9) * np.sin(Y * 1.9)
        noise = rng.random((W, H)).astype(np.float32)
        canvas = 0.962 + 0.038 * (0.5 * weave + 0.5 * noise)
        _FACTOR = (vig * canvas)[:, :, None].astype(np.float32)
    return _FACTOR


def apply_factor(surface, x0=0, y0=0):
    w, h = surface.get_size()
    f = factor()[x0:x0 + w, y0:y0 + h]
    arr = pygame.surfarray.pixels3d(surface)
    arr[:] = np.clip(arr * f, 0, 255).astype(np.uint8)
    del arr
