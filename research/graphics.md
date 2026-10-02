# Defender (Williams 1981) graphics research

Primary source: github.com/historicalsource/defender (Red Label, cocktail version; files DEFA7/DEFB6/BLK71/MESS0/AMODE1/PHR6.SRC;
the repo has no files named DISPLAY/PHRASE/IMAGES - sprites live in DEFB6.SRC "G R A P H I C S", font in MESS0.SRC, terrain in BLK71.SRC).
Items marked (mem) are from my own knowledge of the hardware/MAME, not verified in this session (web tools were not used); everything else is read from source.

## Display
- Video RAM: 304 x 256 (152 byte-columns x 256 rows), 4 bits/pixel, 16 palette entries (mem; consistent with source: screen addr = $XXYY, XX = byte column 0..$98, YY = row; 1 byte = 2 horizontal pixels, HIGH nibble = LEFT pixel).
- Visible area in MAME: 292 x 240 (x 6..297, y 7..246) (mem). Source constants: YMAX=240, YMIN=42 (top of play area), SCANH=YMIN-34=8 (scanner top row).
- Monitor is rotated, so memory is column-major: sprites stored as W byte-columns of H bytes, top->bottom.
- Palette RAM entry = 8 bits BBGGGRRR (bits0-2 red 3 bits, 3-5 green 3 bits, 6-7 blue 2 bits). Index 0 is transparent in blits.

## Palette (CRTAB in DEFB6.SRC, 'PCRAM' pseudo colour RAM, 16 entries)
| idx | byte | name | approx RGB (r*255/7, g*255/7, b*255/3) |
|---|---|---|---|
| 0 | $00 | space/black | 0,0,0 |
| 1 | $00 | laser (special, cycled in software) | cycles |
| 2 | $07 | red | 255,0,0 |
| 3 | $28 | green | 0,182,0 |
| 4 | $2F | yellow | 255,182,0 |
| 5 | $81 | blue | 36,0,170 |
| 6 | $A4 | gray | 145,145,170 |
| 7 | $15 | brown | 182,72,0 |
| 8 | $C7 | purple | 255,0,255 |
| 9 | $FF | white | 255,255,255 |
| A | $00 | bomb cycler (software-animated) | |
| B | $00 | monochrome (software; scoring/flash) | |
| C | $00 | cycler (software; "DEFENDER" logo letters = $CC) | |
| D,E,F | $00 | TIE1/2/3 (bomber colour cycling; D/E/F used in TIED* sprites) | |
Note: the sprite data above uses indices differently per sprite (e.g. lander body 3 green, 4 yellow; player 6/8/2/9/3 etc.).
Colour cycling tables (DEFA7.SRC COLTAB; written to PCRAM+1 laser colour each frame): $38,$39,$3A,$3B,$3C,$3D,$3E,$3F,$37,$2F,$27,$1F,$17,$47,$47,$87,$87,$C7,$C7,$C6,$C5,$CC,$CB,$CA,$DA,$E8,$F8,$F9,$FA,$FB,$FD,$FF,$BF,$3F,$3E,$3C,0
 (green -> cyan/white -> yellow -> orange/red -> purple -> blue -> ... a rainbow sweep; the laser/smart-bomb flash cycles through these).
Wall/terrain colour per wave (WCTAB): $81,$28,$07,$16,$2F,$84,$15 (blue, green, red, brown-ish, yellow, ...). Terrain normally brown $15 on early waves (mem: brown/orange).
Player explosion colour table PXCOL: $FF,$7F,$3F,$37,$2F,$27,$1F,$17,7,6,5,4,3,2,0 (white -> yellow -> red -> dark -> black fade, 4 frames per colour).
Player glow (PXCTB): 7,7,7,$F,$3F,$7F,$FF,$FF,0.

