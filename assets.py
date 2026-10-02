"""Sprite loading from data/sprites_raw.txt into 8-bit palettized pygame Surfaces (colorkey 0).

Use `blit_sprite(dst, surf, pos, pal)` to draw with a frame palette (see palette.frame_palette).
"""
import os
import pygame
from palette import PALETTE

_PATH = os.path.join(os.path.dirname(__file__), "data", "sprites_raw.txt")
_RAW = None     # name -> (w_px, h, rows[list of list int])
_SURF = {}
_FLIP = {}


def parse(path=_PATH):
    raw = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "|" not in line:
                continue
            head, data = line.split("|", 1)
            parts = head.split()
            if len(parts) != 3 or parts[0].startswith("FONT_"):
                continue
            name, wb, h = parts[0], int(parts[1]), int(parts[2])
            data = [int(x, 16) for x in data.split()]
            w = wb * 2
            rows = [[0] * w for _ in range(h)]
            for c in range(wb):
                for y in range(h):
                    b = data[c * h + y] if c * h + y < len(data) else 0
                    rows[y][2 * c] = b >> 4
                    rows[y][2 * c + 1] = b & 15
            raw[name] = (w, h, rows)
    return raw


def _raw():
    global _RAW
    if _RAW is None:
        _RAW = parse()
    return _RAW


def make_surface(w, h, rows):
    s = pygame.Surface((w, h), depth=8)
    s.set_palette(PALETTE)
    s.set_colorkey(0)
    s.fill(0)
    for y in range(h):
        for x in range(w):
            v = rows[y][x]
            if v:
                s.set_at((x, y), v)
    return s


def names():
    return list(_raw().keys())


def sprite(name):
    """Palettized Surface for a raw sprite name (e.g. 'LND10')."""
    s = _SURF.get(name)
    if s is None:
        w, h, rows = _raw()[name]
        s = _SURF[name] = make_surface(w, h, rows)
    return s


def flipped(name):
    s = _FLIP.get(name)
    if s is None:
        s = _FLIP[name] = pygame.transform.flip(sprite(name), True, False)
    return s


def blit_sprite(dst, surf, pos, pal):
    surf.set_palette(pal)
    dst.blit(surf, pos)


def sprite_name(kind, frame=0, facing=1):
    """Map an entity kind (+frame) to a raw sprite name, or None if unknown."""
    f = int(frame or 0)
    if kind == "lander":
        return "LND%d0" % (1 + f % 3)
    if kind == "mutant":
        return "SCZD10" if (f // 2) % 2 == 0 else "SCZD11"
    if kind == "baiter":
        return "UFOD%d0" % (1 + f % 3)
    if kind == "bomber":
        return "TIED%d0" % (1 + f % 4)
    if kind == "pod":
        return "PRBD10"
    if kind == "swarmer":
        return "SWMD10" if (f // 2) % 2 == 0 else "SWMD11"
    if kind == "humanoid":
        return "ASTD%d0" % (1 + f % 4)
    if kind == "enemy_shot":
        return "BMBD10" if f % 2 == 0 else "BMBD11"
    if kind == "mine":
        return "BMBD20"
    if kind == "player":
        return "PLD10" if facing >= 0 else "PLD20"
    return None


def sprite_for(kind, frame=0, facing=1):
    n = sprite_name(kind, frame, facing)
    return sprite(n) if n else None


EXPLOSION = "BXD10"
SMART_BOMB_ICON = "SBD10"
MINI_SHIP = "PLAM0"
POPUP = {250: "C25D10", 500: "C5D10"}
TERRAIN_EXPLOSION = "TERX0"
