# Williams Defender (1981) - Gameplay Spec for Faithful Recreation

PRIMARY SOURCE: Williams' original 6809 source (historicalsource/defender on GitHub:
DEFA7.SRC, DEFB6.SRC, BLK71.SRC [wave table], PHR6.SRC [RAM map/equates], AMODE1.SRC [scanner],
ROMC8.SRC [CMOS factory defaults]). Values below were READ FROM THE SOURCE unless marked
**[UNCERTAIN]** (inferred/approximated) or **[WIKI]** (secondary source only).
Sean Riddle's page and the Dot Eaters/Killer List were not fetchable; the source supersedes them.

Conventions: frame = 1/60 s ("tick" in the source = 16 ms). Source pos units: world X is a
16-bit value; **32 units = 1 screen pixel**, 64 units = 1 screen byte (2 pixels). Y is a 16-bit
value whose high byte is the screen row, so **256 units = 1 pixel row**. Velocities are
units/frame (applied once per frame).

---
## 1. World, screen, scanner

- World X: 65536 units = **2048 px**, wraps around (toroidal). Terrain altitude table has 1024
  entries (index = X>>6, i.e. one per 2 px). World = ~6.7 screens wide (screen ~300 px).
- Visible playfield width: objects drawn when 0 <= (X - BGL) < 150*64 units = **300 px**
  (screen byte 0..0x98 = 304 px max). Screen RAM is 304x256 (arcade visible ~292x240).
- Y: playfield rows **YMIN=42 to YMAX=240** (above 42 is score/scanner header). Objects that
  cross YMIN/YMAX wrap to the other limit (VELO: <42 -> 240, >240 -> 42). Ship limited to
  Y in [42..238]. Ground (astronaut walk altitude) capped at Y=$E8 (232).
- Scanner (mini-map): shows the WHOLE world, 64 columns each 1024 units (= 32 px of world) per
  column; 1 column = 2 px wide. Rows = Y>>3 (about 26 rows, y=42..255). Window is offset so the
  screen's centre is at scanner centre (scanner left = BGL - $8000 + 150*32), i.e. the
  scanner scrolls with the player and wraps. Blips are 1 col x 2 rows, coloured per object
  (OBJCOL). Player blip = ship pos. Scanner is ~128 px wide, centred horizontally. Mini
  terrain table is 64x3 bytes. Terrain also shown on scanner (disappears when planet blown).
- Objects far off screen are moved to an "inactive list" and moved at 8x velocity every ~4
  frames (equiv. to normal speed); activated when within (BGL-100*32 .. +500*32) hmm i.e.
  ~100 px left of screen to ~400 px right of screen-left. Practical rule: simulate everything,
  all world positions move continuously.
- Spawn convention: random world X = random 16-bit, Y = 44 for Landers (top).
- Player screen position: ship nose-right rest X = byte $20 (64 px from left), nose-left rest
  X = byte $70 (224 px). Ship slides toward target byte X = base +/- speed/8-ish
  (full thrust right: byte $38 = 112 px; full left mirrored from $70) over a few frames
  (max slide $100 units/frame = 1 byte/frame). **Recreate**: ship screen x lerps between
  ~64px (rest, facing right) and ~112px (full speed right); mirrored when facing left
  ($70 base -> ~ 224px rest, pulling toward ~176 at speed).

## 2. Player ship

Start: **3 ships total (current + 2 in reserve)**, **3 smart bombs** (CMOS NSHIP default 3; bomb
count initialised to the ship count), **10 humanoids**, wave 1.
Replay: **every 10,000 points** (CMOS REPLAY default $0100 -> "10,000"), +1 ship and +1 smart
bomb; next replay level increments by the same amount (10k, 20k, 30k...). Operator-adjustable.
Smart bombs persist across deaths (not reset per life) per source [PSBC kept in player save].

### Horizontal (fixed-point velocity D, units/frame of world scroll, 16-bit signed)
- Each frame: D -= D/64 (drag: "x4 then shift 1 byte" = 4/256). Always applies.
- THRUST held: D += 3 (direction = PLADIR sign; facing right +, left -). (PLADIR=$0300 added
  to low 16 bits of the 24-bit velocity => +3.0 in D units.)
- Terminal speed where 3 = D/64 -> **D = 192 units/frame = 6 px/frame = 360 px/s**
  (hard clamp at +/-256 = 8 px/frame, never reached by thrust alone). Full-speed lap of the
  2048 px world = ~5.7 s. Time constant 64 frames: ~63% of top speed in 1.07 s, ~95% in 3.2 s.
