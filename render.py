"""Renderer: draws a Game (or duck-typed stub, see Game API in ARCHITECTURE.md) onto a 304x256 surface."""
import random
import pygame
import assets, effects
from effects import W, H, PLAY_TOP, X_OFF, WORLD, wrap_dx
from font import draw_text, text_width
from palette import frame_palette, BLUE, BROWN, WHITE, PALETTE

SCAN_X, SCAN_Y, SCAN_W, SCAN_H = 88, 8, 128, 32
SCAN_DIV = 16            # world px per scanner px (2048/128)
VIEW_W = 292
TERRAIN_Y0, TERRAIN_Y1 = 160, 232


class Renderer:
    def __init__(self):
        self.tick = 0
        self.stars = effects.Starfield()
        self.rng = random.Random(7)

    # ------------------------------------------------------------------
    def draw(self, surface, game):
        self.tick += 1
        t = self.tick
        pal = frame_palette(t)
        cam = float(getattr(game, "cam_x", 0.0))
        bg = effects.flash_color(getattr(game, "flash", 0) or 0, t) or (0, 0, 0)
        surface.fill(bg)
        flashing = bg != (0, 0, 0)

        state = getattr(game, "state", "play")
        if not flashing:
            self.stars.draw(surface, cam, t)
        self._terrain(surface, game, cam)
        self._entities(surface, game, cam, pal)
        player = getattr(game, "player", None)
        if player is not None:
            self._player(surface, game, player, cam, pal)
        for ls in getattr(game, "lasers", ()):
            effects.draw_laser(surface, ls, cam, t)
        effects.draw_particles(surface, getattr(game, "particles", ()), cam, pal)
        self._popups(surface, game, cam, pal)
        self._hud(surface, game, cam, pal)
        self._messages(surface, game, state)
        return surface

    # ------------------------------------------------------------------
    def _sx(self, x, cam):
        return wrap_dx(x, cam) + X_OFF

    def _terrain(self, surface, game, cam):
        terr = getattr(game, "terrain", None)
        if terr is None or not getattr(terr, "alive", True):
            return
        pts = []
        ci = int(cam)
        for sx in range(0, W):
            wx = (ci + sx - X_OFF) % WORLD
            pts.append((sx, int(terr.height_at(wx))))
        if len(pts) > 1:
            pygame.draw.lines(surface, BROWN, False, pts)

    def _entities(self, surface, game, cam, pal):
        t = self.tick
        clip = pygame.Rect(0, PLAY_TOP, W, H - PLAY_TOP)
        surface.set_clip(clip)
        for e in getattr(game, "entities", ()):
            if not getattr(e, "alive", True):
                continue
            kind = getattr(e, "kind", "")
            sx = self._sx(e.x, cam)
            if sx < -24 or sx > W + 24:
                continue
            name = assets.sprite_name(kind, getattr(e, "frame", 0), getattr(e, "facing", 1))
            if name is None:
                surface.fill(WHITE, (int(sx) - 2, int(e.y) - 2, 4, 4))
                continue
            spr = assets.sprite(name)
            w, h = spr.get_size()
            assets.blit_sprite(surface, spr, (int(sx - w / 2), int(e.y - h / 2)), pal)
        surface.set_clip(None)

    def _player(self, surface, game, p, cam, pal):
        if not getattr(p, "alive", True):
            return
        sx = self._sx(p.x, cam)
        sy = int(p.y)
        name = assets.sprite_name("player", 0, getattr(p, "facing", 1))
        mat = getattr(p, "materialize", None)
        if mat is not None and mat < 1.0:
            effects.draw_materialize(surface, name, sx, sy, mat, pal, random.Random(self.tick))
            return
        spr = assets.sprite(name)
        w, h = spr.get_size()
        if getattr(p, "thrusting", False):
            effects.draw_flame(surface, sx, sy + 1, getattr(p, "facing", 1), self.tick, self.rng)
        assets.blit_sprite(surface, spr, (int(sx - w / 2), int(sy - h / 2)), pal)

    def _popups(self, surface, game, cam, pal):
        for pu in getattr(game, "popups", ()):
            sx = self._sx(pu.x, cam)
            nm = assets.POPUP.get(pu.value)
            if nm:
                spr = assets.sprite(nm)
                assets.blit_sprite(surface, spr, (int(sx - 6), int(pu.y - 3)), pal)
            else:
                draw_text(surface, str(pu.value), (sx, pu.y - 3), WHITE, center=True)

    # ------------------------------------------------------------------
    def _hud(self, surface, game, cam, pal):
        # separator line across the whole width, scanner box
        pygame.draw.line(surface, BLUE, (0, 40), (W - 1, 40))
        score = int(getattr(game, "score", 0))
        draw_text(surface, "%d" % score, (30, 28), (255, 255, 255))
        ships = max(0, int(getattr(game, "ships", 0)) - 1)
        mini = assets.sprite(assets.MINI_SHIP)
        for i in range(min(ships, 5)):
            assets.blit_sprite(surface, mini, (30 + i * 11, 19), pal)
        sb = assets.sprite(assets.SMART_BOMB_ICON)
        for i in range(min(int(getattr(game, "smart_bombs", 0)), 3)):
            assets.blit_sprite(surface, sb, (30 + i * 8, 11), pal)
        self._scanner(surface, game, cam, pal)

    def _scan_pos(self, x, y, cam):
        u = (x - cam - 146 + WORLD // 2) % WORLD
        sx = SCAN_X + int(u / SCAN_DIV)
        sy = SCAN_Y + 1 + int((min(max(y, PLAY_TOP), 240) - PLAY_TOP) * (SCAN_H - 3) / 198)
        return sx, sy

    def _scanner(self, surface, game, cam, pal):
        x0, y0, w, h = SCAN_X, SCAN_Y, SCAN_W, SCAN_H
        r = pygame.Rect(x0 - 1, y0, w + 2, h + 1)
        pygame.draw.rect(surface, BLUE, r, 1)
        # view brackets at top centre
        vl = x0 + int((WORLD // 2 - 146) / SCAN_DIV)
        vr = vl + int(VIEW_W / SCAN_DIV)
        for bx in (vl, vr):
            surface.fill(WHITE, (bx, y0 + 1, 1, 3))
            surface.fill(WHITE, (bx, y0 + h - 3, 1, 3))
        surface.fill(WHITE, (vl, y0 + 1, 3, 1))
        surface.fill(WHITE, (vr - 2, y0 + 1, 3, 1))
        # mini terrain
        terr = getattr(game, "terrain", None)
        if terr is not None and getattr(terr, "alive", True):
            for i in range(w):
                wx = (cam + 146 - WORLD // 2 + i * SCAN_DIV) % WORLD
                ht = terr.height_at(wx)
                sy = y0 + 1 + int((min(max(ht, TERRAIN_Y0 - 20), TERRAIN_Y1 + 8) - PLAY_TOP) * (h - 3) / 198)
                surface.set_at((x0 + i, min(sy, y0 + h - 1)), BROWN)
        # entities
        for e in getattr(game, "entities", ()):
            if not getattr(e, "alive", True):
                continue
            c = getattr(e, "scanner_color", 0)
            if not c:
                continue
            sx, sy = self._scan_pos(e.x, e.y, cam)
            if x0 <= sx < x0 + w:
                surface.fill(pal[c & 15], (sx, sy, 2, 2))
        p = getattr(game, "player", None)
        if p is not None and getattr(p, "alive", True):
            sx, sy = self._scan_pos(p.x, p.y, cam)
            surface.fill(WHITE, (sx, sy, 3, 2))

    def _messages(self, surface, game, state):
        cx = W // 2
        if state == "game_over":
            draw_text(surface, "GAME OVER", (cx, 120), (255, 255, 255), center=True)
        elif state == "wave_bonus":
            info = getattr(game, "bonus_info", None)
            if info:
                draw_text(surface, "ATTACK WAVE %d" % info.get("wave", 0), (cx, 90), (255, 255, 255), center=True)
                draw_text(surface, "COMPLETED", (cx, 102), (255, 255, 255), center=True)
                draw_text(surface, "BONUS X %d" % info.get("points", 0), (cx, 118), (255, 182, 0), center=True)
                n = int(info.get("humanoids", 0))
                spr = assets.sprite("ASTD10")
                pal = frame_palette(self.tick)
                for i in range(min(n, 10)):
                    assets.blit_sprite(surface, spr, (cx - n * 3 + i * 6 - 2, 132), pal)
        elif state == "wave_intro":
            draw_text(surface, "ATTACK WAVE %d" % int(getattr(game, "wave", 1)), (cx, 100),
                      (255, 255, 255), center=True)
