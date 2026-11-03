"""Window, input handling and main loop."""
import argparse
import os
import sys
import time

import pygame

from .config import FPS, H, TITLE, W


def make_screen():
    flags = pygame.SCALED | pygame.RESIZABLE
    try:
        return pygame.display.set_mode((W, H), flags, vsync=1)
    except pygame.error:
        try:
            return pygame.display.set_mode((W, H), flags)
        except pygame.error:
            return pygame.display.set_mode((W, H))


def toggle_fullscreen(screen):
    try:
        pygame.display.toggle_fullscreen()
        return pygame.display.get_surface()
    except pygame.error:
        return screen


def handle_key(scene, key, screen):
    """Returns (keep_running, screen)."""
    if key == pygame.K_ESCAPE:
        return False, screen
    if key == pygame.K_SPACE:
        scene.toggle_pause()
    elif key == pygame.K_UP:
        scene.change_speed(+1)
    elif key == pygame.K_DOWN:
        scene.change_speed(-1)
    elif key == pygame.K_g:
        scene.toggle_glow()
    elif key == pygame.K_r:
        scene.reset()
        scene.toast("Scene reset")
    elif key == pygame.K_f:
        screen = toggle_fullscreen(screen)
        scene.screen = screen
    return True, screen


def run(argv=None):
    ap = argparse.ArgumentParser(description="The Starry Night — Living Painting")
    ap.add_argument("--save-frame", metavar="PNG", help="render and save a still, then exit")
    ap.add_argument("--frames", type=int, default=240, help="frames to simulate before saving / benchmarking")
    ap.add_argument("--bench", action="store_true", help="print average frame cost, then exit")
    args = ap.parse_args(argv)

    pygame.init()
    pygame.display.set_caption(TITLE)
    screen = make_screen()
    clock = pygame.time.Clock()

    font = pygame.font.Font(None, 42)
    screen.fill((6, 12, 36))
    msg = font.render("Painting The Starry Night …", True, (240, 220, 140))
    screen.blit(msg, msg.get_rect(center=(W // 2, H // 2)))
    pygame.display.flip()
    pygame.event.pump()

    from .scene import Scene
    t0 = time.time()
    print("Building scene:")
    scene = Scene(screen)
    print(f"Ready in {time.time() - t0:.1f}s")

    if args.save_frame or args.bench:
        dt = 1 / 60
        times = []
        for i in range(args.frames):
            s = time.perf_counter()
            scene.update(dt)
            scene.draw()
            times.append((time.perf_counter() - s) * 1000)
        if args.bench:
            tail = times[len(times) // 2:]
            print(f"avg {sum(tail) / len(tail):.1f} ms/frame  max {max(tail):.1f} ms  "
                  f"live strokes {scene.particles.active}")
        if args.save_frame:
            pygame.image.save(screen, args.save_frame)
            print("saved", args.save_frame)
        pygame.quit()
        return 0

    running = True
    cap_t = 0.0
    while running:
        dt = min(clock.tick(FPS) / 1000.0, 0.05)
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False
            elif e.type == pygame.KEYDOWN:
                running, screen = handle_key(scene, e.key, screen)
        scene.update(dt)
        scene.draw()
        pygame.display.flip()
        cap_t += dt
        if cap_t > 0.5:
            cap_t = 0.0
            pygame.display.set_caption(
                f"{TITLE}  |  {clock.get_fps():.0f} FPS  |  speed {scene.speed:.2f}x"
                f"{'  |  paused' if scene.paused else ''}")
    pygame.quit()
    return 0