- Releasing thrust: speed decays exponentially (D/64 per frame, ~1 s time constant); ship never
  "brakes" faster. There is NO reverse thrust: "REVERSE" button just flips facing (PLADIR
  negated); existing velocity persists and decays/accelerates in the new direction when
  thrust is applied. Reverse has debounce (REVFLG, must release the button).
- World scroll per frame: BGL += D (minus a small slide term BGDELT = +/-$40 while the ship's
  on-screen slide is catching up with its target position).
- Ship's absolute world X = BGL + (screen-x offset); screen slide is clamped to +/-$100
  (PLAX16 units) per frame.

### Vertical
- Joystick up/down. Pressing a direction: vy jumps to **1 px/frame (=$100)** if it was
  stopped or the other way, then accelerates 8/256 px per frame^2 up to **2 px/frame ($200)**
  (30 frames to reach max, i.e. 120 px/s). Releasing: vy = 0 immediately (no inertia).
- Bounds Y 42..238.

### Laser
- Fire button (one shot per press; trigger needs release - no autofire). **Max 4 lasers
  in flight** (LFLG<4).
- Beam spawns at ship nose (+7 bytes right / +4 bytes left, +4 rows) in the facing direction.
  Each frame the head advances **4 bytes = 8 px** horizontally (drawn as a growing line with a
  flickering "fissle" colour tail pixels). Beam ends on leaving the screen (x byte $98 right /
  $05 left) or on hitting any object. Collision tested each frame at the head
  (3-wide picture). The beam kills exactly ONE enemy (stops at first hit).
  Travel across a full 300 px screen ~ 38 frames/ 0.63 s at 8 px per frame... [UNCERTAIN:
  4 byte columns = 8 px/frame; if columns are 1 px the speed halves].
- Laser is not blocked by terrain. Humanoids ($10 type) are not hit by smart bombs; lasers
  hitting a humanoid kill it (no points, "AKIL10").

### Smart bomb
- Button; needs count>0; decrements by 1; flashes the screen (4 flashes, background colour COM).
- Calls the kill routine of every on-screen object with type <2 (all enemies, baiters,
  mutants, pods, swarmers, bombers; NOT humanoids, which are type $10/$11).
  Each kill awards normal points. Pods hit by smart bomb do NOT release swarmers? [UNCERTAIN -
  in source the pod kill vector (PRBKIL) spawns swarmers regardless, so they ARE released
  and are then not killed since the list iterates; in the arcade swarmers appear after bombing].
- Does not destroy enemy shells/bombs explicitly [UNCERTAIN]; does not hurt the player.
- Debounced (needs button release).

### Hyperspace
- Sequence: screen clears, 15-tick (~0.25 s) pause, all enemy shells killed, bomb count reset.
  Player teleports: new BGL = random 16-bit (random world position; the ship therefore lands
  at random X), random facing (50/50): right -> screen x $20, left -> $70;
  **Y = 42 + rand(0..127) = 42..169**; velocities zeroed.
  Re-materialises with an "appear" animation lasting **$28 = 40 ticks (0.67 s)**; then
  **death roll: if random byte (LSEED) > 192 the ship explodes = 63/256 = 24.6% death chance.**
  Hyperspace disallowed in attract/death states (status mask).
- The ship is invulnerable? No: after reappearing, normal collision applies (death roll happens
  at end of appear). Enemies keep simulating.

### Death
- Collision with any enemy body, fireball or bomb (pixel-mask collision using ship picture) or
  a hyperspace failure kills. Death animation: ship flashes/explodes ~ (color table 9 steps,
  2 ticks each) + 2-tick full-screen white flash, then player explosion.
- On death: remaining enemy counts (active + reserve) are saved and restored on the new life
  (wave is NOT reset; enemies on screen respawn near the ship from the reserve), humanoid
  count preserved (they are re-placed randomly in quadrants). If all enemies were already dead,
  the wave bonus is given before life end.

## 3. Wave table (exact, from BLK71.SRC)

Table row format `max, min, intra-wave delta, inter-wave delta` then `W1,W2,W3,W4`.
Waves >= 4 use the W4 column. Waves 1-3 use W1-W3 (index = min(wave,4)).
After loading, the **inter-wave delta is applied k times**, with
**k = min(GA1 + max(wave-4, 0), GA2)**, where factory GA1 "initial difficulty" = 5 and GA2
"difficulty ceiling" = 15. (So even wave 1 gets 5 applications.) A delta is skipped (value left
as is) if it would exceed max (positive delta) or go below min (negative delta).
Intra-wave deltas are applied to the live values **every 40 x 15 ticks = 9.6 s** of wave time.

