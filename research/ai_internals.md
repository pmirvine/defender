# Defender (Williams 1981) internals for a faithful Python/pygame-ce recreation

Primary source: github.com/historicalsource/defender (Red Label 6809 source; cloned and read directly:
DEFA7.SRC main/exec/player/shells/collision/hyper, DEFB6.SRC enemies+graphics, BLK71.SRC terrain + wave table,
AMODE1.SRC scanner, PHR6.SRC RAM map/equates, ROMC8.SRC CMOS defaults). All numbers are read from that source unless tagged
[INFERRED] or [UNVERIFIED]. Sean Riddle's pages / Computer Archeology could not be retrieved via search (nothing usable returned);
nothing here relies on them.

Source terminology: "UFO" = Baiter, "TIE" = Bomber, "PROBE" = Pod, "SWARM" = Swarmer, "SCHITZO/SCZ" = Mutant,
"ASTRO/EARTHLING" = Humanoid, "BOMB/SHELL" = enemy bullet.

---------------------------------------------------------------------------------------------------
## 1. Timing and scheduler

* One game tick = one video frame (~16 ms; source: "SLEEP TIME X 16MSEC"). Target 60 Hz. The EXEC loop spins on `TIMER` (incremented once per
  frame by the IRQ), then: collision check, explosion update, one RAND call, switch processing, process dispatcher.
* Cooperative processes: singly linked list `ACTIVE`; each has PTIME countdown, PADDR resume address, PD.. data. `NAP n,addr` / `SLEEP` = resume after
  n ticks; dispatcher does `DEC PTIME; if 0 run` once per frame. `MKPROC/NEWP` inserts after the current process; `SUCIDE` = kill self; `GNCIDE` = kill all but self.
  In Python: one generator per entity, `yield n` = nap n frames.
* Per-frame object update:
  - `VELO` (IRQ): for every active object `OX16 += OXV` (16-bit wrap), `OY16 += OYV`; if `OY16.hi < 42` set hi=240; if `> 240` set hi=42
    (vertical wrap, no bounce).
  - `OPROC`: erase old sprite, draw new sprite if on screen. Shells handled separately (section 8).
  - Inactive list (`IPTR`): objects outside the window are moved by `ISCAN` every 8 ticks by 8*velocity (same world speed). Active window:
    `(OX16 - (BGL - 100*32)) mod 65536 < 500*32`, i.e. from 100 px left of the screen edge to 400 px right of it.
* Overload protection (`OVCNT`): if frame work runs long, star count cut to 3 and first OTYP==0 object is "hypered" away (+`($SEED&$3F)+$60`<<8 in X) to the inactive list.
  A fixed-timestep Python port can ignore this.
* GEXEC (game executive) sleeps 15 ticks (0.25 s) per pass; most wave timers count these passes.

## 2. Number formats and coordinates

| Thing | Format | Notes |
|---|---|---|
| World X `OX16` | 16-bit unsigned, **32 units = 1 px** | world = 65536/32 = **2048 px wide**, wraps mod 65536 |
| World Y `OY16` | 16-bit **8.8**, hi byte = pixel y | playfield y = 42 (`YMIN`) .. 240 (`YMAX`); y grows downward |
| Velocity X | signed 16-bit, 32 = 1 px/tick | |
| Velocity Y | signed 16-bit 8.8, 256 = 1 px/tick | |
| Screen X (`OBJX`) | byte column, **1 byte = 2 px** (4 bpp) | `OBJX = (OX16 - BGL) / 64`; valid if `(OX16-BGL) < 150*64` (300 px); screen RAM columns $00..$9B (~312 px; visible ~292 [UNVERIFIED]) |
| Screen Y (`OBJY`) | `OY16.hi` | |
| Player `PLAXV` | 24-bit signed, hi 16 bits used for scroll | section 3 |
| Shell `OX16/OY16` | **screen space**: X = 8.8 in screen bytes, Y = 8.8 px | corrected for scroll every frame |

