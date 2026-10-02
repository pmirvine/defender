"""Reference port of Williams Defender sound ROM (VSNDRM1) -> numpy.
Each routine emits (cycle_time, dac_byte) events; render() box-filters to a PCM rate.
CPU = MC6808 @ 3.579545MHz/4 = 894886 cycles/s.  Cycle counts hand-derived (6800 timing)."""
import numpy as np
CLK = 894886.25

class Board:
    def __init__(s, max_cycles=3*CLK):
        s.t = 0.0; s.T = []; s.V = []; s.dac = 0; s.max = max_cycles
        s.HI = 0x3C; s.LO = 0xA5          # LFSR seed (HI=$3C from reset code; LO is power-up RAM)
    def out(s, v):
        s.dac = v & 255; s.T.append(s.t); s.V.append(s.dac)
    def tick(s, c):
        s.t += c
        return s.t < s.max
    def rnd(s, A):                         # LSRx3/EOR LO/LSR/ROR HI/ROR LO ; returns carry (old LO bit0)
        c = ((A >> 3) ^ s.LO) & 1
        c2 = s.HI & 1; s.HI = (c << 7) | (s.HI >> 1)
        c3 = s.LO & 1; s.LO = (c2 << 7) | (s.LO >> 1)
        return c3

# ---------------------------------------------------------------- tables
GWVTAB = [
 [127,217,255,217,127,36,0,36],                                   # 0 GS2
 [0,64,128,0,255,0,128,64],                                       # 1 GSSQ2
 [127,176,217,245,255,245,217,176,127,78,36,9,0,9,36,78],         # 2 GS1
 [127,197,236,231,191,141,109,106,127,148,146,113,64,23,18,57],   # 3 GS12
 [255]*4+[0]*4+[255]*4+[0]*4,                                     # 4 GSQ22
 [138,149,160,171,181,191,200,209,218,225,232,238,243,247,251,253,254,255,254,253,251,247,243,238,232,225,218,
  209,200,191,181,171,160,149,138,127,117,106,95,84,74,64,55,46,37,30,23,17,12,8,4,2,1,0,
  1,2,4,8,12,17,23,30,37,46,55,64,74,84,95,106,117,127],         # 5 GS72 (72)
 [89,123,152,172,179,172,152,123,89,55,25,6,0,6,25,55],           # 6 GS1.7
]
assert len(GWVTAB[5]) == 72 and all(len(w) in (8,16,72) for w in GWVTAB)
GFR = {   # GFRTAB in ROM order (patterns may run past their label into the next table)
 'BONSND':[0xA0,0x98,0x90,0x88,0x80,0x78,0x70,0x68,0x60,0x58,0x50,0x44,0x40],
 'HBTSND':[1,1,2,2,4,4,8,8,0x10,0x10,0x30,0x60,0xC0,0xE0],
 'SPNSND':[1,1,2,2,3,4,5,6,7,8,9,0xA,0xC],
 'TRBPAT':[0x80,0x7C,0x78,0x74,0x70,0x74,0x78,0x7C,0x80],
 'HBDSND':[1,1,2,2,4,4,8,8,0x10,0x20,0x28,0x30,0x38,0x40,0x48,0x50,0x60,0x70,0x80,0xA0,0xB0,0xC0],
 'BBSND':[8,64]*10,
 'HBESND':[1,2,4,8,9,0xA,0xB,0xC,0xE,0xF,0x10,0x12,0x14,0x16],
 'SPNR':[0x40],
 'COOLDN':[0x10,8,1],
 'STDSND':[1,1,1,1,2,2,3,3,4,4,5,6,8,0xA,0xC,0x10,0x14,0x18,0x20,0x30,0x40,0x50,0x40,0x30,
           0x20,0x10,0xC,0xA,8,7,6,5,4,3,2,2,1,1,1],
 'ED10FP':[7,8,9,0xA,0xC,8],
 'ED13FP':[0x17,0x18,0x19,0x1A,0x1B,0x1C,0,0,0],
}
FLAT = []; OFF = {}
for k in GFR: OFF[k] = len(FLAT); FLAT += GFR[k]
OFF['SWPAT'] = OFF['BBSND']
def pat(name, n): return list(FLAT[OFF[name]:OFF[name]+n])
# SVTAB rows: (echo<<4|cycles, decay<<4|wave, predecay, dfinc, dcnt, patlen, pattern)
SVTAB = [
 (0x81,0x24,0x00,0x00,0,22,'HBDSND'),   # 1  HBDV
 (0x12,0x05,0x1A,0xFF,0,39,'STDSND'),   # 2  STDV
 (0x11,0x05,0x11,0x01,15,1,'SWPAT'),    # 3  DP1V
 (0x11,0x31,0x00,0x01,0,13,'SPNSND'),   # 4  XBV
 (0xF4,0x12,0x00,0x00,0,20,'BBSND'),    # 5  BBSV
 (0x41,0x45,0x00,0x00,0,15,'HBESND'),   # 6  HBEV (15th byte runs into SPNR=$40)
 (0x21,0x35,0x11,0xFF,0,13,'SPNSND'),   # 7  PROTV
 (0x15,0x00,0x00,0xFD,0,1,'SPNR'),      # 8  SPNRV
 (0x31,0x11,0x00,0x01,0,3,'COOLDN'),    # 9  CLDWNV
 (0x01,0x15,0x01,0x01,1,1,'BBSND'),     # 10 SV3
 (0xF6,0x53,0x03,0x00,2,6,'ED10FP'),    # 11 ED10
 (0x6A,0x10,0x02,0x00,2,6,'ED13FP'),    # 12 ED12
 (0x1F,0x12,0x00,0xFF,0x10,4,'SPNR'),   # 13 ED17 (pattern = $40,$10,$08,$01)
 (0x31,0x11,0x00,0xFF,0,13,'BONSND'),   # 14 BONV  (index 13, via BON2 = N 18)
 (0x12,0x06,0x00,0xFF,1,9,'TRBPAT'),    # 15 TRBV  (index 14, via BG2)
]

