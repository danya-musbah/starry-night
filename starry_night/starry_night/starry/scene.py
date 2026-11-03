"""Scene: owns all layers, time, speed and the draw order."""
import time

import numpy as np
import pygame

from .atmosphere import Bloom, Mist, Windows
from .brush import BrushLibrary
from .celestial import Moon, StarLayer
from .composition import FlowField
from .config import SEED, SPEED_MAX, SPEED_MIN, SPEED_STEP
from .cypress import Cypress
from .landscape import Land
from .sky import Particles, Sky, StrokeSprites


class Scene:
    def __init__(self, screen, log=print):
        self.screen = screen
        rng = np.random.default_rng(SEED)
        brush = BrushLibrary()
        log("  · painting hills, village and church …")
        self.land = Land(brush, rng)
        log("  · building swirl flow field …")
        self.flow = FlowField()
        log("  · painting the sky (tens of thousands of brush strokes) …")
        self.sky = Sky(brush, self.flow, self.land.sky_h, rng)
        log("  · preparing living brush strokes …")
        self.sprites = StrokeSprites(brush)
        self.particles = Particles(self.flow, self.sprites, self.land.sky_h, rng)
        log("  · stars, moon, cypress, mist …")
        self.stars = StarLayer(brush, rng)
        self.moon = Moon(brush, rng)
        self.cypress = Cypress(brush, rng)
        self.mist = Mist(rng)
        self.windows = Windows(self.land.windows)
        self.bloom = Bloom(self.land.sky_h)
        self.font = pygame.font.Font(None, 30)
        self.reset()

    # ------------------------------------------------------------ state
    def reset(self):
        self.t = 0.0
        self.speed = 1.0
        self.paused = False
        self.glow = True
        self.particles.active = 1500
        self.particles.reset()
        self._toast = None
        self._avg = 1 / 60
        self._adapt_t = 0.0

    def toast(self, text, secs=1.6):
        self._toast = (self.font.render(text, True, (240, 232, 190)), time.time() + secs)

    def toggle_pause(self):
        self.paused = not self.paused
        self.toast("Paused" if self.paused else "Playing")

    def change_speed(self, direction):
        self.speed = float(np.clip(self.speed + direction * SPEED_STEP, SPEED_MIN, SPEED_MAX))
        self.toast(f"Speed  {self.speed:.2f}x")

    def toggle_glow(self):
        self.glow = not self.glow
        self.toast("Star glow  ON" if self.glow else "Star glow  OFF")

    # ------------------------------------------------------------ update
    def update(self, dt):
        sim = 0.0 if self.paused else dt * self.speed
        self.t += sim
        self.particles.step(sim)
        self._adapt(dt)

    def _adapt(self, dt):
        """Keep ~60 FPS on slower machines by scaling live-stroke count."""
        self._avg = 0.95 * self._avg + 0.05 * dt
        self._adapt_t += dt
        if self._adapt_t > 1.0:
            self._adapt_t = 0.0
            p = self.particles
            if self._avg > 1 / 52:
                p.active = max(300, int(p.active * 0.82))
            elif self._avg < 1 / 63 and p.active < p.N:
                p.active = min(p.N, int(p.active * 1.08) + 10)

    # -------------------------------------------------------------- draw
    def draw(self):
        s, t = self.screen, self.t
        self.sky.draw(s, t)
        self.particles.draw(s)
        self.moon.draw(s, t, self.glow)
        self.stars.draw(s, t, self.glow)
        if self.glow:
            self.bloom.apply(s, refresh=not self.paused or not self.bloom.ready)
        self.land.draw(s)
        self.mist.draw(s, t, 0)
        self.windows.draw(s, t)
        self.cypress.draw(s, t)
        self.mist.draw(s, t, 1)
        if self._toast:
            surf, until = self._toast
            if time.time() < until:
                s.blit(surf, (20, 18))
            else:
                self._toast = None