`BGL` = world X (1/32 px) of screen left edge. Absolute ship X `PLABX = BGL + ((PLAX16>>2) & $FFE0)` where `PLAX16` hi byte is the ship's screen column (so ship at column $20 -> ~ +$800).
Enemy AI always compares world X with `PLABX`.

Python: `x` int mod 65536 (1/32 px), `y` int (1/256 px). Wrap-aware signed distance: `((a-b+32768)&0xFFFF)-32768`. The source uses unsigned window tests, e.g.
`(PLABX - OX16 + 150*32) < 300*32` == "within +-150 px of ship".

## 3. Player ship (PLAYER routine, once per frame)

Horizontal (24-bit velocity V, V16 = hi 16 bits):
* Damping each tick: `V -= V/64` (code: add `-V16*4` at 1/256 scale).
* Thrust held: `V += $0300` (24-bit units) in `PLADIR` sign. Terminal V16 = $0300*64/256 = **$C0 (192)**; V16 clamped to +-$0100.
* World scroll: `BGL += V16 - BGDELT`. Max scroll ~ 192/32 = **6 px/tick = 360 px/s** at full thrust.
* Ship's screen column target (`PCX`): base **$20 facing right / $70 facing left** (bytes) plus roughly `V16/8` bytes in the direction of motion (zero if V opposes facing).
  `PLAX16` slews toward target at most `$100` (1 byte = 2 px) per tick; while slewing the scroll is adjusted by `BGDELT = +-$40` (2 px/tick).
  Net feel: ship slides forward on thrust, drifts back when reversing.
* Reverse: `PLADIR = -PLADIR`, needs release (debounce + 5 ticks). Ship image `PLAPIC`/`PLBPIC`, 8x6 bytes = 16x6 px.
* Vertical (8.8): up: starts -$100 (1 px/tick), then -8/tick to -$200 (2 px/tick); down mirrored; **released = velocity 0 immediately**. Blocked at `y<=43` (up) and `y>=238` (down).
* Start: `PLAX16=$2000`, `PLAY16=$8000` (y=128), facing right, `BGL=0`.
* Lasers: max 4 at once (`LFLG`). Each laser is a process stepping every tick: head advances **4 byte columns (8 px) per tick**, tail erases 1 column per tick; ends at screen edge ($9800 / $0500) or on hit.
  Starts at ship +7 columns (right) / +4 (left), y+4. Hit test each tick = `COLIDE` of `LASP1` (8x1 bytes) against all objects. Lasers also destroy enemy shells (25 pts).
* Smart bomb: start with 3; calls every on-screen (`OBJX!=0`) object's kill vector when `OTYP < 2` (astronauts $10 immune); 4 screen flashes (2-tick each); needs button release.
* Hyperspace (`HYPER`; blocked if `STATUS & $FD`): clears all shells; `BGL = (SEED:HSEED)` random world position; random facing; `PLAX16` = $2000 or $7000; `y = (HSEED>>1)+42`; velocities zero;
  15-tick wait, 40-tick ($28) "appear" animation, then **if `LSEED > 192` the ship dies** -> 63/256 = **24.6 % death**. Enemies are not moved.
* Game start: 3 ships (`NSHIP` CMOS default 3), 3 smart bombs, 10 astronauts. Replay level gives +1 ship +1 smart bomb (replay score value [UNVERIFIED]).

## 4. Terrain

* `TDATA` = **256 bytes = 2048 bits**, 1 bit per pixel across the entire 2048 px world, MSB first. Bit 1 -> terrain y **-1** (up), bit 0 -> y **+1** (down). Start altitude $E0 (224). The profile closes exactly after 2048 steps (ends at 224): seamless wrap.
* Altitude table `ALTTBL` (for `GETALT`): 1024 entries, one per **2 px** (`index = OX16>>6`); entry = altitude before consuming that cell's 2 bits. Verified range **160..232**.
* Terrain drawn 1 px per column with two flavours by `BGL & $20`.
* Scanner mini-terrain `MTERR` is a 64-column pre-baked version (1 column per 32 world px).
* When the last astronaut dies: `TERBLO`: STATUS bit1 (terrain off), terrain+scanner terrain erased, 16 iterations of 2 random explosions on the terrain each, random background flash colour,
  random sleep `RMAX(1+iter/8)*2` ticks, `TBSND` at end. Remaining landers become mutants. Astronauts restored to 10 every `GA4`=5th wave.

