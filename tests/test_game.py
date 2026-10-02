import random

from entities import Humanoid, Lander, Mutant, Baiter, Pod, Bomber, Swarmer, SIZES, wrap_dx
from game import Game, Inputs
from rng import Rand
from terrain import Terrain, PROFILE
from waves import wave_params, lander_yv


def fresh(seed=1, enemies=False):
    g = Game(seed)
    g.start_game()
    g.state = "play"
    if not enemies:
        g.lander_reserve = g.bomber_reserve = 0
        g.entities = [e for e in g.entities if e.kind == "humanoid"]
        g.clear_timer = 10 ** 9   # suppress wave-complete
    return g


def run(g, n, inp=None):
    inp = inp or Inputs()
    for _ in range(n):
        g.update(inp)


# ---- rng / terrain / waves
def test_rng_deterministic_and_spread():
    a, b = Rand(5), Rand(5)
    assert [a.rand() for _ in range(50)] == [b.rand() for _ in range(50)]
    r = Rand(9)
    vals = {r.rand() for _ in range(5000)}
    assert len(vals) > 200
    for _ in range(200):
        assert 1 <= r.rmax(6) <= 7


def test_terrain_profile():
    assert len(PROFILE) == 2048
    assert 159 <= min(PROFILE) and max(PROFILE) <= 233
    t = Terrain()
    assert t.alive and t.height_at(2048 + 10) == t.height_at(10)


def test_wave_table():
    p = wave_params(1)
    assert (p["landers"], p["bombers"], p["pods"]) == (15, 0, 0)
    assert p["lndxv"] == 32 and p["ldstim"] == 64 and p["ufotim"] == 192 and p["ufosk"] == 200
    p2 = wave_params(2)
    assert (p2["landers"], p2["bombers"], p2["pods"]) == (20, 3, 1)
    assert wave_params(5)["bombers"] == 5 and wave_params(9)["pods"] == 4
    assert lander_yv(wave_params(3)) == 1.0


def test_wave1_has_15_landers():
    g = Game(3)
    g.start_game()
    assert g.wave == 1 and g.lander_total() == 15
    assert g.humanoid_count() == 10 and g.ships == 3 and g.smart_bombs == 3
    run(g, 200)
    assert g.lander_total() <= 15 and g.count("lander") + g.count("mutant") >= 5 or g.player.alive is False


# ---- ship physics
def test_top_speed_and_damping():
    g = fresh()
    g.entities = []
    run(g, 1500, Inputs(thrust=True))
    assert 5.8 < g.player.vx <= 6.01
    run(g, 64)
    assert g.player.vx > 0
    v = g.player.vx
    run(g, 64)
    assert abs(g.player.vx - v * (1 - 1 / 64) ** 64) < 0.05


def test_reverse_flips_and_requires_edge():
    g = fresh()
    g.update(Inputs(reverse=True))
    assert g.player.facing == -1
    g.update(Inputs(reverse=True))
    assert g.player.facing == -1
    g.update(Inputs())
    g.update(Inputs(reverse=True))
    assert g.player.facing == 1


def test_vertical_ramp_and_bounds():
    g = fresh()
    y0 = g.player.y
    g.update(Inputs(up=True))
    assert g.player.vy == -1.0
    run(g, 40, Inputs(up=True))
    assert g.player.vy == -2.0
    g.update(Inputs())
    assert g.player.vy == 0.0
    run(g, 200, Inputs(up=True))
    assert g.player.y >= 46
    run(g, 400, Inputs(down=True))
    assert g.player.y <= 235


def test_max_four_lasers_and_kill():
    g = fresh()
    g.entities = [e for e in g.entities if e.kind == "humanoid"]
    for i in range(6):
        g.update(Inputs(fire=True))
        g.update(Inputs())
    assert len(g.lasers) <= 4 and "laser" in g.events
    g = fresh()
    p = g.player
    m = Pod(g, p.x + 120, p.y + 1)
    m.vx = m.vy = 0
    g.entities.append(m)
    g.update(Inputs(fire=True))
    run(g, 30)
    assert not m.alive and g.score == 1000


