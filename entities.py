"""Entity classes and per-entity AI. Pure logic (no pygame).

All x,y are the CENTRE of the sprite in world pixels (x wraps mod 2048, y playfield 42..240).
Per-entity AI runs on "naps" like the original processes: lander 6/1/4 ticks, mutant 3,
baiter 6, swarmer 3, bomber ~4, humanoid 2.
"""
from waves import lander_yv, mutant_yv

WORLD = 2048
YMIN = 42
YMAX = 240

SIZES = {
    "lander": (10, 8), "mutant": (10, 8), "baiter": (12, 4), "bomber": (8, 8),
    "pod": (8, 8), "swarmer": (6, 4), "humanoid": (4, 8),
    "enemy_shot": (4, 3), "mine": (4, 3),
}
SCORES = {
    "lander": 150, "mutant": 150, "baiter": 200, "bomber": 250, "pod": 1000,
    "swarmer": 150, "enemy_shot": 25, "mine": 25,
}
SCANNER_COLORS = {
    "lander": 3, "mutant": 8, "baiter": 4, "bomber": 2, "pod": 8, "swarmer": 2,
    "humanoid": 4, "enemy_shot": 9, "mine": 10,
}
ENEMY_KINDS = ("lander", "mutant", "baiter", "bomber", "pod", "swarmer")
SHOT_KINDS = ("enemy_shot", "mine")
EXPLOSION_COLORS = {
    "lander": 3, "mutant": 8, "baiter": 4, "bomber": 2, "pod": 8, "swarmer": 2,
    "humanoid": 4, "enemy_shot": 4, "mine": 4,
}
HUMANOID_SAFE_VY = 0.875     # px/frame; faster than this on landing kills
HUMANOID_MAX_VY = 3.0


def wrap_dx(a, b):
    """Signed shortest world-x distance a - b in [-1024, 1024)."""
    return (a - b + WORLD / 2) % WORLD - WORLD / 2


def sgn(v):
    return 1 if v > 0 else (-1 if v < 0 else 0)


class Laser:
    def __init__(self, s0, s1, d, y, cam_x):
        self.s0 = s0          # tail, screen-window coords (== wrap_dx(x, cam_x))
        self.s1 = s1          # head
        self.d = d
        self.y = y
        self.age = 0
        self.moving = True
        self.x0 = cam_x + s0
        self.x1 = cam_x + s1


class Particle:
    __slots__ = ("x", "y", "vx", "vy", "color", "ttl")

    def __init__(self, x, y, vx, vy, color, ttl):
        self.x, self.y, self.vx, self.vy, self.color, self.ttl = x, y, vx, vy, color, ttl


class Popup:
    def __init__(self, x, y, value, ttl=50):
        self.x, self.y, self.value, self.ttl = x, y, value, ttl


class Player:
    def __init__(self):
        self.x = 0.0
        self.y = 128.0
        self.facing = 1
        self.vx = 0.0
        self.vy = 0.0
        self.sx = 66.0            # ship centre in screen-window coords
        self.thrusting = False
        self.alive = True
        self.materialize = None
        self.carrying = None


class Entity:
    kind = "entity"

    def __init__(self, x, y, vx=0.0, vy=0.0):
        self.x = x % WORLD
        self.y = float(y)
        self.vx = vx
        self.vy = vy
        self.frame = 0
        self.facing = 1 if vx >= 0 else -1
        self.alive = True
        self.age = 0
        self.nap = 0
        self.scanner_color = SCANNER_COLORS.get(self.kind, 2)
        self.w, self.h = SIZES.get(self.kind, (8, 8))

    def step(self):
        self.x = (self.x + self.vx) % WORLD
        self.y += self.vy
        if self.y < YMIN:
            self.y = YMAX
        elif self.y > YMAX:
            self.y = YMIN

    def update(self, g):
        self.age += 1
        self.step()
        self.nap -= 1
        if self.nap <= 0:
            self.think(g)

    def think(self, g):
        pass