Counts (no deltas): 
| Wave | Landers | Bombers | Pods | Mutants at start | Swarmers at start |
|-----:|--------:|--------:|-----:|-----:|-----:|
| 1 | 15 | 0 | 0 | 0 | 0 |
| 2 | 20 | 3 | 1 | 0 | 0 |
| 3 | 20 | 4 | 3 | 0 | 0 |
| 4 | 20 | 5 | 4 | 0 | 0 |
| 5+ | 20 | 5 | 4 | 0 | 0 |
(Baiters are not part of the count; they are timed.) 
Landers are released in squads of WAVSIZ=**5** (all waves). New squad when the squad timer
(WAVTIM x 15 ticks=0.25 s) expires OR when no landers are alive on screen, only if fewer than 8
landers are alive. WAVTIM: w1 30 (7.5 s), w2 25 (6.25 s), w3 20 (5 s), w4+ 16 (4 s).
Bombers come in groups of up to 3 (a 5-bomber wave = 3+2 groups), pods all spawn at once at start.
Pods spawn at world X = left-of-screen + (16..79)*8 px, random Y (they are right-of-screen).
**Wave ends** when landers (alive+reserve) + bombers + pods + swarmers + mutants (alive+reserve)
= 0. Baiters do NOT count (but are removed -- genocide -- at wave end).

### Effective parameters after the inter-wave application (computed from the source)
(values are raw bytes; /32 -> px/frame for speeds; yv in 1/256 px/frame; timers in loop counts)
| Wave | LandXV | LandYV(16b) | LandShotMax | BomberXV | MutXV | MutYV(16b) | MutHopY | MutShotMax | SwXV | SwShotMax | BaiterTimer | BaiterShotMax | BaiterSeek(thr) |
|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
|1|32|$0070|64|32|32|$0080|1|32|32|20|192|10|200|
|2|40|$00B0|48|40|48|$00FE|1|24|40|20|176|8|180|
|3|48|$0100|32|44|56|$0120|2|20|42|20|144|7|160|
|4|56|$0100|32|48|60|$0130|2|18|44|20|128|5|160|
|5|58|$0100|30|48|64|$0136|2|16|46|19|124|4|152|
|6|60|$0100|28|48|68|$013C|2|14|48|18|120|3|144|
|7|62|$0100|26|48|72|$0142|2|12|50|17|116|3|136|
|10|68|$0100|20|48|84|$0154|2|8|56|14|104|3|112|
|15+|76|$0100|16|48|96|$016C|2|8|64|10|88|3|80|
SwAccelMask: $1F (w1-3), $3F (w4+).
Intra-wave drift (per 9.6 s): LandXV +3 (max $60), LandYV lo +$10 (max $FF in low byte),
LandShot -4 (min $10), MutXV +8 (max $60), MutYV +8, MutShot -2 (min 8), SwXV +8 (max $60),
SwShot -2 (min 10), BaiterTimer -12 (min $18), BaiterShot -1 (min 3), BaiterSeek -12 (min 40).
Speeds in px/frame = value/32 (e.g. wave-1 lander horizontal 1.0 px/frame = 60 px/s;
wave-4 1.75 px/frame). Lander descent speed wave 1 = $70/256 = 0.44 px/frame (26 px/s),
wave 3+ = 1.0 px/frame (60 px/s). Hard caps like $60 on LandXV exceed what's reached
(LandXV approaches 76 > $60=96? no: $60=96; 76 < 96 OK).

## 4. Humanoids (astronauts)
- 10 at start; stored per player. **Replenished to 10 at the start of every 5th wave**
  (waves 5, 10, 15, ... : GA4 "restore wave" = 5; code: wave mod 5 == 0 => count = 10) and the
  terrain is restored. Between those they carry over (minus losses).
- Walk along terrain: each humanoid is updated in round-robin (one per 2 ticks over the
  list), moves +/-$20 units (1 px) horizontally per update, turning around with prob ~8/256
  per update, y follows terrain altitude (+4/+15 offset, +/-1 px per update).
- Abducted by Lander: lander and humanoid ascend at the lander's descent speed (LandYV) in
  reverse (same speed up as the lander descends). When the lander reaches Y <= 42+8 it
  "pulls him inside": humanoid removed (killed), lander becomes a **Mutant** (counts move from
  LNDCNT to SCZCNT; keeps position).
