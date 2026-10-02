"""Palette: 16 entries (BBGGGRRR hardware bytes -> RGB), plus software colour cycling."""

COLTAB = [0x38, 0x39, 0x3A, 0x3B, 0x3C, 0x3D, 0x3E, 0x3F, 0x37, 0x2F, 0x27, 0x1F, 0x17,
          0x47, 0x47, 0x87, 0x87, 0xC7, 0xC7, 0xC6, 0xC5, 0xCC, 0xCB, 0xCA, 0xDA, 0xE8,
          0xF8, 0xF9, 0xFA, 0xFB, 0xFD, 0xFF, 0xBF, 0x3F, 0x3E, 0x3C]


def byte_to_rgb(b):
    r = b & 7
    g = (b >> 3) & 7
    bl = (b >> 6) & 3
    return (r * 255 // 7, g * 255 // 7, bl * 255 // 3)


COLTAB_RGB = [byte_to_rgb(b) for b in COLTAB]

# idx: 0 black(transparent) 1 laser(cycled) 2 red 3 green 4 yellow 5 blue 6 gray 7 brown
# 8 purple 9 white A bomb(cycled) B mono C logo cycler D/E/F tie cycled
_BASE = [0x00, 0x00, 0x07, 0x28, 0x2F, 0x81, 0xA4, 0x15, 0xC7, 0xFF, 0x00, 0xFF, 0x00, 0x00, 0x00, 0x00]
PALETTE = [byte_to_rgb(b) for b in _BASE]
PALETTE[0xA] = (255, 255, 0)
PALETTE[0xB] = (255, 255, 255)
PALETTE[0xC] = (255, 182, 0)
PALETTE[0xD] = (255, 0, 0)
PALETTE[0xE] = (255, 182, 0)
PALETTE[0xF] = (255, 255, 255)

BLACK = PALETTE[0]
WHITE = PALETTE[9]
BLUE = PALETTE[5]
BROWN = PALETTE[7]

_TIE = [(255, 0, 0), (255, 182, 0), (255, 255, 255), (0, 182, 0), (0, 182, 255), (255, 0, 255)]
_BOMB = [(255, 255, 0), (255, 0, 0), (255, 255, 255), (255, 182, 0)]


def laser_color(tick, offset=0):
    return COLTAB_RGB[(tick + offset) % len(COLTAB_RGB)]


def frame_palette(tick):
    """16-entry palette for this frame with the software-cycled entries updated."""
    p = list(PALETTE)
    p[1] = laser_color(tick)
    p[0xA] = _BOMB[(tick // 3) % len(_BOMB)]
    p[0xC] = laser_color(tick // 2, 5)
    n = len(_TIE)
    p[0xD] = _TIE[(tick // 6) % n]
    p[0xE] = _TIE[(tick // 6 + 1) % n]
    p[0xF] = _TIE[(tick // 6 + 2) % n]
    return p
