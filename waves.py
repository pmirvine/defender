"""Wave table (BLK71.SRC WVTAB) and difficulty application."""

GA1 = 5    # initial difficulty (inter-wave applications)
GA2 = 15   # difficulty ceiling

# name, max, min, intra delta, inter delta, W1, W2, W3, W4
WVTAB = [
    ("landers", 20, 0, 0, 0, 15, 20, 20, 20),
    ("bombers", 3, 0, 0, 0, 0, 3, 4, 5),
    ("pods", 6, 0, 0, 0, 0, 1, 3, 4),
    ("mutants", 10, 0, 0, 0, 0, 0, 0, 0),
    ("swarmers", 10, 0, 0, 0, 0, 0, 0, 0),
    ("wavtim", 30, 0, 0, 0, 30, 25, 20, 16),
    ("wavsiz", 5, 0, 0, 0, 5, 5, 5, 5),
    ("lndxv", 0x60, 0, 3, 2, 0x16, 0x1E, 0x26, 0x2E),
    ("lndyv_hi", 1, 0, 0, 0, 0, 0, 1, 1),
    ("lndyv_lo", 0xFF, 0, 0x10, 0, 0x70, 0xB0, 0x00, 0x00),
    ("ldstim", 0x80, 0x10, -4, -2, 0x4A, 0x3A, 0x2A, 0x2A),
    ("tiexv", 0x30, 0, 0, 0, 0x20, 0x28, 0x2C, 0x30),
    ("szry", 2, 0, 0, 0, 1, 1, 2, 2),
    ("szyv_hi", 1, 0, 0, 0, 0, 0, 1, 1),
    ("szyv_lo", 0xFF, 0, 8, 6, 0x62, 0xE0, 0x02, 0x12),
    ("szxv", 0x60, 0, 8, 4, 0x0C, 0x1C, 0x24, 0x28),
    ("szstim", 0xFF, 0x08, -2, -2, 0x2A, 0x22, 0x1E, 0x1C),
    ("swxv", 0x60, 0, 8, 2, 0x16, 0x1E, 0x20, 0x22),
    ("swstim", 40, 10, -2, -1, 25, 25, 25, 25),
    ("swac", 0x3F, 0, 0, 0, 0x1F, 0x1F, 0x1F, 0x3F),
    ("ufotim", 0xC0, 0x18, -12, -4, 0xD4, 0xC4, 0xA4, 0x94),
    ("ufstim", 10, 3, -1, -1, 15, 13, 12, 10),
    ("ufosk", 200, 40, -12, -8, 240, 220, 200, 200),
]
_ROW = {r[0]: r for r in WVTAB}


def _apply(params, which):
    """Apply every row's delta (which: 3=intra, 4=inter) if it stays within [min, max]."""
    for row in WVTAB:
        name, mx, mn = row[0], row[1], row[2]
        d = row[which]
        if d:
            nv = params[name] + d
            if (nv <= mx) if d > 0 else (nv >= mn):
                params[name] = nv


def wave_params(wave, ga1=GA1, ga2=GA2):
    """Live difficulty parameters (dict) for a wave, including inter-wave steps."""
    col = 5 + min(max(wave, 1), 4) - 1
    p = {row[0]: row[col] for row in WVTAB}
    for _ in range(min(ga1 + max(wave - 4, 0), ga2)):
        _apply(p, 4)
    return p


def intra_step(params):
    """Intra-wave drift, applied every 40 exec passes (600 ticks)."""
    _apply(params, 3)


def lander_yv(p):
    """Lander vertical speed in px/frame."""
    return (p["lndyv_hi"] * 256 + p["lndyv_lo"]) / 256.0


def mutant_yv(p):
    return (p["szyv_hi"] * 256 + p["szyv_lo"]) / 256.0
