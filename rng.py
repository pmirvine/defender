"""Williams Defender RNG (3 state bytes) plus helpers. Deterministic for a given seed."""


class Rand:
    def __init__(self, seed=None):
        self.seed = 0
        self.h = 0xA5
        self.l = 0x5A
        if seed is not None:
            s = (int(seed) * 2654435761 + 0x9E3779B9) & 0xFFFFFFFF
            self.seed = s & 0xFF
            self.h = (s >> 8) & 0xFF
            self.l = (s >> 16) & 0xFF
            if self.h == 0 and self.l == 0:
                self.h = 0xA5
            for _ in range(8):
                self.rand()

    def rand(self):
        """Next byte 0..255 (algorithm from the 6809 source)."""
        b = (self.seed * 3 + 17) & 0xFF
        carry = (((self.l >> 3) ^ self.l)) & 1
        c = self.h & 1
        self.h = (carry << 7) | (self.h >> 1)
        self.l = (c << 7) | (self.l >> 1)
        t = b + self.l
        b = t & 0xFF
        carry = t >> 8
        b = (b + self.h + carry) & 0xFF
        self.seed = b
        return b

    def rand16(self):
        return (self.rand() << 8) | self.rand()

    def rmax(self, a):
        """Source RMAX: skewed-low value in 1..a+1."""
        r = self.rand()
        while r > a:
            r >>= 1
        return r + 1

    def randint(self, lo, hi):
        """Uniform-ish integer in [lo, hi] inclusive."""
        n = hi - lo + 1
        return lo + (self.rand16() % n)

    def uniform(self, lo, hi):
        return lo + (hi - lo) * (self.rand16() / 65536.0)

    def sign(self):
        return 1 if self.rand() & 1 else -1

    def chance(self, p):
        return self.rand16() < p * 65536
