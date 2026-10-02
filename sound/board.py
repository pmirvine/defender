"""SoundBoard: emulates the single-voice Williams sound board with the game's priority rules."""
import time
import numpy as np
import pygame
from . import cache, effects

# pygame.mixer.pre_init must precede init so mono sndarray/Sound(buffer) match; callers may have
# initialised already, in which case we adapt to whatever format the mixer has.
def _ensure_mixer():
    if not pygame.mixer.get_init():
        try:
            pygame.mixer.pre_init(effects.RATE, -16, 1, 512)
            pygame.mixer.init()
        except pygame.error:
            return False
    return True

def _convert(a16, freq, fmt, chans):
    """int16 mono @ RATE -> bytes in the mixer's actual format."""
    x = a16.astype(np.float32) / 32768.0
    if freq != effects.RATE:
        n = int(round(len(x) * freq / effects.RATE))
        x = np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)
    if chans > 1:
        x = np.repeat(x[:, None], chans, axis=1)
    if fmt == -16: out = np.round(x * 32767).astype('<i2')
    elif fmt == 16: out = (np.round(x * 32767) + 32768).astype('<u2')
    elif fmt == -32: out = x.astype('<f4')
    elif fmt == 8: out = (np.round(x * 127) + 128).astype(np.uint8)
    elif fmt == -8: out = np.round(x * 127).astype(np.int8)
    else: out = np.round(x * 32767).astype('<i2')
    return out.tobytes()

class SoundBoard:
    def __init__(self, enabled=True):
        self.enabled = enabled and _ensure_mixer()
        self._sounds = {}
        self._busy_until = 0.0
        self._prio = 0
        self._main = None
        self._thrust_ch = None
        self._thrusting = False
        self._bonus_step = 0
        self._bonus_t = -9.0
        if self.enabled:
            pygame.mixer.set_num_channels(max(4, pygame.mixer.get_num_channels()))
            self._main = pygame.mixer.Channel(0)
            self._thrust_ch = pygame.mixer.Channel(1)

    # -- loading
    def _sound(self, name):
        s = self._sounds.get(name)
        if s is None:
            f, fmt, ch = pygame.mixer.get_init()
            s = pygame.mixer.Sound(buffer=_convert(cache.get(name), f, fmt, ch))
            self._sounds[name] = s
        return s

    def preload(self):
        if not self.enabled: return
        for n in effects.all_render_names():
            self._sound(n)

    # -- control
    def play(self, name):
        if not self.enabled: return
        if name == 'thrust_on': return self._thrust(True)
        if name == 'thrust_off': return self._thrust(False)
        now = time.monotonic()
        if name == 'bonus_tick':
            if now - self._bonus_t > 1.0: self._bonus_step = 0
            self._bonus_t = now
            name = 'bonus_tick_%d' % (self._bonus_step % effects.BONUS_STEPS)
            self._bonus_step += 1
        else:
            self._bonus_step = 0
        if name not in effects.EVENTS and ':' in name:
            name = name.split(':')[0]
        if name not in effects.EVENTS: return
        prio = effects.EVENTS[name][0]
        if now < self._busy_until and prio < self._prio:
            return                                   # sequencer ignores lower priority
        self._prio = prio
        self._busy_until = now + effects.seq_seconds(name)
        self._main.play(self._sound(name))           # new command cuts the current voice
        self._duck()

    def _thrust(self, on):
        self._thrusting = on
        if on:
            if not self._thrust_ch.get_busy():
                self._thrust_ch.play(self._sound('thrust'), loops=-1)
            self._duck()
        else:
            self._thrust_ch.stop()

    def _duck(self):
        # thrust is a low-priority background: quiet while another effect plays
        if self._thrust_ch is not None:
            self._thrust_ch.set_volume(0.15 if self._main.get_busy() else 0.45)

    def update(self):
        """Optional per-frame call: restores thrust volume once the voice is idle."""
        if self.enabled and self._thrusting: self._duck()

    def stop(self, name=None):
        if not self.enabled: return
        if name in ('thrust', 'thrust_on', 'thrust_off'):
            self._thrust(False)
        elif name is None:
            self._main.stop(); self._thrust_ch.stop(); self._busy_until = 0
        else:
            self._main.stop(); self._busy_until = 0