TDATA (BLK71.SRC):
```
2A AA AA AA AA AA AB A1 D5 55 55 55 55 55 AA BF FF FF FF C0 00 00 00 55 55 57 FF C0 01 55 55 55
55 55 55 5F E0 15 55 55 57 FF F0 00 15 55 5F FF FF FF FF 00 00 00 00 05 55 7F FF E0 00 05 55 55
55 55 FC 05 55 55 50 01 FF FF FF C0 00 0A AA AA AA FF 00 00 FF FF FF FF F0 00 00 1F E0 00 55 55
55 40 AA AA AA AA AA AA B5 57 AA AA AA F5 7F D5 55 55 57 FF 80 07 E0 7F F1 55 7F FF FF 00 00 00
00 00 0F EF 76 91 11 11 5E DB E9 84 77 EC C4 87 47 98 08 98 3F C3 CB DB 9F C7 5F 2F C7 7D EF BF
FA 4C 57 2B 61 EF EF FB F7 E8 00 20 40 00 14 04 04 3C 06 00 1D 07 3C E1 A5 55 55 45 2A AA AA AA
A8 55 55 55 55 55 55 55 55 55 55 56 AA AA FE AA AA AA AA AA AA AA AA EA AA AA A8 02 AA AA AA AA
BF BE 3E 63 FF E0 D8 1C 18 2A AB 1E 77 7A AF A8 40 70 7D 40 0B FB FA FF C1 53 54 75 70 03 00 00
```
```python
def build_alt(tdata):                       # returns 1024 altitudes (verified: min 160, max 232)
    bits=[(b>>(7-i))&1 for b in tdata for i in range(8)]
    y=0xE0; alt=[]
    for k in range(0,2048,2):
        alt.append(y)
        for j in (0,1): y += -1 if bits[k+j] else 1
    return alt                              # altitude(worldx32) = alt[(x>>6)&1023]
# per-pixel profile h[0]=224; h[i+1]=h[i]+(-1 if bit[i] else +1)
```

## 5. Scanner

* 64 byte-columns = **128 px wide**; `col = ((OX16 - scanner_left) >> 10) & 63` = 1024 world units (32 px) per byte column = **16 world px per scanner px**; whole world fits.
  Row = `OY16.hi >> 3` (**8:1 vertical**; y 42..240 -> rows 5..30).
* `scanner_left = BGL - ($8000 - 150*32)`: scanner is **centred on the screen centre**; scanner column 32 = screen centre; world wraps around the window.
  Player blip uses ship screen coords: `(PLAXC.hi>>4, PLAXC.lo>>3)` on the scanner.
* Blips are 2x2 px, colour from `OBJCOL`: lander $4433, mutant $CC33, baiter $3333, bomber $8888, pod $CCCC, swarmer $2424, astronaut $6666. Active and inactive lists both drawn.
  Bezel with two window markers.
* Redrawn by `SCPROC` every 8 ticks (cycle: ISCAN, nap2, OSCAN+SHSCAN, nap2, scanner, nap4).

## 6. Random number generator (`RAND`)