## Screen layout (source constants; coordinates = byte-column x2 = pixel, row)
- Player 1 score: top-left at $0F1C -> x=30px, y=28; Player 2: $711C -> x=226px, y=28 (cocktail/2P). Digit cell height 4*256 (4 byte columns = 8px wide?).
- Player 1 remaining ships (mini ship icons, 10x4px PLAM0): $0F14 -> x=30, y=20 (above the score). P2 at $7114.
- Smart bomb icons (SBPIC 6x3 px, drawn at 4-column spacing = 8 px, max 3 shown): P1 $291B -> x=82,y=27; P2 $8B1B.
- Scanner: top y=8 (SCANH), bottom y=40; spans byte-columns $30..$6F (=96..224 px?, ~128px) in screen centre; bordered by a rectangle: left/right vertical lines, top line colour 5 (blue); a horizontal blue line across the ENTIRE width at y = SCANH+$20 = 40 (colour $5555 = blue) separates HUD from playfield; the scanner has small white (9) "bezel" tick marks at its top centre (the player-view bracket, $9090 / $0909 at columns SCANH+$4C01 and +$5301, i.e. ~x=152..166) marking the on-screen window. Player blip at (PLAXC>>4)/(>>3) scaled position in white; enemies drawn as dots with their own colour pair.
- Mini-terrain on scanner: table MTERR (BLK71.SRC) 3 bytes per 2 columns: byte0 = height, bytes 1-2 = pixel-pair pattern ($77,$00 / $07,$70 / $70,$07 = brown pixel placement), repeated; scanner terrain is drawn in colour 7 (brown).
- Play area: y 42..240; terrain sits at the bottom, humanoids stand on it.

## Terrain
- TDATA (BLK71.SRC) is a 1-bit-per-step delta table (bit=1 -> terrain y moves one way, 0 -> other; in code: `LDA LTBYTE; BPL up else DEC LOFF`, i.e. each bit = step of +-1 pixel in altitude per 1 scroll step); base offset $E0 (224). 32 bytes ... the table is ~0x100 bytes, wraps for the planet. Generator builds ALTTBL (altitude table, TLEN*4) and two 'flavour' pixel tables (TERTF0/TERTF1: even/odd pixel alignment) used by BGOUT for 1-pixel line draw; screen scrolled in 32-unit steps ($20) of 16-bit world X (~ 1/ (screen px *32)).
- Terrain is a single 1px line (no fill below), brown by default. World is 64 screens wide; wraps. Destroyed planet: "TERRAIN EXPLOSION" 16x6 sprite TERX0 (below) and terrain erased (BGERAS) on last human death.
- Full TDATA bytes available in /private/tmp copy of BLK71.SRC lines 509-526 (256 bytes); copy included below only by reference: re-extract from the repo.

## Object descriptors (DEFB6.SRC): FCB W_bytes,H_px ; FDB data0,data1,ON,OFF
Sizes (px WxH): Lander 10x8 (3 anim frames LND1/2/3, each with 2 pixel-phase images), Mutant("SCHITZO") 10x8, Baiter ("UFO") 12x4 (3 frames),
Bomber ("TIE") 8x8 (4 frames, rotating - D/E/F colour cycling), Pod ("PROBE") 8x8, Swarmer 6x4, Humanoid ("ASTRO") 4x8 (4 poses L1,L2,R1,R2),
Ship 16x6 (PLAPIC=PLD1x facing right frames, PLBPIC=PLD2x frames facing left), mini ship 10x4, Smart bomb icon 6x3, Bomber bomb 4x3 (2 shapes), Bomber-bomb explosion 8x8,
Baiter/lander bullets: Lander "bullet" is the 4x3 bomb shape, laser: 16px x 1 line segments moving ($FFFF x4 = 8 bytes, colour idx F white), score popups 12x6 (250 and 500: colours 1 / F,E,D), Terrain explosion 16x6.
Each sprite has 2 images (suffix 0 / 1) = same sprite shifted by one pixel for odd/even X alignment (not animation) EXCEPT where noted; animation = distinct sprite sets.

## Laser
- Right laser LASR (DEFA7.SRC 2792): starts at ship nose (+$704 offset = x+7 bytes, y+4), each frame extends 4-pixel (4 rows) segments of colour $11 (index 1, colour-cycled -> rainbow), with a head of $99 (white) 1 pixel; trailing end erased from FISTAB random-ish 'fizzle' tail (3 px steps) so beam appears as a growing then shrinking flickering line. Dies on x>= $9800 (screen edge) or collision. Colour 1 is cycled through COLTAB per frame so the beam flickers rainbow. Beam is 1 pixel thick (one row), length grows to about screen edge.

