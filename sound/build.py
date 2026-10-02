"""python -m sound.build [--rebuild] : pregenerate the sound cache."""
import sys
from . import cache

if __name__ == '__main__':
    cache.build_all(verbose=True, rebuild='--rebuild' in sys.argv)