# ---------------------------------------------------------------- GWAVE
def gwave(b, idx, bg2flag=None, bonus=False):
    v = SVTAB[idx]
    gcc = v[0] & 15; gecho = v[0] >> 4; gecdec = v[1] >> 4; wav = GWVTAB[v[1] & 15]
    predec, gdfinc, gdcnt, plen = v[2], v[3], v[4], v[5]
    freq = pat(v[6], plen)               # GWFRQ..FRQEND view (list slice)
    fofs = 0
    rom = list(wav); ram = list(wav)
    def decay(n):
        if n == 0: return True
        for i in range(len(ram)):
            ram[i] = (ram[i] - n * (rom[i] >> 4)) & 255
        return b.tick(len(ram) * (66 + 12 * n))
    def transfer():
        ram[:] = rom; return b.tick(len(ram) * 43 + 60)
    b.tick(150)                          # GWLD
    if not decay(predec): return
    lo, hi = 0, len(freq)                # active window into pattern
    if bg2flag is not None:              # BG2 entry: FOFSET = ~(flag<<2); then scan
        fofs = (~(bg2flag << 2)) & 255
        r = scan(freq, lo, hi, fofs, gdfinc); 
        if r is None: return
        lo, hi = r
    first = True
    while True:
        for echo in range(gecho or 256):   # GECNT DEC wraps if 0        # GWAVE: GECNT = GECHO; repeat pattern with decaying wave
            for i in range(lo, hi):
                per = (freq[i] + fofs) & 255 or 256
                for c in range(gcc):
                    for j, s in enumerate(ram):
                        if not b.tick(6 * per + 13): return    # LDAA GPER, DECA/BNE x per, LDAA ,X, STAA
                        b.out(s)
                        last = j == len(ram) - 1
                        b.tick(13 if not last else (59 if c == gcc - 1 else 62))
            if not decay(gecdec): return
        if bonus: return
        if gdfinc == 0: return
        gdcnt = (gdcnt - 1) & 255
        if gdcnt == 0: return
        fofs = (fofs + gdfinc) & 255
        r = scan(freq, lo, hi, fofs, gdfinc)
        if r is None: return
        lo, hi = r
        if gecdec:
            if not transfer(): return
            if not decay(predec): return