## Explosions
- Enemy/humanoid/ship explosion (PHR6 EXPLSV/APERSV vectors, Williams 'XSVCT'): object bitmap is split into pixels that fly outward from centre (expanding disintegration: RSIZE, CENTER, TOPLFT, ERASES table), pieces drawn in the object's own colours, then erased; "appear" (APVCT) is the reverse - pixels converge from a random scatter to form the sprite (used for enemy materialising, and DEFENDER logo letters).
- Player explosion (PLEX in BLK71.SRC): PNBITS=$80 (128) pieces, tables for X/Y position and X/Y velocity (TABLE 10*PNBITS), random seeds PSED/PSED2, colour pointer stepping PXCOL every 4 frames, pieces are single pixels, plus the screen-wide 'flash' (PCRAM+0 background set to colour - the whole screen flashes white/colour, see PDTH "STA PCRAM / CLR PCRAM BLACK SCREEN").
- Bomb/smart-bomb explosion BXD10: 8x8 filled yellow-ish (colour C, cycling) circle.
- Smart bomb: whole-screen flash (SBMBX0 COM PCRAM = background colour inverted briefly), all on-screen enemies killed.

## Thrust flame / starfield
- Thrust: THTAB (64 byte table, PHR6) holds random flame data; flame drawn behind the ship as a few jittering coloured pixels (yellow/red/...) (mem); ship sprite is flipped by switching PLAPIC / PLBPIC.
- Stars: STINIT (SAMEXAP7 / PHR6 area) initialises a field of single-pixel stars of random colour scrolling at parallax speed (mem: stars twinkle, drawn behind everything, and parallax with ship movement). Exact star count not found.