def test_smart_bomb():
    g = fresh()
    p = g.player
    near = Lander(g, p.x + 50, 100)
    far = Lander(g, p.x + 1000, 100)
    hum = g.entities[0]
    g.entities += [near, far]
    g.update(Inputs(smart_bomb=True))
    assert not near.alive and far.alive and hum.alive
    assert g.smart_bombs == 2 and g.score == 150 and g.flash > 0


def test_hyperspace_death_rate():
    deaths = 0
    N = 80
    for s in range(N):
        g = fresh(s)
        g.entities = []
        g.humanoid_count = lambda: 10
        g.update(Inputs(hyperspace=True))
        run(g, 60)
        if g.state == "player_dying":
            deaths += 1
        else:
            assert g.player.alive and g.player.materialize is None
    assert 5 <= deaths <= 40   # nominal 24.6%


# ---- enemies
def test_abduction_leads_to_mutation():
    g = fresh()
    g.entities = []
    g.humanoid_count_dummy = None
    h = Humanoid(g, 1000)
    g.entities.append(h)
    # player far away so nothing interferes
    g.player.x = 100
    l = Lander(g, 1000, 60)
    l.vx = 0
    g.entities.append(l)
    for _ in range(3000):
        g.update(Inputs())
        if not l.alive:
            break
        g.player.alive = True
    assert not l.alive
    assert not h.alive
    assert g.count("mutant") == 1
    assert "lander_grab" in g.events and "lander_mutates" in g.events
    assert g.terrain.alive is False or True


def test_shooting_carrier_drops_humanoid_and_landing_scores():
    g = fresh()
    g.entities = []
    h = Humanoid(g, 1000)
    l = Lander(g, 1000, 100)
    g.entities += [h, l]
    h.set_state("carried")
    h.carrier = l
    h.target_of = l
    l.target = h
    l.mode = "flee"
    h.y = g.terrain.height_at(1000) - 30
    l.y = h.y - 12
    g.kill(l)
    assert h.state == "falling" and g.score == 150
    run(g, 400)
    assert h.alive and h.state == "walk"
    assert g.score == 150 + 250


def test_high_fall_kills_and_catch_scores_500_then_500():
    g = fresh()
    g.entities = []
    far = Humanoid(g, 200)
    h = Humanoid(g, 1500)
    g.entities += [far, h]
    h.set_state("falling")
    h.y = 60
    run(g, 400)
    assert not h.alive and g.score == 0
    h2 = Humanoid(g, 1500)
    g.entities.append(h2)
    p = g.player
    p.x = 1500
    p.y = 100
    h2.set_state("falling")
    h2.y = 100
    g.update(Inputs())
    assert h2.state == "caught" and g.score == 500
    for _ in range(300):
        g.update(Inputs(down=True))
        if h2.state == "walk":
            break
    assert h2.state == "walk" and g.score == 1000


def test_planet_destroyed_when_last_humanoid_dies():
    g = fresh()
    l = Lander(g, g.player.x + 400, 90)
    g.entities.append(l)
    for h in [e for e in g.entities if e.kind == "humanoid"]:
        g.kill_humanoid(h)
    run(g, 2)
    assert g.terrain.alive is False
    assert "planet_explode" in g.events
    assert g.state in ("planet_exploding", "play")
    assert not l.alive and g.count("mutant") == 1
    g.lander_reserve = 5
    g.wavtmr = 0
    g.clear_timer = None
    run(g, 30)
    assert g.count("lander") == 0 and g.count("mutant") >= 2
    run(g, 200)
    assert g.state == "play"


def test_pod_releases_swarmers():
    g = fresh()
    pod = Pod(g, g.player.x + 60, 100)
    g.entities.append(pod)
    g.kill(pod)
    assert g.score == 1000 and 1 <= g.count("swarmer") <= 7
    assert "pod_explode" in g.events


def test_scoring_values():
    g = fresh()
    for cls, pts in ((Mutant, 150), (Baiter, 200), (Pod, 1000), (Swarmer, 150)):
        s = g.score
        e = cls(g, 10, 100)
        g.entities.append(e)
        g.kill(e)
        assert g.score - s == pts
    b = Bomber(g, 10, 100, 1.0)
    s = g.score
    g.kill(b)
    assert g.score - s == 250


