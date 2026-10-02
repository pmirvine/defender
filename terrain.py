"""Terrain from the original TDATA bit table (1 bit per world pixel, 2048 px, wraps)."""

WORLD = 2048

TDATA = bytes.fromhex(
    "2AAAAAAAAAAAABA1D55555555555AABFFFFFFFC0000000555557FFC001555555"
    "5555555FE015555557FFF00015555FFFFFFFFF0000000005557FFFE000055555"
    "5555FC0555555001FFFFFFC0000AAAAAAAFF0000FFFFFFFFF000001FE0005555"
    "5540AAAAAAAAAAAAB557AAAAAAF57FD5555557FF8007E07FF1557FFFFF000000"
    "00000FEF769111115EDBE98477ECC487479808983FC3CBDB9FC75F2FC77DEFBF"
    "FA4C572B61EFEFFBF7E8002040001404043C06001D073CE1A55555452AAAAAAA"
    "A85555555555555555555556AAAAFEAAAAAAAAAAAAAAAAEAAAAAA802AAAAAAAA"
    "BFBE3E63FFE0D81C182AAB1E777AAFA840707D400BFBFAFFC153547570030000"
)


def _build():
    bits = [(b >> (7 - i)) & 1 for b in TDATA for i in range(8)]
    prof = [224]
    y = 224
    for i in range(2048):
        y += -1 if bits[i] else 1
        prof.append(y)
    return prof[:2048]


PROFILE = _build()


class Terrain:
    def __init__(self):
        self.profile = PROFILE
        self.alive = True

    def height_at(self, x):
        return float(self.profile[int(x) % WORLD])

    def explode(self):
        self.alive = False

    def restore(self):
        self.alive = True


def alt_table():
    """Source ALTTBL: 1024 altitudes, one per 2 px."""
    return [PROFILE[i] for i in range(0, 2048, 2)]