3 state bytes `SEED`, `HSEED`, `LSEED`; init `HSEED=$A5`, `LSEED=$5A`, `SEED=0`. RAND is called once per frame in EXEC plus every use. AI code often reads `SEED/HSEED/LSEED` directly without calling RAND again.
```python
class Rand:
    def __init__(s): s.seed=0; s.h=0xA5; s.l=0x5A
    def rand(s):
        b=(s.seed*3)&0xFF; b=(b+17)&0xFF            # LDB SEED; LDA #3; MUL; ADDB #17
        a=s.l
        a=(a>>3)^s.l                                 # 3x LSRA; EORA LSEED
        carry=a&1; a>>=1                             # LSRA
        c=s.h&1; s.h=(carry<<7)|(s.h>>1)             # ROR HSEED
        s.l=(c<<7)|(s.l>>1)                          # ROR LSEED (carry from HSEED bit0)
        t=b+s.l; b=t&0xFF; carry=t>>8                # ADDB LSEED
        b=(b+s.h+carry)&0xFF                         # ADCB HSEED
        s.seed=b; return b
```
(Derived by reading; confirm in a 6809 emulator if bit-exactness matters.)
`RMAX(a)`: `r=rand(); while r>a: r>>=1; return r+1` -> range 1..a+1, skewed low (not uniform).

## 7. Wave data and difficulty (BLK71.SRC `WVTAB`)

Each row: `MAX, MIN, INTRA_DELTA, INTER_DELTA`, then values for waves `W1..W4` (wave clamped to 4 for lookup).

| # | parameter | MAX | MIN | intra | inter | W1 | W2 | W3 | W4 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | landers (reserve) | 20 | 0 | 0 | 0 | 15 | 20 | 20 | 20 |
| 2 | bombers | 3 | 0 | 0 | 0 | 0 | 3 | 4 | 5 |
| 3 | pods | 6 | 0 | 0 | 0 | 0 | 1 | 3 | 4 |
| 4 | mutants | 10 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 5 | swarmers | 10 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 6 | WAVTIM (x15 ticks between lander squads) | 30 | 0 | 0 | 0 | 30 | 25 | 20 | 16 |
| 7 | WAVSIZ (landers/squad) | 5 | 0 | 0 | 0 | 5 | 5 | 5 | 5 |
| 8 | LNDXV (lander x speed cap, 1/32 px/tick) | $60 | 0 | +3 | +2 | $16 | $1E | $26 | $2E |
| 9 | LNDYV hi | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 1 |
| 10 | LNDYV lo | $FF | 0 | +$10 | 0 | $70 | $B0 | $00 | $00 |
| 11 | LDSTIM | $80 | $10 | -4 | -2 | $4A | $3A | $2A | $2A |
| 12 | TIEXV | $30 | 0 | 0 | 0 | $20 | $28 | $2C | $30 |
| 13 | SZRY (px) | 2 | 0 | 0 | 0 | 1 | 1 | 2 | 2 |
| 14 | SZYV hi | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 1 |
| 15 | SZYV lo | $FF | 0 | +8 | +6 | $62 | $E0 | $02 | $12 |
| 16 | SZXV | $60 | 0 | +8 | +4 | $0C | $1C | $24 | $28 |
| 17 | SZSTIM | $FF | $08 | -2 | -2 | $2A | $22 | $1E | $1C |
| 18 | SWXV | $60 | 0 | +8 | +2 | $16 | $1E | $20 | $22 |
| 19 | SWSTIM | 40 | 10 | -2 | -1 | 25 | 25 | 25 | 25 |
| 20 | SWAC (y accel mask) | $3F | 0 | 0 | 0 | $1F | $1F | $1F | $3F |
| 21 | UFOTIM (baiter timer, x15 ticks) | $C0 | $18 | -12 | -4 | $D4 | $C4 | $A4 | $94 |
| 22 | UFSTIM (baiter shot timer) | 10 | 3 | -1 | -1 | 15 | 13 | 12 | 10 |
| 23 | UFOSK (baiter no-reaim threshold /256) | 200 | 40 | -12 | -8 | 240 | 220 | 200 | 200 |

Rows 9/10 and 14/15 are hi/lo bytes of one 16-bit 8.8 value.

