import os
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
import numpy as np
import pytest
from sound import SoundBoard, effects, cache

ARCH_EVENTS = """laser thrust_on thrust_off player_explode enemy_explode pod_explode smart_bomb hyperspace
lander_grab humanoid_scream humanoid_caught humanoid_landed humanoid_killed lander_mutates enemy_shot
mine_drop swarmer_shot baiter_appear wave_start extra_life planet_explode coin start bonus_tick appear""".split()

# approximate natural/sequenced lengths (research duration table + sequencer timers)
EXPECT = {'laser': .77, 'pod_explode': 1.5, 'coin': 2.26, 'extra_life': 5.31, 'humanoid_landed': 2.64,
          'humanoid_killed': .69, 'appear': 1.07, 'enemy_shot': .16, 'swarmer_shot': .6, 'start': 1.02,
          'enemy_explode': .6, 'player_explode': 2.84, 'smart_bomb': 2.95, 'humanoid_scream': 2.5}

def test_all_events_known():
    names = set(effects.event_names())
    assert set(ARCH_EVENTS) <= names

@pytest.mark.parametrize('name', effects.all_render_names())
def test_render(name):
    a = cache.get(name)
    assert a.dtype == np.int16 and a.ndim == 1 and len(a) > 0
    assert np.abs(a.astype(int)).max() < 32767          # no clipping
    assert np.abs(a).max() > 3000                         # audible
    assert a.std() > 500

@pytest.mark.parametrize('name,dur', sorted(EXPECT.items()))
def test_duration(name, dur):
    a = cache.get(name)
    assert abs(len(a) / effects.RATE - dur) < 0.12 * dur + 0.05

def test_board_play_all():
    sb = SoundBoard()
    assert sb.enabled
    sb.preload()
    for n in ARCH_EVENTS + ['enemy_explode:bomber', 'bogus']:
        sb.play(n)
    sb.stop('thrust_on'); sb.stop(None)

def test_priority():
    sb = SoundBoard()
    sb.play('coin'); ch = sb._main.get_sound()
    sb.play('laser')                       # lower priority than active coin: ignored
    assert sb._main.get_sound() is ch
    sb.stop()
    sb.play('laser'); sb.play('coin')      # higher pre-empts
    assert sb._main.get_sound() is sb._sounds['coin']
