"""Variable-width font from FONT_* entries in sprites_raw.txt (column-major, 8 rows/column)."""
import os
import pygame

_PATH = os.path.join(os.path.dirname(__file__), "data", "sprites_raw.txt")
_GLYPHS = None   # char -> (width_px, rows[8][w] of 0/1)
_CACHE = {}
H = 8

_NAMES = {"EXCLPT": "!", "COMMA": ",", "PERIOD": ".", "COLON": ":", "QUESMK": "?"}


def _load():
    global _GLYPHS
    if _GLYPHS is not None:
        return _GLYPHS
    g = {}
    with open(_PATH) as f:
        for line in f:
            p = line.split()
            if not p or not p[0].startswith("FONT_"):
                continue
            nm = p[0][5:]
            if nm in _NAMES:
                ch = _NAMES[nm]
            elif nm.startswith("NUMBR"):
                ch = nm[5:]
            elif nm.startswith("LETTR"):
                ch = nm[5:]
            else:
                continue
            data = [int(x, 16) for x in p[1:]]
            cols = len(data) // 8
            w = cols * 2
            rows = [[0] * w for _ in range(8)]
            for c in range(cols):
                for y in range(8):
                    b = data[c * 8 + y]
                    rows[y][2 * c] = 1 if (b >> 4) else 0
                    rows[y][2 * c + 1] = 1 if (b & 15) else 0
            g[ch] = (w, rows)
    g[" "] = (4, [[0] * 4 for _ in range(8)])
    _GLYPHS = g
    return g


def text_width(text):
    g = _load()
    return sum(g.get(c.upper(), g[" "])[0] for c in text)


def render_text(text, color=(255, 255, 255), scale=1):
    """Return an SRCALPHA Surface with the text drawn in `color`."""
    key = (text, tuple(color), scale)
    s = _CACHE.get(key)
    if s is not None:
        return s
    g = _load()
    w = max(1, text_width(text))
    s = pygame.Surface((w, H), pygame.SRCALPHA)
    x = 0
    col = tuple(color)
    for c in text:
        gw, rows = g.get(c.upper(), g[" "])
        for y in range(8):
            r = rows[y]
            for i in range(gw):
                if r[i]:
                    s.set_at((x + i, y), col)
        x += gw
    if scale != 1:
        s = pygame.transform.scale(s, (w * scale, H * scale))
    if len(_CACHE) > 500:
        _CACHE.clear()
    _CACHE[key] = s
    return s


def draw_text(surface, text, pos, color=(255, 255, 255), center=False, scale=1):
    s = render_text(text, color, scale)
    x, y = pos
    if center:
        x -= s.get_width() // 2
    surface.blit(s, (int(x), int(y)))
    return s.get_width()