## Font (MESS0.SRC CHRTBL / NUMBR* / LETTR*)
- Variable width: most chars 3 byte-columns (6 px advance incl. 1px spacing -> 5x7 glyph, rows 8 high); I = 2 columns, M and W = 4 columns, punctuation = 1 column. Drawn in colour 1 in the glyph data and recoloured at write time (text colour set by routine).
- Chars: space ! , ? . ? 0-9 : ? then blank, A-Z (table order: ASCII 0x20.. -> 0x5A).
- Sample glyphs (# = lit pixel, 2px per byte):
NUMBR0
.#####
.#..##
.#..##
.#..##
.#..##
.#..##
.#####
......

NUMBR1
...###
..####
.##.##
....##
....##
....##
....##
......

NUMBR2
.#####
.#..##
....##
...##.
..#...
.#....
.#####
......

LETTRA
.#####
.#..##
.#..##
.#####
.#..##
.#..##
.#..##
......

LETTRM
.#######
.##.#.##
.##.#.##
.##.#.##
.##...##
.##...##
.##...##
........

LETTRS
.#####
.##...
.##...
.#####
....##
....##
.#####
......
- Raw hex for every glyph is in sprites_raw.txt (FONT_* lines).

## Attract mode sequence (AMODE1.SRC)
1. Williams page: "WILLIAMS" logo is drawn as a line-drawn stroke figure by a data-driven pen (LGOTAB: bytes = cursor moves, $AA+ = instructions), first slowly (3 bytes/frame) then fast (10); colour set via PCRAM+$C. Then text "ELECTRONICS PRESENTS" at $3258 (x=100,y=88).
2. "DEFENDER" logo: 'DEFENDER' letters materialise (APVCT appear effect, 15 pieces of 8x12 px blocks from DEFBLK, each 4x12 bytes), colours DCOLRS: shadow $22, letters $CC (cycling), background 0; then whole logo 0x3C x 0x18 bytes (120x24 px?) restores; then copyright "COPYRIGHT 1980" in tiny 5x7 font data CPRTAB at $3BD0 (the (c)(P) 'WILLIAMS ELECTRONICS INC' line, below logo).
3. Hall of Fame (today's greatest / all time): two tables, initials + score, headings underlined, blinking colour PCRAM+$D for new entry (HOFBL).
4. Instruction page ("SCANNER" label, 'LANDER' demo): demo plays - a lander (colour $4433 blip) descends to the humanoid, abducts him, the ship laser kills the lander (LASR$), catch humanoid; text lines TEXTAB introduce each enemy with its score; then enemies shown with score values.
(Order loops: Williams logo -> Defender title -> Hall of Fame -> Instruction/demo -> demo game play -> ... mem.)

## Sprites (ASCII renders; digits = palette index, '.' = transparent). Raw hex in sprites_raw.txt
SCZD10  [SCHITZO(mutant)]  10x8 px
...CC.....
..3CC.3...
.3.CC8.3..
.3.878.3..
..38783...
..3.7.3...
.3..7..3..
3...7...3.

SCZD11  [SCHITZO(mutant)]  10x8 px
....CC....
...3CC.3..
..3.CC8.3.
..3.878.3.
...38783..
...3.7.3..
..3..7..3.
3....7...3

ASXD10  [ASTRO EXPLODE]  8x8 px
...66...
..E66D..
.DC88CE.
6C8328C6
6C8228C6
.DC88CE.
..EC6D..
...66...

SWXD10  [SWARM EXPLODE]  8x8 px
...22...
..2222..
.244442.
22444422
24242422
.242422.
..2222..
........

PRBD10  [PROBE(pod)]  8x8 px
...F....
.E.8.E..
..8C8...
D8C8C8D.
..8C8...
.E.8.E..
...F....
........

PRBD11  [PROBE(pod)]  8x8 px
....F...
..E.8.E.
...8C8..
.D8C8C8D
...8C8..
..E.8.E.
....F...
........

ASTD10  [ASTRONAUT L1]  4x8 px
33..
43..
438.
878.
878.
.7..
.7..
.7..

ASTD11  [ASTRONAUT L1]  4x8 px
.33.
.43.
.438
.878
.878
..7.
..7.
..7.

ASTD20  [ASTRONAUT L2]  4x8 px
33..
43..
438.
878.
878.
77..
77..
77..

ASTD21  [ASTRONAUT L2]  4x8 px
.33.
.43.
.438
.878
.878
.77.
.77.
.77.

ASTD30  [ASTRONAUT R1]  4x8 px
.33.
.34.
834.
878.
878.
.7..
.7..
.7..

ASTD31  [ASTRONAUT R1]  4x8 px
..33
..34
.834
.878
.878
..7.
..7.
..7.

ASTD40  [ASTRONAUT R2]  4x8 px
.33.
.34.
834.
878.
878.
.77.
.77.
.77.

ASTD41  [ASTRONAUT R2]  4x8 px
..33
..34
.834
.878
.878
..77
..77
..77

TIED10  [TIE(bomber) 1]  8x8 px
.88888..
.88888..
DDDDD8..
DEEED8..
DEFED8..
DEEED...
DDDDD...
........

TIED11  [TIE(bomber) 1]  8x8 px
..88888.
..88888.
.DDDDD8.
.DEEED8.
.DEFED8.
.DEEED..
.DDDDD..
........

TIED20  [TIE(bomber) 2]  8x8 px
........
.88888..
DDDDD8..
DEEED8..
DEFED8..
DEEED8..
DDDDD...
........

TIED21  [TIE(bomber) 2]  8x8 px
........
..88888.
.DDDDD8.
.DEEED8.
.DEFED8.
.DEEED8.
.DDDDD..
........

TIED30  [TIE(bomber) 3]  8x8 px
........
........
DDDDD8..
DEEED8..
DEFED8..
DEEED8..
DDDDD8..
........

TIED31  [TIE(bomber) 3]  8x8 px
........
........
.DDDDD8.
.DEEED8.
.DEFED8.
.DEEED8.
.DDDDD8.
........

TIED40  [TIE(bomber) 4]  8x8 px
........
........
DDDDD...
DEEED8..
DEFED8..
DEEED8..
DDDDD8..
..8888..

TIED41  [TIE(bomber) 4]  8x8 px
........
........
.DDDDD..
.DEEED8.
.DEFED8.
.DEEED8.
.DDDDD8.
..88888.

BXD10  [BOMB EXPLOSION]  8x8 px
..CCCC..
.CCCCCC.
CCCCCCCC
CCCCCCCC
CCCCCCCC
CCCCCCCC
.CCCCCC.
..CCCC..

BMBD10  [BOMB(bomber bomb)]  4x3 px
A.A.
.A..
A.A.

BMBD11  [BOMB]  4x3 px
.A.A
..A.
.A.A

BMBD20  [BOMB2]  4x3 px
.A..
AAA.
.A..

BMBD21  [BOMB2]  4x3 px
..A.
.AAA
..A.

SWMD10  [SWARMER]  6x4 px
..2...
.222..
23232.
.222..

SWMD11  [SWARMER]  6x4 px
...2..
..222.
.23232
..222.

LND10  [LANDER 1]  10x8 px
...444....
..34443...
.33.33.3..
.33.33.3..
..34343...
..3.3.3...
.3..3..3..
3...3...3.

LND11  [LANDER 1]  10x8 px
....444...
...34443..
..33.33.3.
..33.33.3.
...34343..
...3.3.3..
..3..3..3.
.3...3...3

LND20  [LANDER 2]  10x8 px
...444....
..34443...
.3.33.33..
.3.33.33..
..34343...
..3.3.3...
.3..3..3..
3...3...3.

LND21  [LANDER 2]  10x8 px
....444...
...34443..
..3.33.33.
..3.33.33.
...34343..
...3.3.3..
..3..3..3.
.3...3...3

LND30  [LANDER 3]  10x8 px
..........
..33333...
.333.333..
.333.333..
..33333...
..3.3.3...
.3..3..3..
3...3...3.

LND31  [LANDER 3]  10x8 px
..........
...33333..
..333.333.
..333.333.
...3.333..
...3.3.3..
..3..3..3.
.3...3...3

UFOD10  [UFO(baiter) 1]  12x4 px
..3333333...
.37..7..73..
344.44.44.3.
.333333333..

UFOD11  [UFO(baiter) 1]  12x4 px
...3333333..
..37..7..73.
.344.44.44.3
..333333333.

UFOD20  [UFO(baiter) 2]  12x4 px
..3333333...
.3..7..7.3..
3.44.44.443.
.333333333..

UFOD21  [UFO(baiter) 2]  12x4 px
...3333333..
..3..7..7.3.
.3.44.44.443
..333333333.

UFOD30  [UFO(baiter) 3]  12x4 px
..3333333...
.3.7..7..3..
34.44.44.43.
.333333333..

UFOD31  [UFO(baiter) 3]  12x4 px
...3333333..
..3.7..7..3.
.34.44.44.43
..333333333.

PLD10  [PLAYER SHIP]  16x6 px
..66............
.6666...........
266666..........
.68866666DEF....
268888666666693.
..888693........

PLD11  [PLAYER SHIP]  16x6 px
...66...........
..6666..........
.266666.........
..28866666DEF...
.268888666666693
...888693.......

PLD20  [PLAYER SHIP]  16x6 px
...........66...
..........6666..
.........666663.
...FED66666883..
396666666888863.
.......396888...

PLD21  [PLAYER SHIP]  16x6 px
............66..
...........6666.
..........666663
....FED66666883.
.396666666888863
........396888..

PLAM0  [MINI PLAYER (lives icon / scanner)]  10x4 px
.66.......
2666......
686666ED..
2886666663

SBD10  [SMART BOMB icon]  6x3 px
9.999.
.999CC
9.999.

C25D10  [250 SCORE]  12x6 px
111.111.111.
..1.1...1.1.
111.111.1.1.
1.....1.1.1.
111.111.111.
............

C25D11  [250 SCORE]  12x6 px
.111.111.111
...1.1...1.1
.111.111.1.1
.1.....1.1.1
.111.111.111
............

C5D10  [500 SCORE]  12x6 px
FFF.EEE.DDD.
F...E.E.D.D.
FFF.E.E.D.D.
..F.E.E.D.D.
FFF.EEE.DDD.
............

C5D11  [500 SCORE]  12x6 px
.FFF.EEE.DDD
.F...E.E.D.D
.FFF.E.E.D.D
...F.E.E.D.D
.FFF.EEE.DDD
............

TERX0  [TERRAIN EXPLOSION]  16x6 px
1C.F7C.771.77..1
.D71.D7117777CCD
7F71711771C7D7FF
E7.7C7177C7177D7
7.DC77DEDE17777.
..77DEF7F.7.7.F.