Delta rule (`WDELT`): apply delta only if the result stays inside [MIN, MAX] (no overflow); otherwise the value is left unchanged (it freezes, not clamps).
* **Intra-wave**: every 40 GEXEC passes (600 ticks = **10 s**) apply INTRA deltas to the live params; the drift is saved on death.
* **Inter-wave** (`GETWV`): load the W column, then apply INTER deltas `n = min(GA1 + max(wave-4,0), GA2)` times; CMOS defaults **GA1=5, GA2=15** -> every wave, even wave 1, gets 5 steps
  (wave 1: LNDXV $16+10=$20, LDSTIM $4A-10=64, UFOTIM $D4-20=192, UFOSK 240-40=200, SWXV $16+10=$20, SZXV $0C+20=$20...). Wave w>=4 gets min(w+1,15) steps; difficulty stops rising at wave 14. Counts have zero deltas so composition freezes at W4 (20 landers, 5 bombers, 4 pods).
* Astronauts: restored to 10 whenever `wave % GA4 == 0` (`GA4=5`), else carried over.
* Wave complete when `LNDCNT+LNDRES+TIECNT+PRBCNT+SWCNT+SCZCNT+SCZRES == 0` (baiters do not count). Bonus = astronauts alive x `min(wave,5)` x 100, 4-tick pause per astronaut, ~128-tick hold.
* Wave start: reserves restored: swarmers 6 at a time near ship, mutants, pods, bombers in squads of up to 3, landers via GEXEC.
* GEXEC lander spawning (each 15 ticks): `WAVTMR--` (initial 1 -> immediate squad); when 0 or when `LNDCNT==0`: reload `WAVTIM`; if `LNDRES>0` and `LNDCNT<8` spawn `min(WAVSIZ,LNDRES)` landers. Wave 1 -> a squad of 5 every 30*15=450 ticks (7.5 s) or sooner when none alive.
* Baiter timer: `UFOTMR` starts at UFOTIM, `--` each pass. With `A` = enemies left: if A<=8 `UFOTMR=min(UFOTMR, UFOTIM/2+1)`; if A<=3 `/4+1`. At 0: reload `UFOTIM` (A>=4) or `RMAX(UFOTIM/4)`; spawn if `UFOCNT<12`.
  Wave 1 first baiter after 192*15 = 2880 ticks = **48 s**.
* Terrain/wall colour `WCTAB[(wave&7)-1]` = $81,$28,$07,$16,$2F,$84,$15.

## 8. Shots

* Max simultaneous shells **20** (`BMBCNT`; bomber mines only start while `BMBCNT<10`). A shot needs the shooter on screen and `y>YMIN`.
* Default shell life `ODATA=20` passes of `SHSCAN` (every 8 ticks) = ~160 ticks; shells die leaving the screen. Shell sprite `BMBP1` 2x3 bytes (4x3 px).
* **`SHOOT` (landers, mutants, baiters) - aimed shot**:
  ```
  dx = (PLAXC - OBJX_shooter) [screen bytes] + ((SEED&$1F)-$10)      # +-16 bytes = +-32 px error
  vx = 4*dx                                                          # 8.8 bytes/tick -> arrives in 64 ticks
  if SEED > 120 (~53%): vx += 4*PLAXV16                              # lead the ship
  dy = (PLAYC - OBJY_shooter) + ((LSEED&$1F)-$10)                    # +-16 px error
  vy = 4*dy                                                          # 8.8 px/tick -> arrives in 64 ticks
  ```
  Flight time to aim point is always ~64 ticks (1.07 s). Accuracy does NOT improve with wave; difficulty comes from shot frequency and enemy speed.