- If the abducting lander is shot: humanoid released and falls: accel +8/256 px/frame^2
  (units: +8 per 4 ticks), terminal vy $300 (3 px/frame).
  - On ground contact if vy > $E0 (0.875 px/frame): humanoid dies (explodes) - no points.
  - If vy <= $E0 on landing: survives, **+250** ("250" sprite shown 50 ticks) [source P250].
  - **Catch** by touching with the ship while falling: **+500**; humanoid then rides attached
    to the ship (offset +10 y, x +$80) and when carried down to ground level and released
    (reaches terrain) **+500** again ("500" sprite) and he's placed standing at ground
    (OTYP restored, walking resumes). (Wiki/guides: catch=500, return to ground=500;
    unassisted fall survival 250 only when drop is short.)
  - Falling humanoids are NOT hit by smart bomb and can be killed by laser (no score).
- When last humanoid dies (ASTCNT==0): **planet explodes** (16-step lightning/flash terrain
  explosion ~ 2-3 s; screen flashes, terrain disappears and scanner terrain too). All
  Landers present convert to Mutants immediately; subsequent landers spawn as Mutants
  (LANDST: if no humanoids => SCZST). Terrain remains gone until the restore wave
  (waves 5, 10, ...) when 10 humanoids + terrain return. A wave started with 0 humanoids
  has no terrain, and its "landers" are all mutants.
- Wave-complete bonus: **100 x min(wave,5) per surviving humanoid** (100,200,...,500 each;
  wave 5+ = 500 each), shown "ATTACK WAVE n COMPLETED / BONUS X m", one small astronaut icon
  appears per 4 ticks with the score.
- Target assignment: each Lander picks the next humanoid in a round-robin list (so different
  landers pick different humanoids); if its target dies/is taken it re-picks; if none exists it
  becomes a Mutant.

## 5. Enemies (points = from source SCORE calls)

### Lander - **150**
- Spawns at Y=44, random world X, with random horizontal drift +/-(rand<=LandXV) px, vertical
  descent LandYV. (Appear-in effect first.)
- Behaviour: descends to a hover altitude ~ terrain-50 px (stops descending when within
  20..50 px of that level), keeps x-drift; when horizontally within 4 high-byte units
  (~32 px) of its target it locks on: stops, then aligns x ($20/tick) and descends at LandYV
  until 12 px above the humanoid; touching (within +-$80 units) = grab. Then ascends at LandYV
  until Y<=50 -> mutation (see above). While hunting it fires (LSHOT) at random intervals
  rand(1..LandShotMax) x 6 ticks (wave1 up to 6.4 s) a fireball aimed at the player with
  +-16 px error (lead with 4xplayer velocity if rand>120). (Aimed fireball speed: velocity = 4 x
  dx in bytes per frame **[UNCERTAIN - shell velocity scale]**.)
- Kill: **150**; if carrying a humanoid, humanoid falls (see section 4).
- Lander squads: 5.

### Mutant ("Schitzo") - **150**
- Created from abducting landers (or, when planet gone, directly spawned: random X within
  +-300 px of ... away from the player, Y = 42+rand/2).
- Moves X toward the player at MutXV (wave1 1 px/frame; up to 3 px/frame by wave 15+), flips
  direction instantly each 3 ticks. Y: if |dx|<~ (380..1920 units+) seeks player's Y at
  MutYV, else avoids (moves away vertically when within 8 rows, otherwise hovers); every
  3 ticks adds a random vertical hop +-MutHopY (1-2 px). Fires aimed shots at random
  intervals rand(1..MutShotMax) x 3 ticks (wave 1 <=1.6 s, wave 15+ <=0.4 s).
- Starting count 0 (SCZRES) - only created via abductions / dead planet.

### Baiter (UFO) - **200**
- Spawn timer (decremented each 15 ticks = 0.25 s): initial wave timer = UFOTIM value
  (w1 192 loops = 46 s; w2 176=42 s; w3 144=35 s; w4 128=31 s; decreases per wave/intra).
  When <= 8 enemies (landers+bombers+pods+mutants+swarmers) remain the timer is capped at
  UFOTIM/2+1; <= 3 remain: UFOTIM/4+1 (so baiters come very quickly when you dawdle
  at the end of a wave). After each spawn timer reloads (UFOTIM, or random <= UFOTIM/4 when
  <4 enemies left). Max **12** baiters alive.
