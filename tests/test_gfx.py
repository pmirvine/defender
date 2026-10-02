import os
import tempfile
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import sys
sys.path.insert(0, os.path.dirname(__file__))
import pygame
import pytest
from fakegame import make_game
import assets, font, palette
from render import Renderer

OUT = os.path.join(tempfile.gettempdir(), "defender_frame.png")


@pytest.fixture(scope="module", autouse=True)
def _pg():
    pygame.init()
    pygame.display.set_mode((10, 10))
    yield


def test_sprites():
    for n in ["LND10", "LND20", "LND30", "UFOD10", "TIED40", "SCZD10", "PRBD10", "SWMD10", "ASTD40", "BMBD10", "PLD10", "PLD20", "PLAM0", "SBD10", "C25D10", "C5D10", "TERX0"]:
        assert assets.sprite(n).get_width() > 0
    assert assets.sprite("LND10").get_size() == (10, 8)
    assert assets.sprite("PLD10").get_size() == (16, 6)
    for k in "lander mutant baiter bomber pod swarmer humanoid enemy_shot mine".split():
        for f in range(4):
            assert assets.sprite_for(k, f) is not None


def test_font_and_palette():
    s = font.render_text("SCORE 0123456789 :!,.?", (255, 0, 0))
    assert s.get_height() == 8 and s.get_width() > 50
    assert len(palette.PALETTE) == 16 and len(palette.frame_palette(5)) == 16


def test_render_frame_and_states():
    surf = pygame.Surface((304, 256))
    r = Renderer()
    g = make_game()
    r.draw(surf, g)
    for _ in range(5):
        r.draw(surf, g)
    pygame.image.save(surf, OUT)
    g.flash = 5; r.draw(surf, g); g.flash = 0
    g.player.materialize = 0.4; r.draw(surf, g)
    g.cam_x = 2000.0; r.draw(surf, g)
    for st in ("game_over", "wave_bonus", "wave_intro", "attract", "planet_exploding"):
        g.state = st
        g.bonus_info = {"wave": 1, "humanoids": 5, "points": 2500}
        r.draw(surf, g)
    g.terrain.alive = False
    r.draw(surf, g)


def test_render_minimal_stub():
    from types import SimpleNamespace as NS
    Renderer().draw(pygame.Surface((304, 256)), NS())
