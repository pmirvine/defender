"""Visual effects: starfield, laser, thrust flame, materialize, particles, flash."""
import random
import pygame
import assets
from palette import PALETTE, WHITE, laser_color, COLTAB_RGB

W, H = 304, 256
WORLD = 2048
PLAY_TOP = 42
X_OFF = 6


def wrap_dx(x, cam_x):
    """World x -> screen-x offset relative to cam, wrapped into [-1024+.., 1024)."""
    d = (x - cam_x) % WORLD
    if d > WORLD - 256:
        d -= WORLD
    return d


class Starfield:
    def __init__(self, n=48, seed=1981):
        r = random.Random(seed)
        cols = [(255, 255, 255), (145, 145, 170), (255, 182, 0), (0, 182, 0), (255, 0, 0), (36, 0, 170)]
        self.stars = []
        for _ in range(n):
            self.stars.append((r.randrange(W), r.randrange(PLAY_TOP + 2, 190), r.choice((0.25, 0.5, 0.75)),
                               r.choice(cols), r.randrange(60)))

    def draw(self, surf, cam_x, tick):
        for x, y, par, col, ph in self.stars:
            if (tick + ph) % 40 < 4:      # twinkle: brief off
                continue
            sx = int(x - cam_x * par) % W
            if (tick // 20 + ph) % 3 == 0:
                col = (255, 255, 255)
            surf.set_at((sx, y), col)


def draw_laser(surf, laser, cam_x, tick, cycle_offset=0):
    sx0 = wrap_dx(laser.x0, cam_x) + X_OFF
    sx1 = wrap_dx(laser.x1, cam_x) + X_OFF
    y = int(laser.y)
    step = 1 if sx1 >= sx0 else -1
    a, b = int(sx0), int(sx1)
    n = abs(b - a)
    seg = 0
    i = 0
    while i <= n:
        col = laser_color(tick, seg * 2 + cycle_offset)
        end = min(n, i + 3)
        x_from = a + step * i
        x_to = a + step * end
        lo, hi = min(x_from, x_to), max(x_from, x_to)
        surf.fill(col, (lo, y, hi - lo + 1, 1))
        i += 4
        seg += 1
    # white head
    hx = b
    lo, hi = (hx - 1, hx) if step > 0 else (hx, hx + 1)
    surf.fill(WHITE, (lo, y, 2, 1))


def draw_flame(surf, sx, sy, facing, tick, rng=random):
    """Jittering thrust flame behind the ship (sx,sy = ship centre)."""
    back = -facing
    base = sx + back * 8
    cols = [(255, 182, 0), (255, 0, 0), (255, 255, 0), (255, 255, 255)]
    for i in range(rng.randint(3, 6)):
        dx = rng.randint(0, 6)
        dy = rng.randint(-1, 1)
        surf.set_at((int(base + back * dx), int(sy + dy)), rng.choice(cols))


def draw_materialize(surf, sprite_name, cx, cy, amount, pal, rng=None):
    """Pixels of the sprite converge from a random scatter; amount 0..1 (1 = formed)."""
    raw = assets._raw()[sprite_name]
    w, h, rows = raw
    rng = rng or random.Random(int(amount * 100))
    spread = int((1.0 - max(0.0, min(1.0, amount))) * 48)
    ox, oy = int(cx - w // 2), int(cy - h // 2)
    for y in range(h):
        for x in range(w):
            v = rows[y][x]
            if v:
                px = ox + x + (rng.randint(-spread, spread) if spread else 0)
                py = oy + y + (rng.randint(-spread // 2, spread // 2) if spread else 0)
                if 0 <= px < W and 0 <= py < H:
                    surf.set_at((px, py), pal[v])


def draw_particles(surf, particles, cam_x, pal):
    for p in particles:
        sx = wrap_dx(p.x, cam_x) + X_OFF
        if -2 <= sx < W + 2:
            sy = int(p.y)
            if 0 <= sy < H and 0 <= int(sx) < W:
                col = pal[p.color & 15]
                surf.set_at((int(sx), sy), col)
                if getattr(p, "big", False):
                    surf.fill(col, (int(sx), sy, 2, 2))


def flash_color(game_flash, tick):
    """Background colour for a flash frame, or None."""
    if game_flash <= 0:
        return None
    if tick % 2:
        return WHITE
    return COLTAB_RGB[(tick * 3) % len(COLTAB_RGB)]
