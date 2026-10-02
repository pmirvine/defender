"""Title-screen artwork: the red script Williams logo and the green/red 3D DEFENDER logo."""
import os

import pygame

import font

_DATA = os.path.join(os.path.dirname(__file__), "data")
_WILLIAMS_PNG = os.path.join(_DATA, "williams_logo.png")
RED = (230, 20, 0)
GREEN = (150, 235, 0)
GREEN_HI = (210, 255, 40)
YELLOW = (255, 235, 0)

_cache = {}


def _script_font(size):
    for name in ("applechancery", "timesnewroman", "snellroundhand", "zapfino"):
        if pygame.font.match_font(name):
            f = pygame.font.SysFont(name, size, bold=True, italic=True)
            return f
    return pygame.font.SysFont(None, size, bold=True, italic=True)


def _render_williams():
    """Rasterise 'Williams' in a script face, then reduce to a crisp 1-bit pixel logo."""
    pygame.font.init()
    big = _script_font(120).render("Williams", True, (255, 255, 255))
    src = pygame.mask.from_surface(big, threshold=100)
    full = src.to_surface(setcolor=RED, unsetcolor=(0, 0, 0, 0))
    full = full.subsurface(full.get_bounding_rect()).copy()
    target_w = 86
    target_h = max(8, round(full.get_height() * target_w / full.get_width()))
    small = pygame.transform.smoothscale(full, (target_w, target_h))
    out = pygame.Surface((target_w, target_h), pygame.SRCALPHA)
    for y in range(target_h):
        for x in range(target_w):
            if small.get_at((x, y))[3] > 90:
                out.set_at((x, y), RED)
    return out


def williams_logo():
    s = _cache.get("williams")
    if s is None:
        if os.path.exists(_WILLIAMS_PNG):
            s = pygame.image.load(_WILLIAMS_PNG).convert_alpha()
        else:
            s = _render_williams()
            try:
                pygame.image.save(s, _WILLIAMS_PNG)
            except (OSError, pygame.error):
                pass
        _cache["williams"] = s
    return s


def defender_logo():
    """Heavy slanted DEFENDER: green face over a red extrusion falling down-left."""
    s = _cache.get("defender")
    if s is not None:
        return s
    glyphs = font.render_text("DEFENDER", (255, 255, 255), 1)  # 8 rows tall
    wide = pygame.transform.scale(glyphs, (glyphs.get_width() * 5 // 2, 24))
    # embolden: OR the mask with a copy one pixel to the right
    bold = pygame.Surface((wide.get_width() + 1, 24), pygame.SRCALPHA)
    bold.blit(wide, (0, 0))
    bold.blit(wide, (1, 0))
    w, h = bold.get_size()
    lean = h // 3
    face = pygame.Surface((w + lean, h), pygame.SRCALPHA)
    for y in range(h):  # shear: top leans right
        row = bold.subsurface((0, y, w, 1))
        face.blit(row, ((h - 1 - y) // 3, y))
    depth = 5
    out = pygame.Surface((face.get_width() + depth, h + depth), pygame.SRCALPHA)
    red = _tint(face, RED)
    for d in range(depth, 0, -1):
        out.blit(red, (depth - d // 2 - 1 + 0, d))
    out.blit(_tint(face, GREEN), (depth, 0))
    # lighter band across the top of the face for the beveled arcade look
    hi = _tint(face, GREEN_HI)
    out.blit(hi, (depth, 0), area=(0, 0, face.get_width(), 4))
    _cache["defender"] = out
    return out


def _tint(surf, color):
    t = surf.copy()
    t.fill((*color, 255), special_flags=pygame.BLEND_RGBA_MULT)
    return t