def scan(freq, lo, hi, fofs, gdfinc):
    """GEND61: shrink window to contiguous run of entries whose (entry+FOFSET) stays in range."""
    start = None; i = lo
    while i < hi:
        s = fofs + freq[i]
        if gdfinc & 0x80:                       # decrementing
            ok = (s & 255) != 0 and s > 255
        else:
            ok = s <= 255
        if ok:
            if start is None: start = i
        elif start is not None:
            return start, i
        i += 1
    return (start, hi) if start is not None else None

def bg2_loop(b, flag, passes=8):
    """BG2: turbine pitch pattern (TRBV) at FOFSET=~(flag<<2); repeats forever (GDCNT toggles 1->0)."""
    for _ in range(passes):
        gwave(b, 14, bg2flag=flag)
        # (each gwave call = 1 pass of the pattern; BG2LP re-enters via GEND61 with same offset)

# ---------------------------------------------------------------- VARI
def vari(b, name, maxloops=None):
    raw = {'SAW':[0x40,0x01,0x00,0x10,0xE1,0x00,0x80,0xFF,0xFF],
           'FOSHIT':[0x28,0x01,0x00,0x08,0x81,0x02,0x00,0xFF,0xFF],
           'QUASAR':[0x28,0x81,0x00,0xFC,0x01,0x02,0x00,0xFC,0xFF],
           'CABSHK':[0xFF,0x01,0x00,0x18,0x41,0x04,0x80,0x00,0xFF]}[name]
    return vari_raw(b, raw, maxloops)
def vari_raw(b, p, maxloops=None, hold=None):
    LOPER,HIPER,LODT,HIDT,HIEN = p[0:5]; SWPDT=(p[5]<<8)|p[6]; LOMOD=p[7]; VAMP=p[8]
    snd = VAMP; b.out(snd); b.tick(10)
    while True:                                   # VAR0
        locnt, hicnt = LOPER, HIPER
        while True:                               # V0
            x = SWPDT or 65536
            swept = False
            while not swept:
                # low phase
                b.tick(3); snd ^= 255; b.tick(6); b.out(snd)
                n = locnt or 256
                if x <= n:
                    if not b.tick(14 * (x - 1) + 8): return
                    break
                x -= n
                if not b.tick(14 * n): return
                snd ^= 255; b.tick(6); b.out(snd); b.tick(3)
                n = hicnt or 256
                if x <= n:
                    if not b.tick(14 * (x - 1) + 8): return
                    break
                x -= n
                if not b.tick(14 * n + 4): return
            # VSWEEP
            if not (snd & 128): snd ^= 255
            b.tick(3 + 4 + 2 + 2); b.out(snd); b.tick(4 + 3 + 3 + 4 + 3 + 3 + 4 + 3 + 4)
            locnt = (locnt + LODT) & 255; hicnt = (hicnt + HIDT) & 255
            if hicnt != HIEN: continue
            break
        if LOMOD == 0: return
        LOPER = (LOPER + LOMOD) & 255
        if LOPER == 0: return

# ---------------------------------------------------------------- noise family
def litening(b, lfreq, dfreq, cycnt):
    snd = 0xFF; b.out(snd)
    while True:
        for _ in range(cycnt):
            c = b.rnd(b.LO)
            if not b.tick(30): return
            if c: snd ^= 255; b.tick(6); b.out(snd)
            if not b.tick(3 + 6 * (lfreq or 256) + 6): return
        lfreq = (lfreq + dfreq) & 255
        if lfreq == 0: return
def lite(b): litening(b, 1, 1, 3)
def appear(b): litening(b, 0xC0, 0xFE, 0x10)

def noise(b, decay, x, amp, cycnt, nfflg):
    while True:
        for _ in range(cycnt):
            c = b.rnd(b.LO)
            if not b.tick(40): return
            b.out(amp if c else 0)
            if not b.tick(10 + 8 * (x or 65536)): return
        amp -= decay
        if amp <= 0: return
        if nfflg: x += 1
def turbo(b): noise(b, 1, 1, 0xFF, 0x20, 0x20)

