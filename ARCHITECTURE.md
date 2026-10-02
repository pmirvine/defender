# Defender recreation: architecture (contract between modules)

Run with `.venv/bin/python -m defender` from project root (flat layout: `defender.py` is the entry point). Python 3.14, pygame-ce 2.5.8, numpy.
Research inputs (read-only reference): `research/gameplay.md`, `research/ai_internals.md`, `research/graphics.md`,
`research/sprites_raw.txt`, `research/sound.md` + `research/defsound_ref.py` (sound agent output).

## Units and conventions
- Logic runs at a fixed 60 Hz. Rendering target surface is 304x256 (arcade), scaled with pygame.SCALED.
- World X: float *pixels*, range [0, 2048), wraps. World Y: float pixels, playfield 42..240 (screen y == world y).
- Terrain altitude `terrain.height_at(x)` gives screen-y of ground (160..232 range per research).
- Screen x of an object = wrap(obj.x - game.cam_x) + offset, where cam_x is the world x at the screen's left edge.
  Wrap so objects are visible across the seam. The visible window is 292 px wide (screen x 6..297).
- Palette: `defender.palette.PALETTE` list of 16 (r,g,b); sprite pixel nibble = index; 0 transparent.

## Package layout and ownership
| file | owner | contents |
|---|---|---|
| `palette.py`, `assets.py`, `font.py` | GFX agent | sprite loading from `data/sprites_raw.txt`, font rendering |
| `render.py`, `effects.py` | GFX agent | `Renderer.draw(surface, game)`: HUD, scanner, terrain, stars, entities, explosions, laser |
| `rng.py`, `terrain.py`, `waves.py` | GAME agent | RNG, terrain tables, wave table |
| `game.py`, `entities.py` | GAME agent | `Game`, entity classes, AI, collisions, scoring, state machine |
| `sound/` | SOUND agent | `SoundBoard` synthesis via numpy |
| `defender.py`, `attract.py`, `input.py`, `highscores.py` | LEAD | main loop, attract mode, input mapping |

## Game API (GAME agent implements, GFX + LEAD consume)
```python
class Inputs:  # one per frame, all bool
    thrust, reverse, fire, smart_bomb, hyperspace, up, down: bool   # reverse = flip direction (edge triggered by Game)
    start1, coin: bool
class Game:
    def __init__(self, rng_seed=None, highscores=None)
    def start_game(self)                 # new game, 3 ships, 3 smart bombs
    def update(self, inp: Inputs)        # advance exactly one 60 Hz tick
    # --- read-only state for renderer ---
    state: str            # 'play' | 'wave_intro' | 'player_dying' | 'wave_bonus' | 'planet_exploding' | 'game_over' | 'attract'
    score: int; ships: int; smart_bombs: int; wave: int
    cam_x: float          # world x at screen left
    player: Player        # .x .y .facing(+1/-1) .vx .thrusting .alive .materialize(0..1 or None)
    entities: list[Entity]  # every enemy/humanoid/shot/pod; Entity has: kind:str, x, y, frame:int, facing:int, alive, scanner_color:int (palette idx)
    lasers: list[Laser]     # .x0 .x1 .y (world px), .age
    particles: list[Particle]  # explosion/appear pixels: .x .y .color(palette idx) in world px
    terrain: Terrain      # .height_at(world_x)->float ; .alive bool (False after planet destroyed)
    popups: list[Popup]   # .x .y .value(250|500) .ttl
    flash: int            # >0 => whole-screen flash frames remaining (smart bomb / death), render handles
    events: list[str]     # sound event names emitted this tick; LEAD drains each frame via game.pop_events()
    bonus_info: dict|None # during 'wave_bonus': {'wave':int,'humanoids':int,'points':int}
```
Entity `kind` strings (renderer maps them to sprites): `lander mutant baiter bomber pod swarmer humanoid enemy_shot mine`.
Humanoid `frame`: 0..3 pose; `carried`/`falling` flags may exist. Lander `frame` 0..2, bomber `frame` 0..3, baiter 0..2.

## Sound event names (SOUND agent implements each; GAME agent emits via `self.events.append(name)`)
`laser, thrust(loop start/stop: 'thrust_on','thrust_off'), player_explode, enemy_explode (lander/mutant/baiter/bomber/swarmer),
pod_explode, smart_bomb, hyperspace, lander_grab, humanoid_scream (abducted), humanoid_caught, humanoid_landed,
humanoid_killed, lander_mutates, enemy_shot, mine_drop(bomber), swarmer_shot, baiter_appear, wave_start, extra_life,
planet_explode, coin, start, bonus_tick, appear (enemy materialise)`
`SoundBoard.play(name)`, `SoundBoard.stop(name)`, `SoundBoard.preload()` (render all to Sounds at startup).

## Tests
Each agent adds pytest tests under `tests/` for its own modules (headless: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy`).

## Game agent notes / additive API (defender/game.py, entities.py, terrain.py, waves.py, rng.py)
- All entity/player `x,y` are the sprite CENTRE (world px; x wraps mod 2048). Player `x` is world x of ship centre; `player.sx` = ship centre in screen-window coords (`wrap_dx(x, cam_x)`).
- `game.ships` = ships including the one in play (start 3); HUD should show `ships-1` reserve icons if it wants arcade fidelity. Game ignores `start1`/`coin` (LEAD owns credits); call `start_game()`. Initial state is `'attract'`; `'game_over'` persists until `start_game()` (see `game.game_over_ticks`).
- `Inputs` is a dataclass (all fields default False). `game.pop_events()` returns and clears events.
- Laser: `x0` tail, `x1` head (cam-relative so `wrap_dx` per-end is safe), `y`, `age`. Lasers are screen-attached like the arcade (head 8 px/tick, tail 2 px/tick).
- `player.alive` is False during the 15-tick hyperspace blackout and after death; `player.materialize` 0..1 during hyperspace/respawn appear (invulnerable), else None.
- `bonus_info` also has `total` (humanoids to count) and `per` (points each); `humanoids`/`points` count up as icons appear (one per 4 ticks).
- Humanoid extras: `state` ('walk'|'carried'|'falling'|'caught'), `carried`, `falling` flags; `frame` = (0 left / 2 right) + walk anim 0/1.
- Extras on Game: `wave`-level `params` (live difficulty dict), `lander_reserve`, `bomber_reserve`, `lander_total()`, `enemies_remaining()`, `terrain.explode()/restore()`, `state` also `'planet_exploding'` (150 ticks, gameplay continues).
- Wave-complete: 45-tick delay, then genocide of baiters/shots, `wave_bonus` (4 ticks/humanoid + 128 hold), then `wave_intro` (60 ticks).
- Events emitted additionally: `appear` (squad spawn / hyperspace rematerialise), `start` (start_game).
