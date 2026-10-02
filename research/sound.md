# Williams Defender (1981) sound: research for a procedural numpy recreation

Sources (all verified by reading them):
- `historicalsource/williams-soundroms` -> `VSNDRM1.SRC` ("DEFENDER SOUNDS REV. 1.0 BY SAM D 10/80", programmer Sam Dicker). This is THE Defender sound ROM source (the `historicalsource/defender` repo has only the main-CPU game code; `mwenge/defender` carries a re-formatted copy as `src/vsndrm1.src`). VSNDRM2/3/4 = Stargate/Robotron/Joust (same engine family, not needed).
- `historicalsource/defender` `DEFA7.SRC` / `DEFB6.SRC`: the main-CPU sound table and sequencer (which board command each game event sends).
- MAME `williams.cpp` (mame0240 checked): board hardware description.
- A hand-verified reference port of every routine is in `research/defsound_ref.py` (numpy, runs; durations match hand cycle counts). Algorithms below are exactly what that file does.

## 1. Hardware

- Sound CPU: Motorola MC6808 (6800 core, 128 bytes on-chip RAM at $0000-$007F, stack top $7F). Crystal 3.579545 MHz, internal /4 => **894,886 cycles/s** (not 1 MHz). 1 cycle = 1.1175 us.
- MC6821 PIA at $0400 (MAME maps $0400-$0403). Port A = outputs -> **MC1408 8-bit DAC** (single mono channel, no sound chip, no hardware envelope, no filter modelled in MAME; analog amp + volume only). Port B = inputs (command from main CPU, 5 bits used: `COMA; ANDA #$1F` after a read of the inverted lines), CB1 interrupt -> 6808 IRQ. Reset sets PIA CA2/CB2 and seeds LFSR HI=$3C.
- ROM: 2K at $F800 (MAME name `video_sound_rom_1.ic12`, CRC fefd5b48). Vectors: IRQ->IRQ handler, NMI -> diagnostic loop (plays VARI #1 forever), RESET -> SETUP.
- **No fixed sample rate.** The DAC is written whenever the 6808 executes `STAA SOUND`; each routine is a software loop whose timing sets pitch. Effective update rates vary from ~894886/30 = 29.8 kHz (FNOISE ramps) down to a few hundred Hz. Recommended recreation: generate (cycle_time, byte) events exactly as the ROM does, then area-average ("box filter") onto 44.1/22.05 kHz (this is what `render()` does; plain sample-and-hold aliases badly for the 15-30 kHz loops). MAME just feeds DAC changes to its resampler (the DAC "sample rate" is the CPU write stream).
- Output is full-scale 0..255 (DAC center 128). Most effects are loud 0x00/0xFF-type waves; gain is set by the analog volume only. Treat (v-128)/128.
- **The board is monophonic and single-threaded**: a new command interrupts (IRQ resets the stack with `LDS #ENDRAM`) whatever is playing, which is simply abandoned mid-loop. When a routine ends the CPU spins in `BRA *` and the DAC just holds its last value (so effectively silence/DC). Background flags (BG1/BG2) make the idle loop restart the background sound. Layering in a recreation must be done by emulating the same pre-emption (the main CPU's priority sequencer decides what to send), not by mixing.
- No speech in Defender (talking hooks `$EFFD` are checked for `$7E` JMP opcode and skipped).

## 2. Command decode (IRQ handler)

```
cmd = (~PIA_B) & 0x1F ; if cmd==0: ignore (goes to IRQ3 background check)
# organ/spinner/bonus flag housekeeping: any cmd != $0E clears SP1FLG; any cmd != $12 clears B2FLG
a = cmd - 1
if a <= 0x0C:            GWAVE sound #cmd (1..13) = SVTAB[a]  : GWLD(a); GWAVE()
elif a <= 0x1B:          JMPTBL[a-0x0D]      (cmd 14..28)
else:                    VARI vector (a-0x1C) (cmd 29..31) : VARILD; VARI()
after any of these returns -> IRQ3: if BG1FLG: BG1() ; elif BG2FLG: BG2() ; else idle (BRA *)
```
Command map (N = decimal command):

| N | hex | routine | N | hex | routine |
|---|---|---|---|---|---|
| 1 | 01 | GWAVE HBDV (heartbeat distorto) | 17 | 11 | LITE |
| 2 | 02 | GWAVE STDV (start distorto) | 18 | 12 | BON2 (GWAVE BONV, stateful) |
| 3 | 03 | GWAVE DP1V | 19 | 13 | BGEND (clear BG flags = silence) |
| 4 | 04 | GWAVE XBV | 20 | 14 | TURBO |
| 5 | 05 | GWAVE BBSV (big ben) | 21 | 15 | APPEAR |
| 6 | 06 | GWAVE HBEV (heartbeat echo) | 22 | 16 | THRUST |
| 7 | 07 | GWAVE PROTV | 23 | 17 | CANNON |
| 8 | 08 | GWAVE SPNRV (spinner/drip) | 24 | 18 | RADIO |
| 9 | 09 | GWAVE CLDWNV (cool down) | 25 | 19 | HYPER |
| 10 | 0A | GWAVE SV3 | 26 | 1A | SCREAM |
| 11 | 0B | GWAVE ED10 | 27 | 1B | ORGANT (organ tune; unused by game) |
| 12 | 0C | GWAVE ED12 | 28 | 1C | ORGANN (organ note; unused) |
| 13 | 0D | GWAVE ED17 | 29 | 1D | VARI SAW |
| 14 | 0E | SP1 (spinner, VARI CABSHK, stateful) | 30 | 1E | VARI FOSHIT |
| 15 | 0F | BG1 (low rumble, sets BG1FLG) | 31 | 1F | VARI QUASAR |
| 16 | 10 | BG2INC (turbine background; unused by Defender game code) | | | |

## 3. Game events -> board commands (DEFA7.SRC "SOUND TABLE")

Main CPU table rows are `priority, then N x (repcount, timer in 16 ms ticks, board cmd), 0`. The sequencer (`SNDSEQ`, once per ~16 ms frame) sends cmd, waits `timer` ticks, repeats `repcount` times, then moves to the next triple. Higher priority byte pre-empts (`SNDLD` ignores lower priority than the current one; equals pre-empt). `SNDOUT` writes `~cmd & $3F`. Thrust: while the thrust switch is on and no table sound is active, it sends $16 once; on release sends $0F (BG1). $13 = stop (sent at player-death end / game over). After a table sound ends nothing stops the board's routine: it runs to its natural end or until the next command (so long-tailed routines such as TURBO/RADIO/SCREAM only cut off when something else is sent).

| Game event | Pri | Sequence (rep x 16ms-timer -> cmd) | Board routine(s) |
|---|---|---|---|
| Coin | FF | 1x$18 -> $19 | HYPER |
| Free ship (extra life) | FF | 1x$20 -> $1E | VARI FOSHIT |
| Player death | F0 | 2x$08 -> $11 ; 1x$20 -> $17 | LITE x2 then CANNON |
| Start 1 / Start 2 | F0 | 1x$40 -> $0A / 1x$10 -> $0B | GW SV3 / GW ED10 |
| Terrain blow | E8 | 1x$04 -> $14 ; 2x$06 -> $11 ; 2x$0A -> $17 | TURBO, LITE, CANNON |
| Smart bomb | E8 | 6x$04 -> $11 ; 1x$10 -> $17 | LITE x6 then CANNON |
| Astronaut caught | E0 | 3x$0A -> $08 | GW SPNRV |
| Astronaut lands | E0 | 1x$18 -> $1F | VARI QUASAR |
| Astronaut hit (also lightning bolt/mutation) | E0 | 1x$18 -> $11 | LITE |
| Astronaut scream (falling) | D8 | 1x$10 -> $1A | SCREAM |
| Appear (enemy/wave spawn) | D0 | 1x$30 -> $15 | APPEAR |
| Probe(pod) hit | D0 | 1x$10 -> $05 | GW BBSV |
| Schitzo (baiter-class "schitz") hit | D0 | 1x$08 -> $17 | CANNON |
| UFO (bomber?/baiter) hit | D0 | 1x$08 -> $07 | GW PROTV |
| Tie (bomber) hit | D0 | 1x$0A -> $01 | GW HBDV |
| Lander hit | D0 | 1x$0A -> $06 | GW HBEV |
| Lander pickup (grabs human) | D0 | 1x$10 -> $0B | GW ED10 |
| Lander suck (carrying human up) | C8 | 10x1 -> $0E, plus per-frame `$12` in LNDFXA | SP1 spinner (flag steps 1..31), BON2 |
| Swarmer hit | C0 | 1x$08 -> $07 | GW PROTV |
| Laser | C0 | 1x$30 -> $14 | TURBO |
| Lander grab | C0 | 1x$20 -> $18 | RADIO |
| Lander shoot / UFO shoot | C0 | 1x$08 -> $03 | GW DP1V |
| Schitzo shoot | C0 | 1x$30 -> $09 | GW CLDWNV |
| Swarmer shoot | C0 | 1x$18 -> $0C | GW ED12 |
| Thrust on / off | -- | $16 / $0F | THRUST / BG1 |
| Stop | -- | $13 | BGEND |

(Names "UFO/Tie/Probe/Schitz" are the 1980 source names for baiter/bomber/pod/mutant-family objects; map sound->enemy by the source labels, e.g. pod = PRHSND (probe), swarmer = SWHSND/SWSSND, mutant likely = SCHSND/SSHSND (schitzo), bomber = TIHSND, baiter = UFHSND/USHSND. Smart bomb and every explosion use LITE/CANNON.)

## 4. Algorithms

All timing: 1 cycle = 1/894886 s. Cycle figures below are my hand count of 6800 timings with RAM variables in direct page (DEX 4, branch 4, DECA 2, STAA dir 4/ext 5, COM ext 6, ROR ext 6, LDAA dir 3/ext 4/idx 5, CPX dir 5, INX 4 ...). They reproduce the structure of the ROM; absolute pitch could be off by a few % if the assembler chose different addressing modes (I could not disassemble the ROM binary offline).

### 4.1 LFSR noise source (shared)
16-bit shift register HI:LO (seed HI=$3C; LO is power-up RAM, use any nonzero):
```
def rnd(A):                      # A = LO for LITE/NOISE; A = current DAC value for FNOISE
    c = ((A >> 3) ^ LO) & 1      # LSRAx3; EORA LO; LSRA -> carry
    c2 = HI & 1; HI = (c<<7) | (HI>>1)      # ROR HI
    out = LO & 1; LO = (c2<<7) | (LO>>1)    # ROR LO
    return out                   # carry after ROR LO
```

### 4.2 GWAVE (wave-table synth with echo/decay and frequency sweeps)
Sound vector, 7 bytes: `b0 = (GECHO<<4)|GCCNT`, `b1 = (GECDEC<<4)|WAVE#`, `PREDECAY`, `GDFINC` (signed delta of FOFSET), `GDCNT`, `PATLEN`, `PATOFFSET` (into GFRTAB, a table of 8-bit *periods*; bigger = lower pitch).
```
GWLD:  RAM_wave = ROM wave[WAVE#]  (length byte L then L samples; max 72)
       wave_decay(PREDECAY);  window = pattern[0:PATLEN]; FOFSET = 0
wave_decay(n): for i: RAM[i] = (RAM[i] - n*(ROM[i]>>4)) & 255      # 1/16 of original per step, 8-bit wrap
GWAVE:
  loop:                                   # (GEND0 -> GWAVE)
    repeat (GECHO or 256) times:          # GECNT; GECHO=0 wraps to 256
      for p in window:
         per = (p + FOFSET) & 255 ; if per==0: per=256
         repeat GCCNT times:              # cycles of the wave per pitch step
            for s in RAM_wave:
               delay 6*per cycles (DECA/BNE loop) ; (load,store)  -> DAC = s
               sample-to-sample gap = 26 + 6*per cycles (13 after STAA + 3+6per+10)
               wave end: +46 more if another cycle of same pitch (gap 75+6per), +46-3... new pitch gap 72+6per
      wave_decay(GECDEC)                  # each echo is quieter (RAM_wave shrinks toward 0 -> DAC 0)
    if B2FLG (bonus): return
    if GDFINC==0: return
    GDCNT -= 1 (8-bit, 0 wraps to 255) ; if 0: return
    FOFSET += GDFINC ; window = scan(window)          # GEND60/61
    if window empty: return
    if GECDEC: RAM_wave = ROM wave ; wave_decay(PREDECAY)    # re-arm echoes
scan(): keep only the contiguous run of entries whose (p+FOFSET) is still valid:
   GDFINC>=0 : valid iff p+FOFSET <= 255 (no carry)
   GDFINC<0  : valid iff p+FOFSET > 255 as a 9-bit sum and low byte != 0   (i.e. FOFSET is negative; period stays >=1)
   (leading invalid entries are skipped; the run ends at first invalid one)
```
Frequency of a pattern step: `f = 894886 / (L*(26+6*per))` Hz (L = wave length; add ~46 cycles once per wave-end gap, so period ~ L*(26+6per)+46).
The echo effect is purely amplitude decay of the wave RAM between pattern repeats; the wave samples shrink toward 0 so the DAC level (and DC) drops -> sound fades, not a mix.

Waves (value lists, DAC bytes): GS2 (8): 127,217,255,217,127,36,0,36. GSSQ2 (8): 0,64,128,0,255,0,128,64. GS1 (16) sine: 127,176,217,245,255,245,217,176,127,78,36,9,0,9,36,78. GS12 (16): 127,197,236,231,191,141,109,106,127,148,146,113,64,23,18,57. GSQ22 (16) square 255x4,0x4,255x4,0x4 (4 on, 4 off, twice). GS72 (72): sine-like, 138..255..0..127 (see `GWVTAB[5]` in the .py for all 72). GS1.7 (16): 89,123,152,172,179,172,152,123,89,55,25,6,0,6,25,55. Wave# 0..6 = GS2,GSSQ2,GS1,GS12,GSQ22,GS72,GS1.7.

GWAVE vectors (as decoded; `echo/cyc, decay/wave, pre, dfinc, dcnt, patlen, pattern`):

| N | name | echo | cyc | dec | wave | pre | dfinc | dcnt | len | pattern |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | HBDV | 8 | 1 | 2 | 4 GSQ22 | $00 | 0 | 0 | 22 | HBDSND: 1,1,2,2,4,4,8,8,10,20,28,30,38,40,48,50,60,70,80,A0,B0,C0 |
| 2 | STDV | 1 | 2 | 0 | 5 GS72 | $1A | -1 | 0 | 39 | STDSND: 1,1,1,1,2,2,3,3,4,4,5,6,8,A,C,10,14,18,20,30,40,50,40,30,20,10,C,A,8,7,6,5,4,3,2,2,1,1,1 |
| 3 | DP1V | 1 | 1 | 0 | 5 GS72 | $11 | 1 | 15 | 1 | SWPAT: 8 |
| 4 | XBV | 1 | 1 | 3 | 1 GSSQ2 | $00 | 1 | 0 | 13 | SPNSND: 1,1,2,2,3,4,5,6,7,8,9,A,C |
| 5 | BBSV | 15 | 4 | 1 | 2 GS1 | $00 | 0 | 0 | 20 | BBSND: 8,40,8,40,8,40,8,40,8,40,8,40,8,40,8,40,8,40,8,40 |
| 6 | HBEV | 4 | 1 | 4 | 5 GS72 | $00 | 0 | 0 | 15 | HBESND: 1,2,4,8,9,A,B,C,E,F,10,12,14,16,40 |
| 7 | PROTV | 2 | 1 | 3 | 5 GS72 | $11 | -1 | 0 | 13 | SPNSND: 1,1,2,2,3,4,5,6,7,8,9,A,C |
| 8 | SPNRV | 1 | 5 | 0 | 0 GS2 | $00 | -3 | 0 | 1 | SPNR: 40 |
| 9 | CLDWNV | 3 | 1 | 1 | 1 GSSQ2 | $00 | 1 | 0 | 3 | COOLDN: 10,8,1 |
| 10 | SV3 | 0 | 1 | 1 | 5 GS72 | $01 | 1 | 1 | 1 | BBSND: 8 |
| 11 | ED10 | 15 | 6 | 5 | 3 GS12 | $03 | 0 | 2 | 6 | ED10FP: 7,8,9,A,C,8 |
| 12 | ED12 | 6 | 10 | 1 | 0 GS2 | $02 | 0 | 2 | 6 | ED13FP: 17,18,19,1A,1B,1C |
| 13 | ED17 | 1 | 15 | 1 | 2 GS1 | $00 | -1 | 16 | 4 | SPNR: 40,10,8,1 |
| 18 | BONV (N=18) | 3 | 1 | 1 | 1 GSSQ2 | $00 | -1 | 0 | 13 | BONSND: A0,98,90,88,80,78,70,68,60,58,50,44,40 |
| BG2 | TRBV (BG2) | 1 | 2 | 0 | 6 GS1.7 | $00 | -1 | 1 | 9 | TRBPAT: 80,7C,78,74,70,74,78,7C,80 |

(echo 0 = 256 echoes; dcnt 0 with dfinc!=0 = 255 sweep passes; patterns in hex periods. `pat()` in the .py reproduces the overrun of HBESND into SPNR and ED17 into COOLDN.)

Special GWAVE callers:
- **BON2 (N=18)**: first call (B2FLG==0): set B2FLG=1, load BONV, play pattern once, return (B2FLG!=0 blocks the sweep loop). While B2FLG stays 1 (game resends $12 every frame in the lander-carries-astronaut loop), each further call jumps to GEND50: FOFSET += GDFINC(-1), rescans, plays the pattern again => a descending-pitch ladder, one step per call. Any other command clears B2FLG.
- **SP1 (N=14)**: calls VARI CABSHK repeatedly (see 4.3) with `LOPER` from a call counter `SP1FLG` (1..31, wraps; cleared by any other command): `k = 32 - flag; LOPER = 14*(k-20) + 5*20 if k>20 else 5*k` (computed as loop: while k>20: +14,k--; then +5 per remaining k). Plays one 0.44 s CABSHK sweep then loops forever with same LOPER until next command; with 10 repeats from the game (one per frame) the pitch walks.
- **BG2 (N=16, via BG2INC)**: flag 1..29 (wraps), TRBV with `FOFSET = ~(flag<<2)` (so period = pattern - 4*flag - 1) repeating the 9-step pattern forever; higher flag = higher-pitch "turbine". The Defender game source does not send $10; skip unless wanted.

### 4.3 VARI (variable-duty square wave sweeps)
9-byte vectors: `LOPER, HIPER, LODT, HIDT, HIEN, SWPDT(16-bit, hi first), LOMOD, VAMP`:

| N | name | LOPER | HIPER | LODT | HIDT | HIEN | SWPDT | LOMOD | VAMP |
|---|---|---|---|---|---|---|---|---|---|
| 29 | SAW | 40h | 01 | 00 | 10h | E1h | 0080h | FFh(-1) | FF |
| 30 | FOSHIT | 28h | 01 | 00 | 08 | 81h | 0200h | FFh | FF |
| 31 | QUASAR | 28h | 81h | 00 | FCh(-4) | 01 | 0200h | FCh(-4) | FF |
| (SP1) | CABSHK | var | 01 | 00 | 18h | 41h | 0480h | 00 | FF |

```
VARI:                                     # DAC toggles between VAMP and ~VAMP (00/FF for all)
 snd = VAMP ; DAC=snd
 VAR0: LOCNT=LOPER ; HICNT=HIPER
  V0:  X = SWPDT                          # sweep step length in "ticks"; 1 tick = 14 cycles
       forever:
         snd ^= 255 (edge)      ; low  phase: LOCNT ticks (0 means 256)
         snd ^= 255 (edge)      ; high phase: HICNT ticks (0 means 256)
         every tick: X -= 1 ; if X==0: break out immediately (mid-phase)  -> VSWEEP
       one period costs 14*(LOCNT+HICNT)+~22 cycles ; freq = 894886/(14*(LO+HI)+22)
  VSWEEP: if snd < 128: snd = ~snd ; DAC = snd            # forces the 'high' level
          LOCNT += LODT ; HICNT += HIDT  (8-bit)
          if HICNT != HIEN: goto V0                       # next sweep step (~SWPDT*14 cycles each)
  if LOMOD==0: return
  LOPER += LOMOD ; if LOPER==0: return ; goto VAR0
```
Durations: SAW 1.87 s, FOSHIT 5.31 s, QUASAR 2.64 s, CABSHK 0.44 s (per call). FOSHIT = rising-pulse-width sweeps getting higher (free ship). Each step is 14*SWPDT cycles (FOSHIT/QUASAR 8 ms, SAW 2 ms, CABSHK 1.3 ms... = 1152 ticks => 18 ms).

### 4.4 NOISE (TURBO) - amplitude+rate-decaying white noise
```
TURBO: decay=1, X=1 (delay param), amp=$FF, CYCNT=32 samples/step, NFFLG!=0
 loop: repeat CYCNT: bit=rnd(LO); DAC = amp if bit else 0 ; wait ~ 50 + 8*X cycles   # sample period = 50+8X cycles
       amp -= decay ; if amp==0: return ; X += 1 (because NFFLG)       # 255 steps
```
Sample period grows linearly (15 kHz -> 0.4 kHz), amplitude drops linearly; total 9.8 s (but the game only lets it be heard until the next command; laser = first ~0.77 s: noise zap that descends in pitch while amplitude is still >70%).

### 4.5 LITE / APPEAR - random-toggle noise with swept rate
```
LITEN(lfreq, dfreq, cycnt): DAC=$FF
 loop: repeat cycnt: if rnd(LO): DAC ^= 0xFF ; wait 36+6*lfreq cycles      # lfreq=0 means 256
       lfreq += dfreq ; if lfreq==0: return
LITE:   lfreq=1,   dfreq=+1,  cycnt=3    -> 0.69 s, harsh noise whose toggling slows from ~15 kHz to ~0.6 kHz  (lightning, explosion rattle)
APPEAR: lfreq=$C0, dfreq=-2,  cycnt=16   -> 1.07 s, noise whose rate rises (delay shrinks from 192 -> 2)       (appear/materialize)
```
Output only 0x00/0xFF.

### 4.6 FNOISE (filtered noise: random-target ramps) - THRUST, BG1, CANNON
```
FNOISE(SAMPC=X, FMAX, FDFLG, DSFLG):   FLO=0 ; A = DAC (last value)
 FNOIS0: X=SAMPC; A=DAC
  FNOIS1: rnd(A) ; FHI = FMAX & HI if DSFLG else FMAX ; target = LO ; B=FLO
     ramp toward target at slope FHI:FLO/256 per sample (16-bit fixed point, B holds the fraction):
        each sample: X-=1 (if 0 -> FNOIS6); DAC=A ; A,B += or -= (FHI,FLO)  ; stop when passing target or overflow
        sample cost 30 cycles (29.8 kHz)
     at target: A=LO; DAC=A; (≈70 cycles of overhead) ; new random target
  FNOIS6 (after SAMPC samples): if FDFLG==0: continue forever (X wraps, 65536 more)
     else  D=(FMAX<<8|FLO); D -= D>>3  (x7/8) ; FMAX,FLO=D ; if FMAX==0 and FLO==7: return
```
- THRUST (N=22): FMAX=3, DSFLG=0, FDFLG=0 -> forever. Slope 3 DAC counts/sample => random walk with ~85-sample ramps (a low rumble/hiss; spectrum roughly 1/f^2 up to ~3 kHz).
- BG1 (N=15, thrust-off background): FMAX=1 (slope 1 count/sample, ramps up to 255 samples = deeper rumble), forever, sets BG1FLG so it restarts after interrupts. Both are loud at full DAC swing (no volume scaling in code).
- CANNON (N=23): SAMPC=1000, FMAX=$FF, FDFLG=1, DSFLG=1 -> each ramp has a random slope (HI & $FF) i.e. unlimited-slope white-ish noise at the start; every 1000 samples the max slope decays by 7/8 until D=7 (~68 steps, ~2.5 s) => the big explosion boom: noise sweeping from full band to a very smooth low rumble, ending at slope 7/256 per sample.

### 4.7 HYPER (coin sound, N=25)
Sub-audio PWM: 128 cycles, each with 128 time steps of 123 cycles (+6 on edge) = ~15.7k cycles/cycle (57 Hz). In each cycle DAC toggles at step `TEMPA` and again at cycle end; TEMPA rises 0..127 across the sound => pulse width sweeps 100% -> 0%. Total 2.26 s. `snd=0; for tempa in 0..127: for a in 0..127: if a==tempa: snd^=255 ; wait 115 cycles ; end: snd^=255`.

### 4.8 RADIO (lander grab, N=24)
Phase-accumulator with 16-bit increment that itself increases:
```
freq=100 ; phase=0 (16-bit)
loop: phase += freq ; if carry out of 16 bits: freq += 1 ; if freq==0x10000: return
      DAC = RADSND[(phase>>8)&15] ; wait to make 60 cycles/sample (14.9 kHz)
RADSND = 8C 5B B6 40 BF 49 A4 73 73 A4 49 BF 40 B6 5B 8C     (jagged "sine", amplitude 0x40..0xBF)
```
Start pitch = 14.9k*100/4096 = 364 Hz (note: table repeats every 4096 phase counts); pitch rises ever faster (aliases above Nyquist) and the full run would be ~28 s; only the first fraction of a second matters in play. Output swing is half-scale (0x40-0xBF).

### 4.9 SCREAM (astronaut scream, N=26)
Four square-wave "echo" voices, amplitudes $80/$40/$20/$10 summed into the DAC:
```
freq=[0x40,0,0,0]; timer=[0]*4
repeat:
  for step in 0..255:                    # ~215 cycles/step => 4.2 kHz update
     B=0 ; amp=$80
     for e in 0..3: timer[e]+=freq[e] (8-bit) ; if timer[e]&0x80: B+=amp ; amp>>=1
     DAC=B
  for e: if freq[e]: if freq[e]==0x37: freq[e+1]=0x41 ; freq[e]-=1 ; any_nonzero=True
  until all freq==0
```
Voice pitch = 4.2k*freq/256 Hz; starts 1040 Hz ($40) falling one step per 256-sample pass (61 ms), each next echo starts 9 passes later at $41 slightly above the previous; ends ~5.9 s (truncated by landing/hit sounds).

### 4.10 ORGAN (not used by Defender game; tunes PHANTOM/TACCATA in ROM)
Counter TEMPB increments each sample; DAC = popcount(TEMPB & OSCIL)<<4; note pitch via NOP delay chain; tune table has 4-byte entries (osc mask, delay, duration). Skip.

## 5. Per-effect durations / timing summary (from `defsound_ref.py`)

| Effect | Natural length | Notes |
|---|---|---|
| LITE | 0.69 s | |
| APPEAR | 1.07 s | |
| TURBO (laser/ terrain blow start) | 9.8 s | cut by next cmd (laser: heard ~0.8 s) |
| CANNON | ~2.5 s | |
| HYPER (coin) | 2.26 s | |
| SCREAM | 5.9 s | |
| RADIO | ~28 s | cut quickly |
| THRUST / BG1 | endless | |
| FOSHIT 5.3 s, QUASAR 2.6 s, SAW 1.9 s, CABSHK 0.44 s | | |
| GW1 1.2 s, GW3 0.16 s, GW5 5.3 s, GW6 0.6 s, GW7 1.1 s, GW8 0.22 s, GW10 3.2 s, GW11 0.84 s, GW12 0.6 s, GW13 2.1 s, BON2 pass 0.25 s | | GW2/GW4/GW9 > 12 s (255 sweep passes: STDV, XBV, CLDWNV) |

Game-side playback lengths come from the sequencer timers in section 3 (16 ms ticks), i.e. a faithful player sends the next command on schedule and the previous routine is simply cut.

## 6. Reference implementation notes (`defsound_ref.py`)

- `Board(max_cycles)`: records `(cycle, dac)` events; `b.out(v)`, `b.tick(cycles)`, `b.rnd(A)` LFSR.
- Routines: `gwave(b, idx0)` (idx0 = N-1 for N<=13, 13 = BONV, 14 = TRBV via `bg2_loop`), `vari(b,'SAW'|'FOSHIT'|'QUASAR'|'CABSHK')`, `sp1(b, flag)`, `lite`, `appear`, `turbo`, `thrust`, `bg1`, `cannon`, `hyper`, `radio`, `scream`.
- `render(b, rate)` -> float array in [-1,1], area-averaged. Run offline once per effect and cache (Python event loops: tens of thousands of events per second of audio; seconds to run for long effects; use `max_s`), then play via `pygame.mixer.Sound(array=int16)`.
- Caveats: (1) cycle counts hand-derived, ROM binary not disassembled; (2) initial LFSR LO and initial DAC value (FNOISE reads the port) are unknowable (power-up RAM), chosen arbitrarily; (3) game cut-offs (priority/pre-emption) belong in the game-side sequencer; (4) MAME's DAC output has no analog filter, so a mild lowpass (~8-10 kHz) on the cabinet amp is an optional polish; (5) in Defender, the HBESND pattern length 15 reads one byte beyond its label into SPNR ($40) and ED17's 4-byte pattern reads into COOLDN; the .py keeps this by concatenating tables in ROM order.