- Spawns just right of the screen's left edge: X = BGL + rand(0..31 bytes...), Y random.
- Movement: every 6 ticks, with probability (1 - UFOSK/256) retarget velocity:
  X vel = +-$40 (2 px/frame) + player's X velocity D (so it keeps up with the ship!) unless
  within +-20..+-20 px(20*32 units) hmm: if |dx| < 20 px then X vel unchanged; Y vel =
  (+-1 px/frame + player's vy)/2 unless within +-10 rows. It cycles its 3-frame image.
- Fires aimed shots at rand(1..UFSTIM) x 6 ticks (very frequent: wave 1 up to 1 s,
  w4 0.5 s). Baiters count toward nothing; killing = 200.

### Bomber (TIE) - **250**
- Arrive in formation groups of up to 3 (alternate groups travel left/right), spawn at world X
  = player X + $80 (hi byte) + 1.5*spacing, Y=$50 (80). Constant horizontal speed
  TIE XV ($20..$30 = 1.0-1.5 px/frame), vertical wobbly sine-like drift (random
  accel each frame, plus restoring force toward cruise altitude Y in [$40..$68] = 64-104
  when off-screen; when on-screen, tends to dodge the player's Y).
- Drops stationary-ish **mines/bombs**: each frame, if the bomber is on-screen,
  1-in-8 chance (LSEED&7==0) that the *group* spawns a bomb from a random member;
  max 10 bombs alive; lifetime random 1..32 ticks [UNCERTAIN unit]; bomb drifts slightly.
  Bombs kill the ship on touch; shot-able (shell kill). Bomber count never grows.

### Pod ("probe") - **1000**
- Spawn at wave start (1-4 pods per table). X = screen-left + (16..79)*8 px, random Y,
  random velocity: vx in [-32,+31] units/frame (< 1 px/frame), vy random sign with |vy|>=$20
  units (>=0.125 px/frame), bounces by Y wrap. Pods drift slowly across the screen.
- On kill: releases **rand(1..6) Swarmers [UNCERTAIN distribution; RMAX(6) is biased toward
  smaller numbers]** at the pod's position, max 20 swarmers alive at once. Pods give 1000
  (not 150).

### Swarmer - **150**
- Fast, fires; X velocity SwXV toward the player (wave 1: 1 px/frame; later up to 2 px/frame),
  re-aimed each 3 ticks (reverses to chase). Vertical: accel +-(rand & mask($1F or $3F)) toward
  the player's Y each 3 ticks clamped to +-$200 (2 px/frame), plus damping and random +-16
  jitter -> sinusoidal weave. If it gets 150..300 px past the player it turns around.
- Fires aimed bombs only when moving toward the player, rand(1..SwShotMax) x 3 ticks, shell
  speed = x vel*8, vy = dy>>5.
- Swarmer count persists through death via reserve (SWMRES).

## 6. Scoring summary (BCD, per source)
Lander 150 | Mutant 150 | Baiter 200 | Bomber 250 | Pod 1000 | Swarmer 150 |
Humanoid catch 500 (carried-to-ground drop 500 more) | humanoid safe fall 250 |
wave-end bonus 100 x min(wave,5) per survivor. Smart bombs award the normal value per kill.
Extra ship + bomb each 10,000 points (adjustable).

## 7. Sequence / game flow
1. Start: 3 ships, 3 smart bombs, 10 humanoids, wave 1. (Wave-start screen: "PLAYER 1" prompt
   ~2 s + starting wave sequence.) New life starts at same wave with saved enemies.
2. Game exec loop every 15 ticks (0.25 s): check end-of-wave, baiter timer, lander squad timer,
   star blink, 9.6 s intra-wave difficulty tick.
3. End of wave -> BONUS screen (~2 s) -> next wave: wave++, PWAV recomputed;
   waves where wave %5==0 restore humanoids to 10 and terrain.
4. Game over when ships exhausted. Two-player alternates on death.
5. Per-wave counts persist across a life loss: enemy reserves + alive counts are saved.

## 8. Uncertainties / things not captured
- Exact shell (fireball) velocity scaling/lifetime, and bomber bomb lifetime units.
- Whether smart bomb kills enemy shells/bombs; exact swarmer release count distribution.
- Exact terrain generation (table at ROM $B300, heights ~ Y 200-232) and starfield.
- Ship world speed derived from code analysis (D=192 units/frame, ~360 px/s); verify by
  feel against MAME (world lap should be ~6 s at full thrust).
- Whether laser head is 8 px/frame (4 byte-columns) or less.
- Sound, colours, explosion visuals not documented here.
