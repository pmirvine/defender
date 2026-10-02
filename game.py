"""Game state machine, player physics, collisions, scoring. Pure logic, deterministic per seed."""
from dataclasses import dataclass

from entities import (
    ENEMY_KINDS, EXPLOSION_COLORS, SCORES, SHOT_KINDS, WORLD, YMAX, YMIN,
    Baiter, Bomber, EnemyShot, Humanoid, Lander, Laser, Mine, Mutant, Particle,
    Player, Pod, Popup, Swarmer, sgn, wrap_dx,
)
from rng import Rand
from terrain import Terrain
from waves import intra_step, wave_params

SCREEN_W = 292
SHIP_W, SHIP_H = 16, 6
SHIP_REST_RIGHT = 66.0
SHIP_REST_LEFT = SCREEN_W - 66.0
INTRO_TICKS = 60
HOLD_TICKS = 128
REPLAY_SCORE = 10000
MAX_SHOTS = 20
PX_COLORS = [9, 9, 4, 4, 2, 2, 7, 7]


@dataclass
class Inputs:
    thrust: bool = False
    reverse: bool = False
    fire: bool = False
    smart_bomb: bool = False
    hyperspace: bool = False
    up: bool = False
    down: bool = False
    start1: bool = False
    coin: bool = False


class Game:
    def __init__(self, rng_seed=None, highscores=None):
        self.rng = Rand(rng_seed)
        self.highscores = highscores
        self.state = "attract"
        self.score = 0
        self.ships = 0
        self.smart_bombs = 0
        self.wave = 0
        self.cam_x = 0.0
        self.player = Player()
        self.entities = []
        self.lasers = []
        self.particles = []
        self.popups = []
        self.terrain = Terrain()
        self.flash = 0
        self.events = []
        self.bonus_info = None
        self.params = wave_params(1)
        self.tick = 0
        self.next_replay = REPLAY_SCORE
        self.lander_reserve = 0
        self.bomber_reserve = 0
        self.timer = 0           # generic state timer
        self.planet_timer = 0
        self.hyper_t = None
        self.game_over_ticks = 0
        self._prev = Inputs()
        self._target_ptr = 0
        self._bomber_dir = 1
        self._reset_exec()

    # ------------------------------------------------------------ public
    def pop_events(self):
        ev, self.events = self.events, []
        return ev

    def start_game(self):
        self.score = 0
        self.ships = 3
        self.smart_bombs = 3
        self.next_replay = REPLAY_SCORE
        self.entities = []
        self.lasers = []
        self.particles = []
        self.popups = []
        self.terrain = Terrain()
        self.player = Player()
        self.cam_x = 0.0
        self.player.x = self.cam_x + self.player.sx
        self.flash = 0
        self.hyper_t = None
        self.planet_timer = 0
        self.game_over_ticks = 0
        self.bonus_info = None
        for i in range(10):
            base = (i % 4) * 512
            self.entities.append(Humanoid(self, base + self.rng.rand16() % 512))
        self.events.append("start")
        self._begin_wave(1)

    # ------------------------------------------------------------ queries
    def onscreen(self, e, margin=0):
        rel = wrap_dx(e.x, self.cam_x)
        return -e.w / 2 - margin < rel < SCREEN_W + e.w / 2 + margin

    def count(self, *kinds):
        return sum(1 for e in self.entities if e.alive and e.kind in kinds)

    def humanoid_count(self):
        return self.count("humanoid")

    def lander_total(self):
        return self.lander_reserve + self.count("lander")

    def enemies_remaining(self):
        return (self.lander_reserve + self.bomber_reserve
                + self.count("lander", "mutant", "bomber", "pod", "swarmer"))

    # ------------------------------------------------------------ waves
    def _reset_exec(self):
        self.pass_count = 0
        self.exec_tick = 0
        self.wavtmr = 1
        self.ufotmr = 0
        self.clear_timer = None

    def _begin_wave(self, n):
        self.wave = n
        p = self.params = wave_params(n)
        if n > 1 and n % 5 == 0:
            self.entities = [e for e in self.entities if e.kind != "humanoid"]
            for i in range(10):
                base = (i % 4) * 512
                self.entities.append(Humanoid(self, base + self.rng.rand16() % 512))
            self.terrain.restore()
        self._reset_exec()
        self.ufotmr = p["ufotim"]
        self.lander_reserve = p["landers"]
        self.bomber_reserve = p["bombers"]
        for _ in range(p["pods"]):
            x = self.cam_x + (16 + self.rng.rand() % 64) * 8
            self.entities.append(Pod(self, x, YMIN + (self.rng.rand() >> 1)))
        for _ in range(p["mutants"]):
            self._spawn_mutant()
        for _ in range(p["swarmers"]):
            self.entities.append(Swarmer(self, self.player.x + self.rng.randint(-100, 100),
                                         self.rng.randint(60, 180)))
        self.state = "wave_intro"
        self.timer = INTRO_TICKS
        self.bonus_info = None
        self.events.append("wave_start")

    def _spawn_mutant(self):
        r = self.rng
        x = self.player.x + 300 + r.rand16() % (WORLD - 600)
        m = Mutant(self, x, YMIN + (r.rand() >> 1))
        self.entities.append(m)
        return m

    def _exec(self):
        """GEXEC: runs every 15 ticks."""
        p = self.params
        r = self.rng
        self.pass_count += 1
        if self.pass_count % 40 == 0:
            intra_step(p)
        # lander squads
        alive_l = self.count("lander", "mutant")
        self.wavtmr -= 1
        if self.wavtmr <= 0 or alive_l == 0:
            self.wavtmr = p["wavtim"]
            if self.lander_reserve > 0 and alive_l < 8:
                n = min(p["wavsiz"], self.lander_reserve)
                for _ in range(n):
                    self.lander_reserve -= 1
                    if self.humanoid_count() == 0:
                        self._spawn_mutant()
                    else:
                        self.entities.append(Lander(self, r.rand16() * WORLD / 65536.0))
                self.events.append("appear")
        # bomber groups of up to 3
        if self.bomber_reserve > 0 and (self.count("bomber") == 0 or self.pass_count % 20 == 0):
            n = min(3, self.bomber_reserve)
            self.bomber_reserve -= n
            self._bomber_dir = -self._bomber_dir
            vx = self._bomber_dir * p["tiexv"] / 32.0
            for i in range(n):
                self.entities.append(Bomber(self, self.player.x + WORLD / 2 + i * 12, 80, vx))
            self.events.append("appear")
        # baiters
        a = self.enemies_remaining()
        self.ufotmr -= 1
        if a <= 3:
            self.ufotmr = min(self.ufotmr, p["ufotim"] // 4 + 1)
        elif a <= 8:
            self.ufotmr = min(self.ufotmr, p["ufotim"] // 2 + 1)
        if self.ufotmr <= 0:
            self.ufotmr = p["ufotim"] if a >= 4 else r.rmax(p["ufotim"] // 4)
            if self.count("baiter") < 12:
                x = self.cam_x + (r.rand16() & 0x1FFF) / 32.0
                self.entities.append(Baiter(self, x, YMIN + (r.rand() >> 1)))
                self.events.append("baiter_appear")

    def _start_bonus(self):
        self.entities = [e for e in self.entities
                         if e.kind == "humanoid"]   # genocide of baiters, shots, mines
        n = self.humanoid_count()
        per = 100 * min(self.wave, 5)
        self.bonus_info = {"wave": self.wave, "humanoids": 0, "points": 0,
                           "total": n, "per": per}
        self.state = "wave_bonus"
        self.timer = 0
        self.clear_timer = None

    # ------------------------------------------------------------ scoring / fx
    def add_score(self, pts):
        self.score += pts
        while self.score >= self.next_replay:
            self.next_replay += REPLAY_SCORE
            self.ships += 1
            self.smart_bombs += 1
            self.events.append("extra_life")

    def explode(self, x, y, color, n=14, speed=1.6, ttl=26):
        if len(self.particles) > 800:
            return
        r = self.rng
        for _ in range(n):
            ang_x = (r.rand() - 127.5) / 127.5
            ang_y = (r.rand() - 127.5) / 127.5
            s = speed * (0.3 + r.rand() / 255.0)
            self.particles.append(Particle(x, y, ang_x * s, ang_y * s, color, ttl - (r.rand() & 7)))

    # ------------------------------------------------------------ enemy helpers
    def pick_target(self, lander):
        hs = [e for e in self.entities if e.alive and e.kind == "humanoid"]
        if not hs:
            return None
        n = len(hs)
        for i in range(n):
            h = hs[(self._target_ptr + i) % n]
            if h.state == "walk" and (h.target_of is None or not h.target_of.alive):
                self._target_ptr = (self._target_ptr + i + 1) % n
                h.target_of = lander
                return h
        return None

    def mutate(self, lander):
        t = lander.target
        if t is not None and t.alive and t.state == "carried":
            t.alive = False
            self.explode(t.x, t.y, 4, 8)
        elif t is not None and t.target_of is lander:
            t.target_of = None
        lander.alive = False
        m = Mutant(self, lander.x, lander.y)
        self.entities.append(m)
        self.events.append("lander_mutates")

    def kill_humanoid(self, h):
        if not h.alive:
            return
        h.alive = False
        if h.state == "caught":
            self.player.carrying = None
        self.explode(h.x, h.y, 4, 10)
        self.events.append("humanoid_killed")

    def _release_lander_victim(self, lander):
        t = lander.target
        if t is None or not t.alive:
            return
        if t.state == "carried":
            t.set_state("falling")
            t.vy = 0.0
            t.carrier = None
            t.target_of = None
        elif t.target_of is lander:
            t.target_of = None

    def kill(self, e, score=True):
        """Destroy an enemy / shot, awarding points and effects."""
        if not e.alive:
            return
        e.alive = False
        kind = e.kind
        if kind == "lander":
            self._release_lander_victim(e)
        if score:
            self.add_score(SCORES[kind])
        if kind in SHOT_KINDS:
            self.explode(e.x, e.y, 4, 5, 0.8, 12)
            return
        self.explode(e.x, e.y, EXPLOSION_COLORS.get(kind, 2))
        if kind == "pod":
            self.events.append("pod_explode")
            room = 20 - self.count("swarmer")
            for _ in range(min(self.rng.rmax(6), max(room, 0))):
                self.entities.append(Swarmer(self, e.x, e.y))
        else:
            self.events.append("enemy_explode")

    def _clear_enemy_shots(self):
        self.entities = [e for e in self.entities if e.kind not in SHOT_KINDS]

    def aimed_shot(self, src):
        if not self.onscreen(src) or src.y <= YMIN:
            return
        if self.count(*SHOT_KINDS) >= MAX_SHOTS:
            return
        r = self.rng
        pl = self.player
        dx = wrap_dx(pl.x, src.x) + ((r.rand() & 0x1F) - 0x10) * 2
        vx = dx / 64.0
        if r.rand() > 120:
            vx += pl.vx
        dy = (pl.y - src.y) + ((r.rand() & 0x1F) - 0x10)
        vy = dy / 64.0
        self.entities.append(EnemyShot(src.x, src.y, vx, vy))
        self.events.append("enemy_shot")

    def swarmer_shot(self, src):
        if not self.onscreen(src) or src.y <= YMIN or self.count(*SHOT_KINDS) >= MAX_SHOTS:
            return
        dy = self.player.y - src.y
        self.entities.append(EnemyShot(src.x, src.y, 2 * src.vx, dy / 32.0))
        self.events.append("swarmer_shot")

    def drop_mine(self, bomber):
        if self.count(*SHOT_KINDS) >= MAX_SHOTS // 2:
            return
        self.entities.append(Mine(self, bomber.x, bomber.y))
        self.events.append("mine_drop")

    # ------------------------------------------------------------ main tick
    def update(self, inp):
        self.tick += 1
        st = self.state
        if st == "attract":
            self._fx()
            self._prev = inp
            return
        if st == "game_over":
            self.game_over_ticks += 1
            self._world_tick(inp, player_active=False, collide=False)
            self._prev = inp
            return
        if st == "wave_bonus":
            self._bonus_tick()
            self._fx()
            self._prev = inp
            return
        active = st in ("play", "wave_intro", "planet_exploding")
        self._world_tick(inp, player_active=active, collide=active)
        self._prev = inp

    def _fx(self):
        if self.flash > 0:
            self.flash -= 1
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.ttl -= 1
        self.particles = [p for p in self.particles if p.ttl > 0]
        for pu in self.popups:
            pu.ttl -= 1
        self.popups = [pu for pu in self.popups if pu.ttl > 0]

    def _world_tick(self, inp, player_active, collide):
        pl = self.player
        if player_active:
            self._update_player(inp)
        self._update_lasers()
        for e in list(self.entities):
            if e.alive:
                e.update(self)
        if collide and pl.alive and pl.materialize is None and self.state != "player_dying":
            self._collide_player()
        if self.state in ("play", "planet_exploding") or (self.state == "wave_intro"):
            self._planet_check()
        # exec
        if self.state in ("play", "planet_exploding", "player_dying") and self.clear_timer is None:
            self.exec_tick += 1
            if self.exec_tick >= 15:
                self.exec_tick = 0
                self._exec()
        self.entities = [e for e in self.entities if e.alive]
        self._state_logic()
        self._fx()

    def _state_logic(self):
        st = self.state
        if st == "wave_intro":
            self.timer -= 1
            if self.timer <= 0:
                self.state = "play"
        elif st == "planet_exploding":
            self._planet_fx()
            self.planet_timer -= 1
            if self.planet_timer <= 0:
                self.state = "play"
        elif st == "player_dying":
            self.timer -= 1
            if self.timer <= 0:
                if self.ships > 0:
                    self._respawn()
                else:
                    self.state = "game_over"
                    self.game_over_ticks = 0
        if self.state == "play" and self.player.alive:
            if self.clear_timer is None:
                if self.enemies_remaining() == 0:
                    self.clear_timer = 45
            else:
                self.clear_timer -= 1
                if self.clear_timer <= 0:
                    self._start_bonus()

    def _bonus_tick(self):
        self.timer += 1
        b = self.bonus_info
        if self.timer % 4 == 0 and b["humanoids"] < b["total"]:
            b["humanoids"] += 1
            b["points"] += b["per"]
            self.add_score(b["per"])
            self.events.append("bonus_tick")
        if b["humanoids"] >= b["total"] and self.timer >= 4 * b["total"] + HOLD_TICKS:
            self._begin_wave(self.wave + 1)

    # ------------------------------------------------------------ planet
    def _planet_check(self):
        if self.terrain.alive and self.humanoid_count() == 0:
            self.terrain.explode()
            self.events.append("planet_explode")
            self.planet_timer = 150
            if self.state in ("play", "wave_intro"):
                self.state = "planet_exploding"
            for e in list(self.entities):
                if e.alive and e.kind == "lander":
                    e.alive = False
                    self.entities.append(Mutant(self, e.x, e.y))
                    self.events.append("lander_mutates")

    def _planet_fx(self):
        if self.planet_timer % 4 == 0:
            for _ in range(2):
                x = self.cam_x + self.rng.rand() / 255.0 * SCREEN_W
                self.explode(x, self.terrain.height_at(x), 4 + self.rng.rand() % 3, 18, 2.2, 30)
        self.flash = 2 if self.planet_timer % 12 < 4 else self.flash

    # ------------------------------------------------------------ player
    def _edge(self, inp, name):
        return getattr(inp, name) and not getattr(self._prev, name)

    def _update_player(self, inp):
        p = self.player
        if self.hyper_t is not None:
            self._hyper_tick()
            if not p.alive:
                return
        elif not p.alive:
            return
        if p.materialize is not None and self.hyper_t is None:
            p.materialize += 1 / 40.0
            if p.materialize >= 1.0:
                p.materialize = None
        # facing flip
        if self._edge(inp, "reverse"):
            p.facing = -p.facing
        # horizontal
        was = p.thrusting
        p.vx -= p.vx / 64.0
        p.thrusting = bool(inp.thrust)
        if p.thrusting:
            p.vx += 3 / 32.0 * p.facing
        p.vx = max(-8.0, min(8.0, p.vx))
        if p.thrusting and not was:
            self.events.append("thrust_on")
        elif was and not p.thrusting:
            self.events.append("thrust_off")
        p.x = (p.x + p.vx) % WORLD
        if p.facing > 0:
            target = SHIP_REST_RIGHT + max(0.0, p.vx) * 8
        else:
            target = SHIP_REST_LEFT + min(0.0, p.vx) * 8
        if p.sx < target:
            p.sx = min(target, p.sx + 2)
        elif p.sx > target:
            p.sx = max(target, p.sx - 2)
        self.cam_x = (p.x - p.sx) % WORLD
        # vertical
        up, down = inp.up and not inp.down, inp.down and not inp.up
        if up:
            p.vy = -1.0 if p.vy >= 0 else max(-2.0, p.vy - 8 / 256.0)
        elif down:
            p.vy = 1.0 if p.vy <= 0 else min(2.0, p.vy + 8 / 256.0)
        else:
            p.vy = 0.0
        p.y = min(235.0, max(46.0, p.y + p.vy))
        if self.hyper_t is not None:
            return    # no weapons while rematerialising
        if self._edge(inp, "fire") and len(self.lasers) < 4:
            nose = p.sx + p.facing * 8
            self.lasers.append(Laser(nose, nose, p.facing, p.y + 1, self.cam_x))
            self.events.append("laser")
        if self._edge(inp, "smart_bomb") and self.smart_bombs > 0:
            self._smart_bomb()
        if self._edge(inp, "hyperspace") and p.materialize is None:
            self._start_hyper()

    def _smart_bomb(self):
        self.smart_bombs -= 1
        self.flash = 8
        self.events.append("smart_bomb")
        for e in [e for e in self.entities if e.alive and e.kind in ENEMY_KINDS]:
            if self.onscreen(e):
                self.kill(e)

    def _start_hyper(self):
        p = self.player
        self.events.append("hyperspace")
        self._clear_enemy_shots()
        if p.thrusting:
            self.events.append("thrust_off")
            p.thrusting = False
        self._release_carried()
        p.alive = False
        p.vx = p.vy = 0.0
        self.hyper_t = 0

    def _hyper_tick(self):
        p = self.player
        r = self.rng
        self.hyper_t += 1
        t = self.hyper_t
        if t == 15:
            p.x = r.rand16() * WORLD / 65536.0
            p.facing = r.sign()
            p.sx = SHIP_REST_RIGHT if p.facing > 0 else SHIP_REST_LEFT
            p.y = YMIN + 4 + (r.rand() >> 1)
            p.vx = p.vy = 0.0
            self.cam_x = (p.x - p.sx) % WORLD
            p.alive = True
            p.materialize = 0.0
            self.events.append("appear")
        elif t > 15:
            p.materialize = (t - 15) / 40.0
            if t >= 55:
                p.materialize = None
                self.hyper_t = None
                if r.rand() > 192:
                    self._kill_player()

    def _release_carried(self):
        h = self.player.carrying
        if h is not None and h.alive and h.state == "caught":
            h.set_state("falling")
            h.vy = 0.0
        self.player.carrying = None

    def _kill_player(self):
        p = self.player
        if self.state == "player_dying":
            return
        self.events.append("player_explode")
        if p.thrusting:
            self.events.append("thrust_off")
            p.thrusting = False
        self._release_carried()
        p.alive = False
        p.materialize = None
        self.hyper_t = None
        self.ships -= 1
        self.flash = 12
        self.state = "player_dying"
        self.timer = 90
        r = self.rng
        for i in range(96):
            ang_x = (r.rand() - 127.5) / 127.5
            ang_y = (r.rand() - 127.5) / 127.5
            s = 0.6 + 2.2 * r.rand() / 255.0
            self.particles.append(Particle(p.x, p.y, ang_x * s + p.vx * 0.3, ang_y * s,
                                           PX_COLORS[i % len(PX_COLORS)], 30 + (r.rand() % 40)))

    def _respawn(self):
        p = self.player
        self._clear_enemy_shots()
        p.alive = True
        p.materialize = 0.0
        p.vx = p.vy = 0.0
        p.y = 128.0
        p.facing = 1
        p.sx = SHIP_REST_RIGHT
        self.cam_x = (p.x - p.sx) % WORLD
        self.state = "play" if self.planet_timer <= 0 else "planet_exploding"
        self.clear_timer = None

    # ------------------------------------------------------------ lasers
    def _update_lasers(self):
        cam = self.cam_x
        keep = []
        for L in self.lasers:
            L.age += 1
            if L.moving:
                old = L.s1
                new = old + 8 * L.d
                best, best_t = None, None
                for e in self.entities:
                    if not e.alive or e.kind not in SCORES:
                        continue
                    if abs(e.y - L.y) > e.h / 2 + 0.5:
                        continue
                    rel = wrap_dx(e.x, cam)
                    a, b = rel - e.w / 2, rel + e.w / 2
                    if L.d > 0:
                        if b >= old and a <= new:
                            t = max(a, old) - old
                        else:
                            continue
                    else:
                        if a <= old and b >= new:
                            t = old - min(b, old)
                        else:
                            continue
                    if best_t is None or t < best_t:
                        best, best_t = e, t
                if best is not None:
                    L.s1 = old + L.d * best_t
                    L.moving = False
                    self.kill(best)
                else:
                    L.s1 = new
                    if L.s1 < -8 or L.s1 > SCREEN_W + 8:
                        L.moving = False
            L.s0 += 2 * L.d
            if (L.s1 - L.s0) * L.d <= 0:
                continue
            L.x0 = cam + L.s0
            L.x1 = cam + L.s1
            keep.append(L)
        self.lasers = keep

    # ------------------------------------------------------------ collisions
    def _overlap(self, e, w, h, px, py):
        return (abs(wrap_dx(e.x, px)) * 2 < w + e.w) and (abs(e.y - py) * 2 < h + e.h)

    def _collide_player(self):
        p = self.player
        dead = False
        for e in list(self.entities):
            if not e.alive:
                continue
            k = e.kind
            if k == "humanoid":
                if e.state == "falling" and p.carrying is None and \
                        self._overlap(e, SHIP_W, SHIP_H, p.x, p.y):
                    e.set_state("caught")
                    p.carrying = e
                    self.add_score(500)
                    self.popups.append(Popup(e.x, e.y - 6, 500))
                    self.events.append("humanoid_caught")
                continue
            if self._overlap(e, SHIP_W, SHIP_H, p.x, p.y):
                if k in SHOT_KINDS:
                    e.alive = False
                else:
                    self.kill(e)
                dead = True
        if dead:
            self._kill_player()