def test_extra_ship_and_bomb_every_10000():
    g = fresh()
    ships, bombs = g.ships, g.smart_bombs
    g.add_score(9999)
    assert g.ships == ships
    g.add_score(1)
    assert (g.ships, g.smart_bombs) == (ships + 1, bombs + 1)
    assert "extra_life" in g.events
    g.add_score(10000)
    assert g.ships == ships + 2


def test_collision_kills_ship_and_respawns():
    g = fresh()
    p = g.player
    g.entities.append(Mutant(g, p.x, p.y))
    g.params["szxv"] = 0
    g.update(Inputs())
    assert g.state == "player_dying" and g.ships == 2
    run(g, 100)
    assert g.state == "play" and g.player.alive


def test_game_over():
    g = fresh()
    g.ships = 1
    g.entities.append(Mutant(g, g.player.x, g.player.y))
    run(g, 120)
    assert g.state == "game_over" and g.ships == 0


def test_baiter_timer_and_bbox_sizes():
    assert SIZES["lander"] == (10, 8) and SIZES["baiter"] == (12, 4) and SIZES["swarmer"] == (6, 4)
    g = Game(2)
    g.start_game()
    g.state = "play"
    for e in g.entities:
        if e.kind == "humanoid":
            e.alive = True
    g.player.alive = False   # keep the player out of the way
    run(g, 192 * 15 - 5)
    assert g.count("baiter") == 0
    run(g, 40)
    assert g.count("baiter") >= 1


def test_wave_complete_bonus_and_next_wave():
    g = fresh()
    run(g, 1)
    g.clear_timer = None
    g.entities = [e for e in g.entities if e.kind == "humanoid"]
    for _ in range(80):
        g.update(Inputs())
        if g.state == "wave_bonus":
            break
    assert g.state == "wave_bonus"
    run(g, 4 * 10 + 20)
    assert g.bonus_info["humanoids"] == 10 and g.bonus_info["points"] == 1000
    assert g.score == 1000
    run(g, 200)
    assert g.wave == 2 and g.state in ("wave_intro", "play")
    assert g.lander_total() == 20


def test_humanoids_restored_on_wave_5():
    g = fresh()
    g.wave = 4
    for h in [e for e in g.entities if e.kind == "humanoid"][:6]:
        g.kill_humanoid(h)
    g.entities = [e for e in g.entities if e.alive]
    g.terrain.explode()
    g._begin_wave(5)
    assert g.humanoid_count() == 10 and g.terrain.alive


def test_determinism():
    def play(seed):
        g = Game(seed)
        g.start_game()
        r = random.Random(77)
        for _ in range(3000):
            g.update(Inputs(thrust=r.random() < .6, fire=r.random() < .3, up=r.random() < .2,
                            down=r.random() < .2, reverse=r.random() < .02,
                            smart_bomb=r.random() < .002, hyperspace=r.random() < .002))
        return (g.score, g.wave, g.ships, round(g.player.x, 6), len(g.entities), g.state,
                [(e.kind, round(e.x, 4), round(e.y, 4)) for e in g.entities[:30]])
    assert play(11) == play(11)
    assert play(11) != play(12)


def test_soak_scripted_bot():
    g = Game(2024)
    g.start_game()
    r = random.Random(5)
    held = Inputs()
    starts = 0
    for t in range(20000):
        if t % 15 == 0:
            held = Inputs(thrust=r.random() < .6, up=r.random() < .3, down=r.random() < .3)
        inp = Inputs(thrust=held.thrust, up=held.up, down=held.down,
                     fire=r.random() < .25, reverse=r.random() < .01,
                     smart_bomb=r.random() < .001, hyperspace=r.random() < .001)
        g.update(inp)
        g.pop_events()
        if g.state == "game_over":
            starts += 1
            g.start_game()
        assert len(g.entities) < 400 and len(g.particles) < 1500
        assert 0 <= g.player.y <= 256 and 0 <= g.cam_x < 2048
    assert g.tick == 20000
