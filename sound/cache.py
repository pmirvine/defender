"""On-disk cache of rendered effects (.npy int16 mono @ RATE), keyed by a source hash."""
import hashlib, os
from pathlib import Path
import numpy as np
from . import effects

def cache_dir():
    d = os.environ.get('DEFENDER_SOUNDCACHE')
    return Path(d) if d else Path(__file__).resolve().parent.parent / 'data' / 'soundcache'

def _version():
    h = hashlib.sha1()
    here = Path(__file__).parent
    for f in ('routines.py', 'effects.py'):
        h.update((here / f).read_bytes())
    return h.hexdigest()[:12]

def _check():
    d = cache_dir(); d.mkdir(parents=True, exist_ok=True)
    vf = d / 'VERSION'
    v = _version()
    if not vf.exists() or vf.read_text().strip() != v:
        for f in d.glob('*.npy'): f.unlink()
        vf.write_text(v)
    return d

def get(name, rebuild=False):
    """Return int16 mono array for render name (loads cache, renders+saves on miss)."""
    d = _check()
    p = d / (name.replace(':', '_') + '.npy')
    if not rebuild and p.exists():
        try:
            return np.load(p)
        except Exception:
            pass
    a = effects.render_event(name)
    try:
        np.save(p, a)
    except OSError:
        pass
    return a

def build_all(verbose=False, rebuild=False):
    out = {}
    for n in effects.all_render_names():
        out[n] = get(n, rebuild)
        if verbose: print('%-28s %6.2fs' % (n, len(out[n]) / effects.RATE))
    return out