def fnoise(b, count, fmax, fdflg, dsflg):
    """FNOISE: random-target ramp generator. slope = (FHI:FLO)/256 DAC units per 30-cycle sample."""
    flo = 0; sampc = count; x = count
    while True:                                   # FNOIS0
        x = sampc; a = b.dac
        while True:                               # FNOIS1
            b.rnd(a)
            fhi = (fmax & b.HI) if dsflg else fmax
            if not b.tick(58 if dsflg else 55): return
            lo = b.LO; frac = flo; up = not (a > lo); end6 = False
            while True:
                x = (x - 1) & 0xFFFF
                if x == 0: end6 = True; break
                b.out(a)
                if not b.tick(30): return
                if up:
                    frac += flo; cb = frac > 255; frac &= 255
                    a += fhi + cb
                    if a > 255 or a > lo: break
                else:
                    frac -= flo; bw = frac < 0; frac &= 255
                    a -= fhi + bw
                    if a < 0 or a <= lo: break
            if end6: break
            a = lo; b.out(a); b.tick(12)
        if not fdflg: continue
        d = (fmax << 8) | flo
        d = (d - (d >> 3)) & 0xFFFF
        fmax, flo = d >> 8, d & 255
        if fmax == 0 and flo == 7: return

def cannon(b): fnoise(b, 1000, 0xFF, 1, 1)
def thrust(b): fnoise(b, 0, 3, 0, 0)         # X = leftover jump addr (huge): effectively infinite
def bg1(b):    fnoise(b, 0, 1, 0, 0)

# ---------------------------------------------------------------- hyper / radio / scream
def hyper(b):
    snd = 0; b.out(snd); tempa = 0
    while tempa < 128:
        for a in range(128):
            if a == tempa: snd ^= 255; b.tick(3 + 4 + 6); b.out(snd)
            else: b.tick(3 + 4)
            if not b.tick(2 + 108 + 2 + 4): return
        snd ^= 255; b.out(snd); b.tick(6 + 6 + 4)
        tempa += 1
RADSND = [0x8C,0x5B,0xB6,0x40,0xBF,0x49,0xA4,0x73,0x73,0xA4,0x49,0xBF,0x40,0xB6,0x5B,0x8C]
def radio(b):
    freq = 100; phase = 0
    while freq < 65536:
        phase += freq
        carry = phase > 0xFFFF; phase &= 0xFFFF
        if carry: freq += 1
        b.out(RADSND[(phase >> 8) & 15])
        if not b.tick(60): return

def scream(b):
    fr = [0x40, 0, 0, 0]; tm = [0, 0, 0, 0]
    while True:
        for _ in range(256):
            B = 0; amp = 0x80
            for e in range(4):
                tm[e] = (tm[e] + fr[e]) & 255
                if tm[e] & 128: B += amp
                amp >>= 1
            b.out(B & 255)
            if not b.tick(215): return
        flag = False
        for e in range(4):
            if fr[e]:
                if fr[e] == 0x37 and e < 3: fr[e + 1] = 0x41
                fr[e] -= 1; flag = True
        b.tick(150)
        if not flag: return

# ---------------------------------------------------------------- render
def render(b, rate=44100, dur=None):
    if not b.T: return np.zeros(1)
    T = np.array(b.T); V = np.array(b.V, float)
    end = (min(b.t, b.max) if dur is None else dur * CLK)
    n = int(end / CLK * rate)
    edges = np.arange(n + 1) * CLK / rate
    # piecewise constant integral
    Tn = np.append(T, end)
    seg = np.diff(np.clip(Tn, 0, end)); cum = np.concatenate([[0], np.cumsum(V * seg)])
    tt = np.clip(Tn[:-1], 0, end)
    def integ(x):
        i = np.clip(np.searchsorted(Tn[:-1], x, side='right') - 1, 0, len(V) - 1)
        return cum[i] + V[i] * (x - np.clip(Tn[i], 0, end))
    avg = np.diff(integ(edges)) / (CLK / rate)
    return (avg - 128) / 128.0

def run(fn, *a, max_s=3.0, **k):
    b = Board(max_s * CLK); fn(b, *a, **k); return b

def sp1(b, flag, loops=3):
    """SP1 spinner: CABSHK with LOPER derived from call counter flag (1..31)."""
    k = 32 - flag; lo = 0
    while k > 20: lo += 14; k -= 1
    lo += 5 * k
    raw = [lo & 255,0x01,0x00,0x18,0x41,0x04,0x80,0x00,0xFF]
    for _ in range(loops): vari_raw(b, raw)
