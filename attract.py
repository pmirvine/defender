"""Attract mode: title page -> hall of fame -> instructions."""
import random

import pygame

import assets
import font
import logos
import palette

W, H = 304, 256
CX = 152  # centre of the visible 292px window
PAGE_TICKS = (620, 480, 600)
YELLOW = logos.YELLOW


def spaced_text(surf, text, cx, y, color, gap=2, upto=None):
    """Draw text centred on cx with extra letter spacing (the title page uses wide tracking)."""
    widths = [font.text_width(c) + gap for c in text]
    x = cx - (sum(widths) - gap) // 2
    for i, c in enumerate(text):
        if upto is not None and i >= upto:
            break
        font.draw_text(surf, c, (x, y), color)
        x += widths[i]


_TINY = {  # 3x5 glyphs for the (c) and (p) marks
    "C": ("111", "100", "100", "100", "111"),
    "P": ("110", "101", "110", "100", "100"),
}


def circled(surf, ch, x, y, color):
    """Draw a 9x9 circled letter with its top-left corner at (x, y)."""
    pygame.draw.circle(surf, color, (x + 4, y + 4), 4, 1)
    for ry, row in enumerate(_TINY[ch]):
        for rx, bit in enumerate(row):
            if bit == "1":
                surf.set_at((x + 2 + rx, y + 2 + ry), color)


def copyright_line(surf, cx, y, color):
    text_l, text_r = "COPYRIGHT", "1980"
    wl, wr = font.text_width(text_l), font.text_width(text_r)
    total = wl + 3 + 9 + 1 + 9 + 4 + wr
    x = cx - total // 2
    font.draw_text(surf, text_l, (x, y), color)
    x += wl + 3
    circled(surf, "C", x, y - 1, color)
    circled(surf, "P", x + 10, y - 1, color)
    font.draw_text(surf, text_r, (x + 23, y), color)


class Attract:
    def __init__(self, scores):
        self.scores = scores
        self.tick = 0
        self._logo_px = None

    def update(self):
        self.tick += 1

    @property
    def page(self):
        t = self.tick % sum(PAGE_TICKS)
        for i, n in enumerate(PAGE_TICKS):
            if t < n:
                return i, t
            t -= n
        return 0, 0

    def draw(self, surf, credits=0):
        surf.fill((0, 0, 0))
        page, t = self.page
        pal = palette.frame_palette(self.tick)
        [self._title, self._hall, self._instr][page](surf, t, pal)
        msg = "CREDITS %d" % credits if credits else "PRESS 1 OR ENTER TO START"
        if credits or (self.tick // 30) % 2 == 0:
            font.draw_text(surf, msg, (CX, 240), (255, 255, 255), center=True)
        font.draw_text(surf, "F2 CONTROLS", (8, 246), (110, 110, 110))

    # -- pages ------------------------------------------------------------
    def _title(self, surf, t, pal):
        # Williams script logo, revealed left to right
        logo = logos.williams_logo()
        lw, lh = logo.get_size()
        reveal = min(lw, int(lw * t / 70))
        if reveal > 0:
            surf.blit(logo, (CX - lw // 2 - 2, 70 - lh // 2), area=(0, 0, reveal, lh))
        if t > 70:  # registered mark
            pygame.draw.circle(surf, logos.RED, (CX + lw // 2 + 3, 70 - lh // 2 + 2), 3, 1)
            surf.set_at((CX + lw // 2 + 3, 70 - lh // 2 + 2), logos.RED)
        if t > 90:
            spaced_text(surf, "ELECTRONICS INC.", CX, 90, YELLOW, upto=(t - 90) // 3 + 1)
        if t > 170:
            spaced_text(surf, "PRESENTS", CX, 109, YELLOW, upto=(t - 170) // 3 + 1)
        if t > 220:
            self._defender(surf, min(1.0, (t - 220) / 110))
        if t > 360:
            copyright_line(surf, CX, 208, YELLOW)

    def _defender(self, surf, k):
        """The DEFENDER logo forms from pixels scattered across the screen."""
        logo = logos.defender_logo()
        rect = logo.get_rect(center=(CX, 156))
        if k >= 1.0:
            surf.blit(logo, rect)
            return
        if self._logo_px is None:
            r = random.Random(7)
            w, h = logo.get_size()
            self._logo_px = [
                (x, y, logo.get_at((x, y))[:3], r.randint(-150, 150), r.randint(-110, 110))
                for y in range(h) for x in range(w) if logo.get_at((x, y))[3] > 0
            ]
        inv = 1 - k
        for x, y, c, dx, dy in self._logo_px:
            px, py = rect.x + x + int(dx * inv), rect.y + y + int(dy * inv)
            if 0 <= px < W and 0 <= py < H:
                surf.set_at((px, py), c)

    def _hall(self, surf, t, pal):
        font.draw_text(surf, "HALL OF FAME", (CX, 50), (255, 255, 255), center=True, scale=2)
        font.draw_text(surf, "TODAYS GREATEST", (CX, 84), (255, 182, 0), center=True)
        for i, (name, sc) in enumerate(self.scores[:8]):
            y = 104 + i * 14
            font.draw_text(surf, "%d  %s" % (i + 1, name), (80, y), (0, 182, 0))
            font.draw_text(surf, "%6d" % sc, (180, y), (0, 182, 0))

    def _instr(self, surf, t, pal):
        font.draw_text(surf, "SCANNER", (CX, 20), (255, 255, 255), center=True)
        rows = [("lander", 0, "LANDER"), ("mutant", 0, "MUTANT"), ("baiter", 0, "BAITER"),
                ("bomber", 0, "BOMBER"), ("pod", 0, "POD"), ("swarmer", 0, "SWARMER"),
                ("humanoid", 0, "HUMANOID")]
        show = min(len(rows), 1 + t // 50)
        for i, (kind, fr, label) in enumerate(rows[:show]):
            y = 50 + i * 24
            s = assets.sprite_for(kind, fr, 1)
            assets.blit_sprite(surf, s, (90, y), pal)
            font.draw_text(surf, label, (130, y), (255, 255, 255))
        font.draw_text(surf, "SHOOT THEM ALL  PROTECT THE HUMANOIDS", (CX, 226),
                       (0, 182, 0), center=True)
