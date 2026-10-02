"""Game event -> original sound-ROM routine mapping, and offline rendering to int16 PCM."""
import numpy as np
from . import routines as R

RATE = 22050
GAIN_PEAK = 0.9
TICK = 0.016   # main-CPU sound sequencer tick

def _gw(i, **k):
    return lambda b: R.gwave(b, i, **k)

ROUTINES = {
    'LITE': R.lite, 'APPEAR': R.appear, 'TURBO': R.turbo, 'CANNON': R.cannon,
    'HYPER': R.hyper, 'RADIO': R.radio, 'SCREAM': R.scream,
    'THRUST': R.thrust, 'BG1': R.bg1,
    'SAW': lambda b: R.vari(b, 'SAW'), 'FOSHIT': lambda b: R.vari(b, 'FOSHIT'),
    'QUASAR': lambda b: R.vari(b, 'QUASAR'),
    'HBDV': _gw(0), 'STDV': _gw(1), 'DP1V': _gw(2), 'XBV': _gw(3), 'BBSV': _gw(4),
    'HBEV': _gw(5), 'PROTV': _gw(6), 'SPNRV': _gw(7), 'CLDWNV': _gw(8), 'SV3': _gw(9),
    'ED10': _gw(10), 'ED12': _gw(11), 'ED17': _gw(12),
}

# event -> (priority, [(routine, max_seconds), ...]) ; segments play back to back,
# each cut at max_seconds (the next command pre-empting it) or at its natural end.
# Priorities / cut times from DEFA7.SRC sound table (16 ms ticks).
EVENTS = {
    'laser':           (0xC0, [('TURBO', 0x30 * TICK)]),
    'player_explode':  (0xF0, [('LITE', 8 * TICK), ('LITE', 8 * TICK), ('CANNON', 2.6)]),
    'enemy_explode':   (0xD0, [('HBEV', 0.7)]),            # lander hit
    'pod_explode':     (0xD0, [('BBSV', 1.5)]),            # probe hit
    'smart_bomb':      (0xE8, [('LITE', 4 * TICK)] * 6 + [('CANNON', 2.6)]),
    'hyperspace':      (0xE0, [('HYPER', 1.0)]),
    'lander_grab':     (0xC0, [('RADIO', 0.8)]),
    'humanoid_scream': (0xD8, [('SCREAM', 2.5)]),
    'humanoid_caught': (0xE0, [('SPNRV', 10 * TICK)] * 2 + [('SPNRV', 0.3)]),
    'humanoid_landed': (0xE0, [('QUASAR', 2.7)]),
    'humanoid_killed': (0xE0, [('LITE', 0.7)]),
    'lander_mutates':  (0xE0, [('LITE', 0.7)]),
    'enemy_shot':      (0xC0, [('DP1V', 0.3)]),
    'mine_drop':       (0xC0, [('SV3', 0.25)]),
    'swarmer_shot':    (0xC0, [('ED12', 0.7)]),
    'baiter_appear':   (0xD0, [('APPEAR', 1.1)]),
    'wave_start':      (0xD0, [('APPEAR', 1.1)]),
    'appear':          (0xD0, [('APPEAR', 1.1)]),
    'extra_life':      (0xFF, [('FOSHIT', 5.4)]),
    'planet_explode':  (0xE8, [('TURBO', 4 * TICK), ('LITE', 6 * TICK), ('LITE', 6 * TICK),
                               ('CANNON', 2.6)]),
    'coin':            (0xFF, [('HYPER', 2.3)]),
    'start':           (0xF0, [('SV3', 0x40 * TICK)]),
    # optional per-kind enemy explosions: play('enemy_explode:bomber')
    'enemy_explode:lander':  (0xD0, [('HBEV', 0.7)]),
    'enemy_explode:mutant':  (0xD0, [('CANNON', 8 * TICK)]),
    'enemy_explode:bomber':  (0xD0, [('HBDV', 0.7)]),
    'enemy_explode:baiter':  (0xD0, [('PROTV', 1.1)]),
    'enemy_explode:swarmer': (0xD0, [('PROTV', 1.1)]),
}
BONUS_STEPS = 12   # bonus_tick ladder: bonus_tick_0 .. bonus_tick_11 (BON2 repeated calls)
for _k in range(BONUS_STEPS):
    EVENTS['bonus_tick_%d' % _k] = (0xC8, [('BON2:%d' % _k, 0.3)])
# looping background: rendered as a loopable buffer
LOOPS = {'thrust': ('THRUST', 1.6)}

def event_names():
    """Public event names (ARCHITECTURE.md) incl. thrust_on/off and bonus_tick."""
    base = [n for n in EVENTS if not n.startswith('bonus_tick_') and ':' not in n]
    return base + ['thrust_on', 'thrust_off', 'bonus_tick']

def seq_seconds(name):
    """Game-side sequencer busy time used for priority pre-emption."""
    return sum(c for _, c in EVENTS[name][1]) if name in EVENTS else 0.0

def _run(rname, max_s, state):
    b = R.Board(max_s * R.CLK)
    b.HI, b.LO, b.dac = state
    if rname.startswith('BON2:'):
        R.gwave(b, 13, bonus=True, bonus_step=int(rname[5:]))
    else:
        ROUTINES[rname](b)
    state[:] = [b.HI, b.LO, b.dac]
    return R.render(b, RATE)

def _post(x):
    """AC-coupled amp (high-pass ~20 Hz), peak limit, short fade; -> int16."""
    w = int(0.04 * RATE) | 1
    pad = np.pad(x, (w // 2, w // 2), mode='edge')
    c = np.concatenate([[0], np.cumsum(pad)])
    x = x - (c[w:] - c[:-w])[:len(x)] / w
    pk = np.abs(x).max() if len(x) else 0
    if pk > 0:
        x = x * min(1.0, GAIN_PEAK / pk)
    n = min(len(x), int(0.004 * RATE))
    if n: x[-n:] *= np.linspace(1, 0, n)
    return np.clip(np.round(x * 32767), -32767, 32767).astype(np.int16)

def render_event(name):
    """Render one event (or loop 'thrust') to mono int16 at RATE."""
    state = [0x3C, 0xA5, 128]
    if name in LOOPS:
        rname, secs = LOOPS[name]
        x = _run(rname, secs, state)
        n = int(0.05 * RATE)           # equal-gain crossfade of tail over head
        f = np.linspace(0, 1, n)
        head, tail = x[:n].copy(), x[-n:].copy()
        y = x[:-n].copy()
        y[:n] = head * f + tail * (1 - f)
        return _post_loop(y)
    prio, segs = EVENTS[name]
    parts = [_run(r, c, state) for r, c in segs]
    return _post(np.concatenate(parts))

def _post_loop(y):
    w = int(0.04 * RATE) | 1
    pad = np.pad(y, (w // 2, w // 2), mode='wrap')
    c = np.concatenate([[0], np.cumsum(pad)])
    y = y - (c[w:] - c[:-w])[:len(y)] / w
    pk = np.abs(y).max()
    y = y * min(1.0, GAIN_PEAK / pk)
    return np.clip(np.round(y * 32767), -32767, 32767).astype(np.int16)

def all_render_names():
    return [n for n in EVENTS] + list(LOOPS)
