# Defender

A recreation of Williams Electronics' 1981 arcade classic **Defender**, written in Python with
[pygame-ce](https://pyga.me/). The goal is fidelity to the original arcade game in gameplay,
graphics and sound, using data and algorithms taken from the released original source code.

> Unofficial fan project, not affiliated with or endorsed by Williams, Midway or any rights holder.
> Defender is a trademark of its owners. Sprite bitmaps, the font and game constants are derived from the
> historically released Red Label source ([historicalsource/defender](https://github.com/historicalsource/defender)).
> Intended for personal and educational use.

## Running

Developed and tested on Python 3.14 with pygame-ce 2.5.

```sh
python3 -m venv .venv
.venv/bin/pip install pygame-ce numpy
.venv/bin/python -m defender
```

Run the tests with `.venv/bin/pip install pytest && .venv/bin/python -m pytest`.

## Controls

| Action | Default key |
|---|---|
| Move up / down | `A` / `Z` |
| Thrust | `Shift` |
| Reverse direction | `Caps Lock` |
| Fire laser | `Return` |
| Smart bomb | `Space` |
| Hyperspace | `H` |
| Coin / Start / Quit | `5` / `1` or `Enter` / `Esc` |

Press `F2` on the title screen to open the **Controls** menu and rebind any action. Choices are saved to
`~/.defender_controls.json`; press `R` in the menu to restore defaults. A gamepad also works (stick moves,
buttons 0-4 = thrust, fire, smart bomb, hyperspace, reverse).

## Display and scaling

The game renders at the arcade's 304x256 and scales that to the window. Options (command line overrides the
saved setting for that run):

```sh
.venv/bin/python -m defender --scale 4            # window = 4x the arcade screen (1-16)
.venv/bin/python -m defender --scale auto         # largest whole multiple that fits your desktop (default)
.venv/bin/python -m defender --fullscreen         # also --no-fullscreen
.venv/bin/python -m defender --smooth             # smoothed scaling (default is crisp square pixels)
```

Crisp mode only uses whole-number scales (letterboxed if the window doesn't divide evenly) so every game pixel is
the same size. In-game hotkeys, saved to `~/.defender_settings.json`: `F7`/`F8` smaller/larger window,
`F9` crisp/smooth, `F11` fullscreen (on a Mac laptop hold `fn`). The window is also freely resizable.

## What's implemented

- **Gameplay** (`game.py`, `entities.py`, `waves.py`, `terrain.py`, `rng.py`): ship physics, lasers, smart bombs,
  hyperspace, Landers, Mutants, Baiters, Bombers, Pods and Swarmers, humanoid abduction/rescue, planet destruction,
  the wave table and difficulty progression, scoring and extra ships/bombs. Logic runs at a fixed 60 Hz and is
  deterministic for a given seed.
- **Graphics** (`render.py`, `assets.py`, `palette.py`, `font.py`, `effects.py`, `logos.py`): original 4-bit sprite
  bitmaps and font, the arcade palette with colour cycling, scanner, terrain, starfield, pixel-scatter explosions,
  and a 304x256 display scaled with crisp pixels.
- **Sound** (`sound/`): the sound board is emulated, not sampled. The original sound-ROM routines (GWAVE wave-table
  synth, variable-duty square sweeps, noise generators) are ported to numpy and rendered at startup, then cached in
  `data/soundcache/`. Like the real board it plays one voice at a time, with a separate looping thrust channel.
- **Attract mode** (`attract.py`): Williams/Defender title, hall of fame, enemy instruction page, and high-score entry.

## Project layout

```
defender.py       entry point / main loop        game.py, entities.py, waves.py, ...   game logic
render.py, ...    graphics                       sound/                                 sound-board emulation
controls.py       key bindings + remap menu      data/                                  sprite data (+ sound cache)
tests/            pytest suite                   research/                              notes on the original game
```

`ARCHITECTURE.md` describes the module contract; `research/` holds the notes on gameplay rules, graphics, sound
hardware and AI internals that the implementation is based on.

## Known gaps

Some values could not be verified against the original and were derived or estimated: enemy shot speed, bomber mine
lifetime, swarmer count per pod, exact visible resolution, and sound pitch (within a few percent). The attract-mode
sequence order is approximate and the Williams logo is rendered from a script font rather than the original artwork.
Sound has been verified numerically but not by ear against a real board. Contributions and corrections are welcome.