# ---------------------------------------------------------------- humanoid
class Humanoid(Entity):
    kind = "humanoid"

    def __init__(self, g, x):
        super().__init__(x, 0)
        self.facing = g.rng.sign()
        self.y = self.stand_y(g)
        self.state = "walk"     # walk | carried | falling | caught
        self.target_of = None   # lander hunting this humanoid
        self.carrier = None
        self.carried = False
        self.falling = False
        self.pose = 0

    def stand_y(self, g):
        return g.terrain.height_at(self.x) - self.h / 2

    def set_state(self, s):
        self.state = s
        self.carried = s in ("carried", "caught")
        self.falling = s == "falling"

    def _pose(self):
        self.frame = (0 if self.facing < 0 else 2) + (self.age // 8) % 2

    def update(self, g):
        self.age += 1
        st = self.state
        if st == "walk":
            if self.age % 2 == 0:
                self.x = (self.x + self.facing) % WORLD
                if g.rng.rand() <= 8:
                    self.facing = -self.facing
                ty = self.stand_y(g)
                if self.y < ty:
                    self.y = min(ty, self.y + 1)
                elif self.y > ty:
                    self.y = max(ty, self.y - 1)
            self._pose()
        elif st == "carried":
            self._pose()    # position driven by the carrying lander
        elif st == "falling":
            if self.age % 4 == 0:
                self.vy = min(HUMANOID_MAX_VY, self.vy + 8 / 256.0)
            self.y += self.vy
            self._pose()
            ground = g.terrain.height_at(self.x)
            if self.y + self.h / 2 >= ground:
                self.y = ground - self.h / 2
                if self.vy > HUMANOID_SAFE_VY:
                    g.kill_humanoid(self)
                else:
                    g.add_score(250)
                    g.popups.append(Popup(self.x, self.y - 6, 250))
                    g.events.append("humanoid_landed")
                    self.vy = 0.0
                    self.set_state("walk")
        elif st == "caught":
            p = g.player
            self.x = (p.x + 2 * p.facing) % WORLD
            self.y = p.y + 10
            self._pose()
            ground = g.terrain.height_at(self.x)
            if self.y + self.h / 2 >= ground:
                self.y = ground - self.h / 2
                g.add_score(500)
                g.popups.append(Popup(self.x, self.y - 6, 500))
                g.events.append("humanoid_landed")
                p.carrying = None
                self.vy = 0.0
                self.set_state("walk")


# ---------------------------------------------------------------- lander
class Lander(Entity):
    kind = "lander"

    def __init__(self, g, x, y=44):
        p = g.params
        super().__init__(x, y, g.rng.sign() * g.rng.rmax(p["lndxv"]) / 32.0, lander_yv(p))
        self.mode = "seek"
        self.target = None
        self.shot_timer = g.rng.rmax(p["ldstim"])

    def update(self, g):
        self.age += 1
        self.frame = (self.age // 6) % 3
        if self.mode == "descend":
            self.think(g)
        else:
            self.nap -= 1
            if self.nap <= 0:
                self.think(g)
        self.step()
        t = self.target
        if self.mode == "flee" and t is not None and t.alive and t.state == "carried":
            t.x = self.x
            t.y = self.y + 12

    def _valid_target(self):
        t = self.target
        return t is not None and t.alive and t.target_of is self and t.state in ("walk", "carried")

    def _shoot_tick(self, g):
        self.shot_timer -= 1
        if self.shot_timer <= 0:
            self.shot_timer = g.rng.rmax(g.params["ldstim"])
            g.aimed_shot(self)

    def think(self, g):
        p = g.params
        yv = lander_yv(p)
        if self.mode == "seek":
            self.nap = 6
            if not self._valid_target():
                self.target = g.pick_target(self)
            if self.target is None and g.humanoid_count() == 0:
                g.mutate(self)
                return
            d = g.terrain.height_at(self.x) - 50 - self.y
            self.vy = yv if d > 0 else (0.0 if d >= -20 else -yv)
            self._shoot_tick(g)
            t = self.target
            if t is not None and abs(wrap_dx(t.x, self.x)) < 16:
                self.mode = "descend"
                self.vx = 0.0
                self.vy = 0.0
        elif self.mode == "descend":
            if not self._valid_target():
                self.target = None
                self.mode = "seek"
                self.vx = g.rng.sign() * g.rng.rmax(p["lndxv"]) / 32.0
                self.nap = 1
                return
            t = self.target
            dx = wrap_dx(t.x, self.x)
            if abs(dx) > 1:
                self.x = (self.x + sgn(dx)) % WORLD
            goal = t.y - 12
            dy = goal - self.y
            if abs(dy) > yv:
                self.y += sgn(dy) * yv
            else:
                self.y = goal
            self._shoot_tick(g)
            if abs(self.y - goal) < 0.5 and abs(dx) <= 4:
                g.events.append("lander_grab")
                g.events.append("humanoid_scream")
                t.set_state("carried")
                t.carrier = self
                self.mode = "flee"
                self.vx = 0.0
                self.vy = -yv
                self.nap = 4
        elif self.mode == "flee":
            self.nap = 4
            self.vy = -yv
            self._shoot_tick(g)
            if self.y <= YMIN + 8:
                g.mutate(self)


# ---------------------------------------------------------------- mutant
class Mutant(Entity):
    kind = "mutant"

    def __init__(self, g, x, y):
        super().__init__(x, y, 0.0, 0.0)
        self.shot_timer = g.rng.rmax(g.params["szstim"])

    def update(self, g):
        self.frame = (self.age // 4) % 3
        super().update(g)

    def think(self, g):
        p = g.params
        pl = g.player
        self.nap = 3
        dx = wrap_dx(pl.x, self.x)
        self.vx = (1 if dx >= 0 else -1) * p["szxv"] / 32.0
        self.facing = 1 if self.vx > 0 else -1
        dy = pl.y - self.y
        yv = mutant_yv(p)
        if abs(dx) <= 56:
            self.vy = sgn(dy) * yv if abs(dy) > 1 else 0.0
        elif abs(dy) <= 8:
            self.vy = -sgn(dy or g.rng.sign()) * yv
        else:
            self.vy = 0.0
        self.y += g.rng.sign() * p["szry"]
        if self.y < YMIN:
            self.y = YMAX
        elif self.y > YMAX:
            self.y = YMIN
        self.shot_timer -= 1
        if self.shot_timer <= 0:
            self.shot_timer = g.rng.rmax(p["szstim"])
            g.aimed_shot(self)


# ---------------------------------------------------------------- baiter
class Baiter(Entity):
    kind = "baiter"

    def __init__(self, g, x, y):
        super().__init__(x, y)
        self.shot_timer = 8
        self.first = True

    def think(self, g):
        p = g.params
        pl = g.player
        self.nap = 6
        self.frame = (self.frame + 1) % 3
        self.shot_timer -= 1
        if self.shot_timer <= 0:
            self.shot_timer = g.rng.rmax(p["ufstim"])
            g.aimed_shot(self)
        if self.first or g.rng.rand() > p["ufosk"]:
            self.first = False
            dx = wrap_dx(pl.x, self.x)
            if abs(dx) >= 20:
                self.vx = (2 if dx > 0 else -2) + pl.vx
            dy = pl.y - self.y
            if abs(dy) >= 10:
                self.vy = ((1 if dy > 0 else -1) + pl.vy) / 2.0
            self.facing = 1 if self.vx >= 0 else -1


# ---------------------------------------------------------------- bomber
class Bomber(Entity):
    kind = "bomber"

    def __init__(self, g, x, y, vx):
        super().__init__(x, y, vx, 0.0)
        self.cruise = y
        self.nap = g.rng.randint(1, 4)

    def update(self, g):
        # the bomber's own vy is integrated every tick but clamped to the playfield
        self.age += 1
        self.x = (self.x + self.vx) % WORLD
        self.y = min(max(self.y + self.vy, YMIN + 4), 200)
        self.nap -= 1
        if self.nap <= 0:
            self.think(g)

    def think(self, g):
        r = g.rng
        pl = g.player
        self.nap = r.randint(2, 6)
        self.vy += ((r.rand() & 0x3F) - 0x20) / 256.0
        self.vy -= self.vy / 32.0
        self.frame = r.rand() & 3
        if g.onscreen(self):
            off = self.y - pl.y
            if abs(off) < 16:
                self.vy += (1 if off >= 0 else -1) * 16 / 256.0
            elif abs(off) > 32:
                self.vy -= sgn(off) * 16 / 256.0
            if (r.rand() & 7) == 0:
                g.drop_mine(self)
        else:
            if (r.rand() & 3) == 0:
                self.cruise = min(0x68, max(0x40, self.cruise + (r.rand() & 3) - 2))
            if abs(self.cruise - self.y) > 16:
                self.vy += sgn(self.cruise - self.y) * 16 / 256.0


# ---------------------------------------------------------------- pod
class Pod(Entity):
    kind = "pod"

    def __init__(self, g, x, y):
        r = g.rng
        vx = ((r.rand() & 0x3F) - 0x20) / 32.0
        vy = r.sign() * (0x21 + (r.rand() & 0x1F)) / 256.0
        super().__init__(x, y, vx, vy)

    def update(self, g):
        self.age += 1
        self.frame = 0
        self.step()


# ---------------------------------------------------------------- swarmer
class Swarmer(Entity):
    kind = "swarmer"

    def __init__(self, g, x, y):
        r = g.rng
        p = g.params
        super().__init__(x, y, ((r.rand() & 0x3F) - 0x20) / 32.0, 2 * ((r.rand() ^ 0x80) - 0x80) / 256.0)
        self.acc = (r.rand() & p["swac"]) / 256.0
        self.delay = r.rand() & 0x1F
        self.first = True
        self.shot_timer = r.rmax(p["swstim"])
        self.nap = 1

    def think(self, g):
        p = g.params
        pl = g.player
        r = g.rng
        self.nap = 3
        if self.age < self.delay:
            return
        dx = wrap_dx(pl.x, self.x)
        if self.first or abs(dx) > 150:
            self.first = False
            self.vx = sgn(dx or 1) * p["swxv"] / 32.0
            self.facing = 1 if self.vx > 0 else -1
        dy = pl.y - self.y
        self.vy += sgn(dy) * self.acc
        self.vy = max(-2.0, min(2.0, self.vy))
        self.vy -= self.vy / 64.0
        self.vy += ((r.rand() & 0x1F) - 0x10) / 256.0
        self.shot_timer -= 1
        if self.shot_timer <= 0:
            self.shot_timer = r.rmax(p["swstim"])
            if sgn(dx) == sgn(self.vx):
                g.swarmer_shot(self)


# ---------------------------------------------------------------- shots
class EnemyShot(Entity):
    kind = "enemy_shot"

    def __init__(self, x, y, vx, vy, life=160):
        super().__init__(x, y, vx, vy)
        self.life = life

    def update(self, g):
        self.age += 1
        self.frame = 0
        self.x = (self.x + self.vx) % WORLD
        self.y += self.vy
        self.life -= 1
        rel = wrap_dx(self.x, g.cam_x)
        if self.life <= 0 or self.y < YMIN or self.y > YMAX or rel < -4 or rel > 296:
            self.alive = False


class Mine(Entity):
    kind = "mine"

    def __init__(self, g, x, y):
        super().__init__(x, y, 0.0, 0.0)
        self.life = ((g.rng.rand() & 0x1F) + 1) * 8

    def update(self, g):
        self.age += 1
        self.frame = 0
        self.life -= 1
        if self.life <= 0:
            self.alive = False
