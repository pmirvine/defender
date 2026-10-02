"""Duck-typed Game stub following the API in ARCHITECTURE.md (for renderer tests)."""
import math
from types import SimpleNamespace as NS


class FakeTerrain:
    alive = True

    def height_at(self, x):
        return 200 + 25 * math.sin(x / 90.0) + 8 * math.sin(x / 23.0)


def make_game():
    g = NS()
    g.state = "play"
    g.score = 12450
    g.ships = 3
    g.smart_bombs = 3
    g.wave = 1
    g.cam_x = 400.0
    g.player = NS(x=550.0, y=130.0, facing=1, vx=2.0, thrusting=True, alive=True, materialize=None)
    g.terrain = FakeTerrain()
    ents = []

    def E(kind, x, y, frame=0, col=2):
        ents.append(NS(kind=kind, x=x, y=y, frame=frame, facing=1, alive=True, scanner_color=col))
    E("lander", 600, 90, 0, 3); E("lander", 700, 150, 1, 3); E("mutant", 480, 100, 0, 8)
    E("baiter", 650, 60, 1, 4); E("bomber", 520, 170, 2, 2); E("pod", 760, 110, 0, 8)
    E("swarmer", 570, 80, 0, 2); E("humanoid", 520, 228, 1, 4); E("humanoid", 900, 225, 2, 4)
    E("enemy_shot", 620, 120, 0, 9); E("mine", 540, 190, 0, 10)
    E("humanoid", 1900, 225, 0, 4)
    g.entities = ents
    g.lasers = [NS(x0=560.0, x1=720.0, y=133.0, age=3)]
    g.particles = [NS(x=600 + i * 2, y=60 + (i * 7) % 20, color=2 + i % 8) for i in range(30)]
    g.popups = [NS(x=700.0, y=140.0, value=250, ttl=30), NS(x=480.0, y=170.0, value=500, ttl=30)]
    g.flash = 0
    g.events = []
    g.bonus_info = None
    return g