* **Swarmer shot (`SWBMB`)**: only when moving toward ship (`sign(PLABX-OX16)==sign(OXV)`); `vx = 8*OXV` (shell units, ~2x swarmer's px speed), `vy = dy*8` (8.8). Timer `RMAX(SWSTIM)` per 3-tick pass.
* **Bomber mine**: velocity 0 (world-fixed), life `(SEED&$1F)+1` scan passes = 8..256 ticks, colour cycling (`CBOMB`).

Firing timers (reload = `RMAX(timer)`):
| Enemy | var | counted per | ticks | wave-1 base | wave-1 effective (+5 inter steps) |
|---|---|---|---|---|---|
| Lander | LDSTIM | `LSHOT` call: 6 ticks seeking, **1 tick descending**, 4 ticks fleeing | 6/1/4 | $4A=74 | 64 |
| Mutant | SZSTIM | `SCZ0` pass | 3 | $2A=42 | 32 |
| Baiter | UFSTIM | UFO pass | 6 | 15 | 10 |
| Swarmer | SWSTIM | swarm pass | 3 | 25 | 20 |
| Bomber | `(LSEED&7)==0` per TIE update while on screen (1/8) | | | | |

Landers do not shoot during the appear animation.

## 9. Enemy AI

### 9.1 Lander
Spawn (after appear animation): `x=(HSEED:LSEED)` random anywhere, `y=44`, `OYV=LNDYV` (8.8, wave 1 = $0070 = 0.44 px/tick), `OXV=+-RMAX(LNDXV)` (sign = bit 0), shot timer `RMAX(LDSTIM)`, target = next live astronaut in `TLIST` round-robin (`GTARG`). If `ASTCNT==0` a mutant spawns instead.
1. **Seek** (nap 6): constant x velocity (no x steering). Vertical: `d = alt(x) - 50 - y`; `d>0` descend `+LNDYV`; `-20<=d<=0` hold `OYV=0`; `d<-20` climb `-LNDYV` => hovers 30..50 px above ground. Retarget if target dead/captured.
   Begin grab when `(lander.x.hi & $FC) == (astro.x.hi & $FC)` (same 32 px cell; hi byte = 8 px).
2. **Descend** (`LANDG`, every tick): velocity 0, `OTYP|=1` (hyperspace-safe); x steps `$20` (1 px/tick) toward astro until `x&$FFE0` equal; y steps `LNDYV` toward `astro.y-12`; shoots. Grab when y matches and `(lander.x+$40-astro.x) <= $80` (unsigned): sound LPKSND, lander kill vector -> `LKIL1`, astro -> `AKIL1`, both `OYV=-LNDYV`.
3. **Flee** (nap 4): rises with astro at LNDYV until `y <= YMIN+8 = 50`; shoots.
4. **Pull in**: both stop, astro raised 1 px/tick to lander; astro explodes, `LNDCNT--`, `SCZCNT++`, lander becomes **Mutant** (sprite `SCZP1`, colour $CC33, kill 150, timer SZSTIM). If target vanished earlier it goes back to reserve (`LNDRES++`).
5. Lander shot while carrying: astro released, falls `OYV += 8`/tick (cap $300). Lands: if `OYV <= $E0` (0.875 px/tick) safe -> 250 pts; else dies. If the player touches the falling astro, it is caught (sound, 500-pt process), follows the ship at `(PLABX+$80, PLAYC+10)` until it touches ground, then 500 pts and walks again.
Kill 150.

### 9.2 Astronaut (nap 2)
Walks on terrain, only updated if on screen and not captured: x `+-$20` (1 px) per update, turn around when `SEED<=8` (3 %); y toward `alt+4` (left) / `alt+15` (right), cap $E8, 1 px per update; 2 anim frames. Initial placement 10 astronauts: N/4 per world quadrant (high-quartile bases $00,$40,$80,$C0) + remainder; `y=$E0`, OTYP $10 (not collidable by enemies/laser, immune to smart bomb).

### 9.3 Mutant (nap 3)
Spawn: converted lander, or `SCZST`: x random but not within +-300 px of the ship (hole pushed by `+$8000`), `y=(SEED>>1)+42`.
Each pass:
1. `OXV = +-SZXV` toward ship (re-evaluated every pass: perfect x homing). Wave 1 eff $20 (1 px/tick); W4 up to $3C (1.9 px/tick); cap $60.
2. If within ~56 px in x (`PLABX-OX16+380 <= $700`): seek ship's y at `SZYV` (wave 1 eff $0080 = 0.5 px/tick), then random hop; else (far): hold y but flee if ship within 8 px above/below (|dy|<=8 -> move away at SZYV), else `OYV=0`.
3. Random y hop: `y.hi += +-SZRY` (sign = bit7 of SEED), wrap at YMIN/YMAX.
4. Shot timer per pass.
Kill 150.

### 9.4 Baiter ("UFO", nap 6, max 12)
Spawn: `x = BGL + ((SEED&$1F)<<8 | HSEED)` (0..256 px from screen left), `y=(HSEED>>1)+42`, first shot timer 8.
Each pass: animate; `PD2--` -> `RMAX(UFSTIM)` + `SHOOT`. Steering `UFONV` runs only if `SEED > UFOSK` (prob (255-UFOSK)/256 per pass: wave 1 eff UFOSK 200 -> 21 %; floor 40 -> 84 %) and always once at spawn:
* X: unless within +-20 px: `OXV = +-$40 + PLAXV16` -> **2 px/tick relative to the ship's own motion** (keeps pace with the player).
* Y: unless within +-10 px: `OYV = (+-$100 + PLAYV)/2`.
Kill 200. Not counted for wave completion.

### 9.5 Bomber ("TIE")
Squad of up to 3 per `TIEST`: x = `PLABX + $8000 + n*1.5*256` (half a world away), y=$50, `OXV=+-TIEXV` (direction alternates per squad, `TFLG`), `OYV=0`. Process runs every tick, picking one of 4 slots at random (`SEED&6`) -> each ship ~every 4 ticks. Per update:
* `OYV += (SEED&$3F)-$20`, then `OYV -= OYV>>5`-style damping; random picture step among `TIEP1..4`.
* Off screen: cruise altitude walks (25 % chance, `+(SEED&3)-2`, clamp $40..$68); `OYV += +-$10` if `|cruise-y|>$10`.
* On screen: keeps 16..32 px vertical offset from ship (pushes `+-$10` toward/away depending on band); **1/8 chance per update to drop a mine** if `BMBCNT<10`.
* No x steering; wave 1 speed eff $20 (1 px/tick), W4 $30.
Kill 250.

### 9.6 Pod ("probe")
Spawn at absolute world `x = (((HSEED&$3F)+$10)<<8 | LSEED)` (128..640 px from world origin), `y=(HSEED>>1)+42`; `OXV=(SEED&$3F)-$20`; `|OYV|` 33..64 (8.8) random sign. No process; just drifts. Kill 1000, spawns `RMAX(6)` (1..7) swarmers at its position (total <=20).

### 9.7 Swarmer (nap 3, max 20)
Spawn: `OYV=2*int8(SEED)`, `OXV=(LSEED&$3F)-$20`, accel `PD2=HSEED&SWAC`, start delay `PTIME=HSEED&$1F`, shot timer `RMAX(SWSTIM)`.
Per pass: x - when starting or when more than 150 px past the ship (`PLABX-OX16+150*32 > 300*32` unsigned), set `OXV=+-SWXV` toward the ship (wave 1 eff $20 = 1 px/tick), else keep going (sweeps through and turns ~150 px later);
y - `OYV += +-PD2` toward ship y, clamp +-$200, damp `OYV -= OYV/64`, jitter `+(SEED&$1F)-$10`; fire `SWBMB` when timer hits 0. Kill 150.

## 10. Collision (`COLIDE`)
1. Box test in screen space (bytes x rows) between the tested picture (ship, shell, or laser tip) and every drawn object (`OBJX != 0`).
2. Overlap region scanned over sprite data: **any overlapping byte pair with both non-zero = hit** (2-px horizontal granularity, 1-px vertical).
3. Calls the object's `OCVECT` kill routine with `CENTMP`=collision address (explosion centre). Player collisions set `PCFLG` first (astronaut catch vs shot; `NOKILL` returns 0).
4. Every frame: ship vs objects, then ship vs shells (`COLCHK`, skipped when STATUS bit4 set e.g. during hyperspace appear). A non-zero return kills the ship; the touched enemy also dies (scores).
Sprite sizes W bytes x H rows: lander 5x8 (10x8 px), mutant 5x8, pod 4x8, bomber 4x8, baiter 6x4 (12x4), swarmer 3x4, astronaut 2x8, bomb 2x3, ship 8x6 (16x6), laser 8x1, explosion 4x8, score popup 6x6.

## 11. Scoring
Lander 150, mutant 150, swarmer 150, baiter 200, bomber 250, pod 1000, enemy shell 25, astronaut: catch/delivered 500, safe landing drop 250, wave bonus astronauts x min(wave,5) x 100.

## 12. Sound
Separate sound board (commands 1..31 via 6-bit PIA). Source gives priority tables (`SNDLD`: `priority, (rep,timer,snd#)*, 0`, equal/higher priority interrupts), e.g. coin `$FF,01,18,19`; extra ship `$FF,01,20,1E`; death `$F0,02,08,11,01,20,17`; terrain blow `$E8,01,04,14,02,06,11,02,0A,17`; smart bomb `$E8,06,04,11,01,10,17`; catch `$E0,03,0A,08`; land `$E0,01,18,1F`; scream `$D8,01,10,1A`; laser `$C0,01,30,14`; lander grab `$C0,01,20,18`; lander suck `$C8,0A,01,0E`. Thrust loops while held. Synth ROM not in repo: synthesize with numpy.

---------------------------------------------------------------------------------------------------
## 13. pygame-ce notes (verified locally: pygame-ce 2.5.8, SDL 2.32.10, Python 3.14 venv)

* `pygame.display.set_mode((292,240), pygame.SCALED, vsync=1)` works; window auto-opened at 3x (876x720); nearest-neighbour scaling; mouse coords auto-mapped. Works with `pygame.FULLSCREEN`. Integer-only scaling hint [UNVERIFIED].
* With vsync on a 120/144 Hz display `Clock.tick(60)` fights vsync: use a fixed-timestep accumulator (logic exactly 1/60 s, e.g. `perf_counter_ns`), render each frame. `Clock.tick(60)` has ms granularity; `tick_busy_loop(60)` is tighter.
* Zero-copy pixel access: `pygame.surfarray.pixels2d(surf)` (32-bit surf, shape OK) and `pixels3d`; `del` views to unlock. 8-bit palette surfaces (`Surface(size, depth=8)` + `set_palette`) suit the 16-colour arcade look. Store sprites as palette-index numpy arrays (2 px/byte layout -> x snapped to even px for authentic look). `pygame.mask` available for collision.
* Audio: call `pygame.mixer.pre_init(22050, -16, 1, 512)` BEFORE `pygame.init()` - in my test `init()` first made a 44.1 kHz stereo mixer and `sndarray.make_sound(1-D)` raised "Array must be 2-dimensional for stereo mixer". Mono: 1-D int16; stereo: shape (n,2). Needs numpy. Use `set_num_channels(16)`, loop thrust with `play(loops=-1)`.
* Install `pygame-ce` only (not `pygame`); wheels exist for Python 3.10-3.15.

## 14. Suggested build order
1. 60 Hz fixed tick, `Rand`, world-x wrap helpers. 2. Terrain from TDATA + alt table + scanner (16:1 x, 8:1 y). 3. Ship physics -> `BGL` scroll. 4. Object list (x 1/32 px, y 1/256 px, vx, vy) with generator processes and the nap rates (lander 6/1/4, mutant 3, swarmer 3, baiter 6, astro 2, bomber 1 with random slot).
5. Wave tables + 5 inter steps + intra every 600 ticks, GEXEC 15-tick spawner, baiter timer. 6. Shots (64-tick aimed flight with +-32/+-16 px error). 7. Collision, smart bomb, hyperspace (24.6 % death), scoring.

## Caveats
* RNG carry details derived by reading; verify with an emulator if exact sequences matter. Screen visible width (292 vs 304) and exact frame rate (60 Hz) are general knowledge, not from this source.
* Ship slew/`PLAXV` arithmetic and the `PLAXV` "lead" term units were derived from assembly; validate by feel (max scroll ~6 px/tick).
* Sound board code not included. Sean Riddle / Computer Archeology pages not cross-checked.
