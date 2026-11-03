"""Colour ramps inspired by the original oil painting."""
import numpy as np


def make_ramp(anchors, n):
    a = np.array(anchors, dtype=np.float32)
    pos = np.linspace(0, 1, len(a))
    t = np.linspace(0, 1, n)
    out = np.stack([np.interp(t, pos, a[:, c]) for c in range(3)], axis=1)
    return [tuple(int(round(v)) for v in row) for row in out]


# deep ultramarine -> cobalt -> cyan -> pale cream
SKY_RAMP = make_ramp([
    (6, 14, 48), (12, 30, 84), (21, 52, 122), (33, 80, 160),
    (60, 120, 188), (108, 170, 208), (176, 214, 222), (230, 236, 206),
], 30)

# burnt orange -> gold -> pale yellow -> warm white
GOLD_RAMP = make_ramp([
    (110, 64, 16), (196, 128, 26), (240, 190, 56),
    (252, 226, 120), (255, 248, 210),
], 12)

ALL_COLORS = SKY_RAMP + GOLD_RAMP
GOLD_OFFSET = len(SKY_RAMP)
