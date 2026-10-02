"""python -m sound.demo NAME [--wav out.wav] : play (or write) an effect. No NAME lists them."""
import sys, time, wave
from . import cache, effects

if __name__ == '__main__':
    args = sys.argv[1:]
    if not args:
        print('\n'.join(effects.event_names())); sys.exit(0)
    name = args[0]
    wav = args[args.index('--wav') + 1] if '--wav' in args else None
    key = 'thrust' if name.startswith('thrust') else name
    if name == 'bonus_tick': key = 'bonus_tick_0'
    if wav:
        a = cache.get(key)
        with wave.open(wav, 'wb') as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(effects.RATE); w.writeframes(a.tobytes())
    else:
        import pygame
        from .board import SoundBoard
        sb = SoundBoard(); sb.play(name if name != 'thrust' else 'thrust_on')
        time.sleep(2.0 if key == 'thrust' else len(cache.get(key)) / effects.RATE + 0.3)
