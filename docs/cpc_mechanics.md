# LET'S GO FOR VROUVES: CPC gameplay mechanics spec

This spec was taken from the Z80 source in `VrouvesCPC` (`src/game.asm`, `src/synergy.asm`,
`src/score.asm`, `src/lives.asm`, `src/tails.asm`, `src/hw.asm`, `src/main.asm`,
`src/title.asm`, `tools/gen_assets.py`, `tools/texts.py`). Each fact names the asm label or
symbol it comes from. If the manual and the code disagree, this spec follows the code, and
the difference is listed in section 13.

It does not cover stage maps, paths or waves; they are in `tools/gen_assets.py`
(`MAPn`, `GROUNDn`, `AIRn`, `SACKSn`, `WAVESn`). It does explain how that data is encoded
and used.

---

## 1. Time base

| Item | Value | Source |
|---|---|---|
| Video frame | 50 Hz (CPC PAL vsync; `framecnt` is incremented in `int_handler` on the interrupt after VSYNC) | `hw.asm int_handler` |
| Draw rate | one draw every 4 frames = **12.5 fps** | `FRAMES_PER_DRAW equ 4` (`hw.asm`) |
| **Logic tick** | **25 Hz = 40 ms**. `flip` sets `ticks_due = (frames elapsed + frame_acc) / 2`, so with 4 frames per draw there are 2 ticks per draw | `flip`, `game_run .t` |
| Overload cap | at most 2 ticks per draw (if ≥3 are due, 2 run and `frame_acc` is cleared). Under load the game slows down; ticks are not skipped | `flip .td` |
| Tick order | `wave_update` → `update_enemies` → `update_towers` → `update_projs` → `update_fx` → `banner_tick` | `game_tick` |
| Game over | the tick loop stops as soon as `game_over` ≠ 0 | `game_run .t` |
| Input | `handle_input` runs once per drawn frame (12.5 Hz), not once per tick | `game_run .loop` |

In this spec, **"tick" means 1/25 s.** "Frame" means a 50 Hz frame and "draw" means a 12.5 Hz
redraw.

---

## 2. Coordinates and grid

| Item | Value | Source |
|---|---|---|
| Map | **20 × 14 cells** | `NCOL equ 20`, `NROW equ 14` |
| Cell | **8 × 12 Mode-0 pixels** = **4 bytes × 12 scanlines** | `TH equ 12`; `col*4` (`draw_tile_bg`, `try_build`) |
| Playfield | 80 bytes (160 Mode-0 px) × 168 lines, drawn at screen lines 16..183 | `PF_Y equ 16`, `PF_H equ 168` |
| HUD | top bar at lines 0..15 (title + score/lives, or a message). Bottom bar at lines 184..199 (`HUD_Y1 184`, `HUD_Y2 192`) | `hud_top`, `hud_*` |

**Yes, the x unit is 2 Mode-0 pixels (one screen byte).** All game-logic x coordinates
(`E_X`, `T_CX`, the effect `F_X`, the cursor) are in bytes. Each cell is 4 x-units wide and
12 y-units (scanlines) tall. **The exception is the projectile x (`P_X`), which is in Mode-0
pixels (2 per byte)** (`P_X ; Mode 0 pixels`, `spawn_proj`: `T_CX*2`; `draw_projs`: `srl a`).

A Mode-0 pixel is about twice as wide as it is tall, so a cell is physically 16×12 in
square-pixel units. **The game logic treats a cell as square for ranges**: 1 x-byte counts as
3 range units and 1 scanline counts as 1, so one cell is 12 × 12 range units (section 6.1).

Reference points:
- Enemy sprite: 8×12 Mode-0 px (4 bytes × 12 lines), top-left at (`E_X`, `E_Y`). **The enemy
  centre is (`E_X+2`, `E_Y+6`)** (`in_range`, `spawn_proj`, `tank_crush`).
- Tower centre: `T_CX = col*4 + 2`, `T_CY = row*12 + 6` (`try_build`).
- Cell of a point: `col = x_bytes >> 2`, `row = y // 12` (`tank_crush`).

### Cell types (cellmap)
`gen_assets.py main()`: `celltype = 0 if t in '.F' else 1 if t == '#' else 3 if t in 'KP' else 2`

| cellmap value | Map chars | Meaning |
|---|---|---|
| 0 | `.` grass, `F` pitch grass | buildable by every defender |
| 1 | `#` road (carved from the `GROUNDn` waypoints) | never buildable |
| 2 | `T` tree, `C` cactus, `G` goat, `Y` cypress, `W` wall, `X` grave (and any other char) | **Psssst only** ("hovers") |
| 3 | `K` building, `P` yard (the base; sacks are on these cells) | never buildable |
| `#80 \| idx` | a tower, slot `idx` (0..31) | occupied |
| `#C0 \| idx` | a tower on a type-2 cell (only a Psssst can be there) | occupied; selling it puts back 2 |

`can_build`: the cell must be 0, or 2 when the selected type is `TT_PSSSST`. Any other value
(road, base, a tower) is refused. **Air paths do not mark cells.** A drone's flight line can
pass over buildable cells; only the ground path is carved as `#`.

---

## 3. Paths and enemy movement

### 3.1 Path encoding (`gen_assets.py main()`, `path_ground`/`path_air` in the stage file)
Each path comes from a waypoint list of (col,row). Each segment is horizontal, vertical or an
exact 45° diagonal (asserted). A segment is stored as `(dx, dy, n)`, where dx, dy ∈ {-1,0,+1}
and **n = 12 × (length in cells)** steps. The header is `x0, y0, sub0, rem0`:
- `x0 = col0*4`, `y0 = row0*12` (top-left of the first waypoint cell, in bytes/lines).
- If `y0 < 2`, steps are consumed until `y ≥ 2`, and `sub0`/`rem0` are adjusted. The comment
  says "start low enough for the health bar", but **no health bar is drawn** (`E_MAXHP` is set
  and never read).
- The list ends with `0,0,0`.

### 3.2 One "step" (`enemy_step`)
- `E_Y += dy` (1 scanline) on **every** step.
- `E_SUB += 1`. When it reaches 3: `E_X += dx` (1 byte) and `E_SUB = 0`. So x moves 1 byte
  every 3 steps.
- So **one cell = 12 steps** in both axes (12 lines vertically; 4 bytes = 12 steps
  horizontally). A diagonal cell also takes 12 steps (x and y change together), so diagonal
  movement covers more physical distance per step.
- `E_PROG` (16-bit) += 1 per step. It counts the steps walked since spawn and is the
  targeting key. It starts at 0 even when the start was trimmed.
- `E_REM -= 1`. At 0, move to the next segment (`E_SEG++`, `E_REM = n`). If the next
  segment's n is 0 (terminator), **the enemy has arrived**.
- Arrival happens at the top-left of the last waypoint cell (inside the base).

### 3.3 Speed (`enemy_move`)
`E_SPD` is in **1/16 step per tick** (`E_SPD equ 4 ; path steps per frame * 16`; "frame"
there means a logic tick):
```
c = E_SPD
if E_SLOW > 0: E_SLOW -= 1; c = c >> 1        ; floor-halved this tick
t = E_ACC + c ; E_ACC = t & 15 ; steps = t >> 4 ; do `steps` enemy_step calls
```
| Enemy | `E_SPD` | steps/tick | steps/s | cells/s | slowed `E_SPD` | slowed cells/s |
|---|---|---|---|---|---|---|
| Bio-drone (air) | 20 | 1.25 | 31.25 | 2.604 | n/a (never slowed) | n/a |
| Compliance guard | 9 | 0.5625 | 14.06 | 1.172 | 4 | 0.521 |
| Weed destroyer (tank) | 7 | 0.4375 | 10.94 | 0.911 | 3 | 0.391 |

The fractional remainder stays in `E_ACC` (starts at 0).

### 3.4 Air vs ground (`enemy_path`)
`ET_DRONE` (type 1) follows `path_air`. Guards and tanks follow `path_ground`. Both paths
start at the same waypoint and end at the base in every stage (data).

### 3.5 Reaching the base (`enemy_move .arrived`, `base_hit`, `update_sacks`)
- The enemy is removed and `en_count -= 1`.
- **Base damage** is etype byte 5: **drone 4, guard 8, tank 20**. It does **not** scale
  with the wave or the stage.
- `hp = max(0, hp - dmg)`. Start **hp = 100** (`game_init`). The HUD shows hp in red when
  hp < 30 (`hud_hp`).
- **Sacks (5 per stage, `NUM_SACKS`)** are only visual. Sack k (k = 0..4, in `SACKSn` order)
  is swapped to its empty tile once **hp ≤ 80 − 20k**, so the thresholds are 80, 60, 40, 20
  and 0. Several can go at once.
- The arrival gives no reward and no points.
- Losing: at the **start of the next tick**, `wave_update` sees hp = 0 and sets
  `game_over = 2`. The rest of the current tick still runs. The hp check comes before the
  wave-clear check, so losing wins over clearing.

### 3.6 Animation and facing (cosmetic, `enemy_sprite_idx`)
`E_ANIM` starts random (`rand`) and goes +1 every tick (even on ticks with 0 steps). The frame
is `(E_ANIM >> 2) & 1`, so it toggles every 4 ticks. The facing comes from the current
segment's dx: 0 → "down/vertical" sprite, <0 → left, >0 → right. Sprite index =
`((type−1)*3 + dir)*2 + frame`.

---

## 4. Enemies

`etype_tab` (game.asm): `base hp, hp per wave, speed, armour, reward, base damage, air, -`

| Type | id | base HP | HP/wave | speed (1/16 step/tick) | armour | reward (vrouves) | base damage (= kill points) | air |
|---|---|---|---|---|---|---|---|---|
| Bio-drone | 1 `ET_DRONE` | 6 | 3 | 20 | 0 | 3 | 4 | yes |
| Compliance guard | 2 `ET_GUARD` | 16 | 8 | 9 | 2 | 4 | 8 | no |
| Weed destroyer | 3 `ET_TANK` | 50 | 19 | 7 | 4 | 10 | 20 | no |

The "air" column is in the table but the code never reads it; it tests `type == ET_DRONE`.

### 4.1 HP (`spawn_enemy`)
```
HP = min(255, base + perwave * (wave_num + toughness))
```
- `wave_num` is **1-based**: `start_wave` increments it before any spawn.
- `toughness` is `stage_unlock+3`: stage 1: 0, stage 2: 0, **stage 3: 2**, **stage 4: 1**,
  stage 5: 0, stage 6: 0, stage 7: 0 (`Stage.toughness`, "invaders have the health of this
  many waves later").
- 8-bit add that saturates at 255 on each step (tank at wave 10, toughness 2: 278 → **255**).
- `E_MAXHP = E_HP` (not used).

Examples (toughness 0): drone 9 / 36 (wave 1 / 10). Guard 24 / 96. Tank 69 / 240.

### 4.2 Armour and damage (`damage_enemy`)
```
if ignore_armour: d = dmg
else:             d = dmg - armour; if d <= 0: d = 1     ; minimum 1
HP -= d ; if HP <= 0: kill
```
Armour is per enemy (`E_ARM`), copied from the table at spawn. Only the Psssst laser
lowers it (section 6.4). The Cauldron ignores armour.

### 4.3 Kill (`kill_enemy`)
- `funds += reward` (3/4/10) and `score += base damage` (4/8/20), through `pay`.
- The slot is freed and `en_count -= 1`. Effect: `FX_BOOM` for a tank, `FX_POOF` for the
  others.

### 4.4 Spawning (`start_wave`, `load_group`, `spawn_tick`, `spawn_enemy`)
- A wave is a list of groups `(type, count, interval)`, ended by 0 (`WAVESn`).
  **The interval is in ticks (1/25 s).**
- `start_wave`: loads group 1, then **sets `sp_timer = 10`**, so the first enemy appears 10
  ticks (0.4 s) after the wave starts.
- `spawn_tick` (each tick while a wave is active): `sp_timer -= 1`. At 0, try to spawn. If
  all **16** enemy slots (`MAX_EN`) are full, retry next tick (`sp_timer = 1`). Otherwise
  `sp_timer = interval` and `count -= 1`. When the group is used up, `load_group` loads the
  next one and sets `sp_timer` to the **new group's** interval. So the gap before a group's
  first enemy is that group's own interval.
- A new enemy starts at the path header position, with `E_ACC = E_PROG = E_SLOW = E_SEG = 0`
  and `E_GEN = ++gen_ctr` (8-bit, wraps).

---

## 5. Waves, countdown, economy

| Item | Value | Source |
|---|---|---|
| Waves per stage | **10** | `NUM_WAVES` (= `len(WAVES1)`) |
| Start funds | **120 every stage**, no carry-over (3000 in DEBUG builds) | `START_FUNDS`, `game_init` |
| Start hp | 100 | `game_init` |
| First countdown | `FIRST_COUNTDOWN equ 45` (seconds, see below) | `game_init` |
| Between waves | `NEXT_COUNTDOWN equ 15` | `wave_update .more` |

### 5.1 Countdown (`wave_update`, `wave_state = 0`)
`cd_sec = N`, `cd_sub = 25`. Each tick: if `cd_sub ≠ 0`: `cd_sub -= 1`. Otherwise, if
`cd_sec = 0`: start the wave. Otherwise `cd_sec -= 1; cd_sub = 25`, then `cd_sub -= 1` that
same tick.
So each displayed second lasts 25 ticks = 1 s. The HUD shows `NEXT nn` from N down to 00, and
the wave starts on the tick after 00 has been shown for 25 ticks. **Total wait = (N+1)×25
ticks: 46 s before wave 1 and 16 s between waves.** The countdown does not run while paused
(no ticks).

### 5.2 Early call (`call_wave_now`, key N)
Only while counting down (`wave_state = 0`), including before wave 1. It does nothing while a
wave is active, so waves never overlap.
- `funds += cd_sec >> 1` (floor of half the whole seconds shown).
- `score += cd_sec`.
- Then `start_wave` runs immediately.

### 5.3 Wave cleared (`wave_update .active`)
The wave is over when `sp_left == 0` and `en_count == 0` (every enemy killed or arrived),
checked at the start of the next tick.
- **Bonus: `funds += 15 + 3 × wave_num`** (the wave just finished, 1-based: 18, 21, … 45).
  No points.
- If `wave_num == 10`: **stage won**. `score += funds` (after the bonus), `game_over = 1`.
- Otherwise the countdown is 15 (section 5.1), with the message `B_CLEAR` / `B_NEXT`.

### 5.4 Messages and banners (timing)
- Stage start: the top bar shows `B_STAGE` + `B_CALL` (stays until replaced or cleared).
  On stages 1–5 a banner over rows 6–7 also shows the newly unlocked defender
  (`stage_unlock+1/+2` string ids) for `ban_timer = 125` ticks (5 s), or until the wave
  starts.
- Wave 10 start: `B_FINAL` for `msg_timer = 100` ticks (4 s). Other waves clear the top
  message.
- End: banner `B_WIN` or `B_LOSE` + `B_SPACE`. For 40 draws (`end_wait`, about 3.2 s) fire is
  ignored, then fire continues.

---

## 6. Defenders (towers)

`ttype_tab`: `cost, range, cooldown, damage, flags (bit0 hits air), projectile, sfx, sell`

| # | Defender | cost | range (units) | range (cells) | cooldown (ticks) | fire period | damage | hits air | projectile | sell |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Cretan | 35 | 30 | 2.50 | 18 | 19 ticks = 0.76 s | 6 | yes | bullet | 17 |
| 2 | Yiayia | 50 | 18 | 1.50 | 22 | 23 ticks = 0.92 s | 14 | **no** | melee (instant) | 25 |
| 3 | Bride | 70 | 28 | 2.33 | 6 | 7 ticks = 0.28 s | 4 (×3 crit) | yes | pistol | 35 |
| 4 | Psssst | 80 | 36 | 3.00 | 10 | 11 ticks = 0.44 s | 5 | yes | laser | 40 |
| 5 | Cauldron | 110 | 22 | 1.83 | 32 | 33 ticks = 1.32 s | 8 (ignores armour) | **no** | area (instant) | 55 |
| 6 | Baker | 60 | 34 | 2.83 | 36 | 37 ticks = 1.48 s | 16 (splash) | yes | dakos | 30 |

Limits: 32 towers (`MAX_TW`), 20 projectiles (`MAX_PR`), 8 effects (`MAX_FX`).

### 6.1 Range (`in_range`)
```
dx = |(E_X + 2) - T_CX| * 3        ; bytes → range units (1 byte = 3 units)
dy = |(E_Y + 6) - T_CY|            ; lines
in range  ⇔  dx <= R  and  dy <= R  and  dx² + dy² <= R²
```
This is a circle in "cell-square" space: **1 cell = 12 units on both axes**, so R/12 = radius
in cells, measured centre to centre. dx is quantised to whole bytes (3 units). The early
rejections do not change the result; they keep the `SQUARES` table index ≤ 63.

### 6.2 Cooldown, target search and budget (`tower_think`)
- New tower: `T_CD = 8` (`try_build`). Its first possible shot is 9 ticks after it is built.
- Each tick: if `T_DIS > 0` (Cauldron dented), only `T_DIS -= 1` (and redraw when it reaches
  0), so the cooldown is frozen. Else if `T_CD > 0`: `T_CD -= 1`. Else the tower is ready.
- **Search budget:** at most `TARGET_BUDGET = 4` ready towers search for a target per tick,
  in slot order (slots 0..31). A ready tower over the budget stays ready (`T_CD = 0`) and
  tries again next tick.
- Target found: fire, `T_CD = cooldown`. **The fire period is cooldown + 1 ticks.**
- No target: `T_CD = 4`, so it searches again 5 ticks later.

### 6.3 Targeting rule (`find_target`)
**First along its path:** of the enemies in range, take the one with the largest `E_PROG`
(steps walked since spawn). A strict `>` comparison means the lowest enemy slot wins a tie.
Towers without the air flag skip `ET_DRONE`.
Drones and walkers are compared by steps walked on their own paths, which differ in length.
This is not distance-to-base.

### 6.4 Fired shots: damage value
`tr_dmg = round(base_damage × T_SYN / 16)` when the tower has a synergy factor (section 7),
otherwise `base_damage` (`syn_dmg`). This value is used by every type except the Cauldron,
which has no synergy entry (it always uses 8).

**Cretan** (`tower_think` → `spawn_proj`, `PT_BULLET`): one bullet carrying `tr_dmg`, normal
armour.

**Bride** (`PT_PISTOL`): `rand() < 64` (8-bit LFSR `rand`, 64/256 = **1 in 4**) →
`damage = tr_dmg × 3` and the crit flag (crit sprite). The crit triples the
synergy-adjusted value: 4 → 12, or 6 → 18 with the Cretan bonus.

**Psssst** (`PT_LASER`): on impact, if the target is still valid, **`E_ARM -= 1` if > 0, and
then** the damage is applied, so that hit already uses the lowered armour. **The strip is
permanent** for that enemy (it has no duration), 1 point per laser hit, down to 0 (guard
armour 2 → 2 hits, tank 4 → 4 hits).

**Baker** (`PT_DAKOS`): on landing (section 6.5), splash `FX_BASH`, then **every** live enemy
(drones too) with
`|(E_X+2) − P_X/2| < 5` bytes **and** `|(E_Y+6) − P_Y| < 13` lines takes `P_DMG` with
normal armour. That is a ±4 bytes × ±12 lines box: **±1 cell on each axis around the landing
point**. The primary target is hit once, as part of the loop. **The splash happens even if
the target died in flight** (it lands at the last known position).

**Yiayia** (`fire_yiayia`, instant, no projectile): first **every non-drone** enemy inside the
Yiayia's range gets `E_SLOW = 40` ticks (1.6 s at half speed, set, not added). Then **only
the target** (furthest along, never a drone) takes `tr_dmg` (14, or 17 with the Baker bonus)
with normal armour. Effect `FX_BASH` on the target.

**Cauldron** (`fire_cauldron`, instant): needs a ground target in range to fire (via
`find_target`). Then **every non-drone** enemy in range gets `E_SLOW = 30` ticks (1.2 s, set,
so it **overwrites** a longer Yiayia slow) and takes **8 damage ignoring armour**. At most 2
cloud effects are drawn per throw (cosmetic).

### 6.5 Projectiles (`spawn_proj`, `proj_step`)
- Spawn: `P_X = T_CX × 2` (pixels), `P_Y = T_CY − 4`. Target = enemy slot + its `E_GEN`. The
  damage and crit flag are fixed at spawn. If all 20 slots are in use, the shot is lost (the
  cooldown and sound still happen).
- Each tick: if the target slot is still the same enemy (type ≠ 0 and same gen), the aim
  point is updated to its centre (`(E_X+2)*2` px, `E_Y+6`). Otherwise it is marked **lost**
  (bit 7) and keeps flying to the last aim point.
- Movement per tick, **per axis on its own** (not normalised): move toward the aim by
  `min(remaining, speed)` on each axis.
  `proj_speed` (x px, y lines): **bullet 6,9 · pistol 7,10 · laser 10,15 · dakos 3,5**.
- Impact when both axes are at the aim point after the move. Bullet, pistol and laser: an
  effect (`FX_SPARK`, or `FX_ZAP` for the laser). **A lost shot deals no damage.** Dakos:
  splash (above), even when lost.
- The enemy can move between the shot and the impact; damage is applied on the impact tick.

### 6.6 Tank dents Cauldrons (`tank_crush`, `crush_at`)
Every tick, while a tank is moving (`.anim` is reached), `E_ANIM += 1`. When
`E_ANIM & 7 == 0`, which is **every 8 ticks** (0.32 s), with a random phase:
- Tank cell = `((E_X+2) >> 2, (E_Y+6) // 12)`.
- The 4 orthogonal neighbours (left, right, up, down; not the tank's own cell and not the
  diagonals) are checked. A Cauldron there with `T_DIS == 0` gets **`T_DIS = 125` ticks
  (5 s) disabled** (dented sprite, `SFX_CRUSH`). A Cauldron that is already dented is not
  extended.
- Other tower types are never affected.

### 6.7 Which towers hit air
Cretan, Bride, Psssst and Baker (flag bit 0) can target drones. Yiayia and the Cauldron cannot
target drones, and their area slow/damage skips drones. The Baker splash hits everything.

### 6.8 Build and sell (`try_build`, `try_sell`, `sc_build`, `sc_sell`)
- Build: `can_build` passes, funds ≥ cost, and a free slot (the lowest free index) exists.
  Otherwise `SFX_ERROR`. Then `funds -= cost` and `score += base damage of the type`
  (6/14/4/5/8/16, the table value without synergy). `syn_update` runs.
- Sell (key S or DEL, on a tower cell): `funds += sell` (17/25/35/40/55/30, roughly half),
  `score -= base damage` (floored at 0). The cell goes back to 0 (or 2 for a Psssst on a
  blocked cell). `syn_update` runs. A tower can be sold at any time, even while dented.
- Only the defenders unlocked on the stage can be selected (keys 1–6, `stage_unlock` bit
  mask). The default selection is the Cretan (1), and the cursor starts at col 7, row 3.

Unlocks (`UNLOCKS`): stage 1: Cretan, Psssst · stage 2: + Yiayia · stage 3: + Bride ·
stage 4: + Baker · stage 5–7: + Cauldron (all 6).

---

## 7. Synergy (neighbour bonus), exactly as implemented

`syn_tab` (synergy.asm): each defender type has one partner type and one factor in 1/16:

| Defender | partner | factor | effect | label shown |
|---|---|---|---|---|
| Cretan | none | none | none | none |
| Yiayia | Baker | 19/16 | ×1.1875 | "+20%" |
| Bride | Cretan | 24/16 | ×1.5 | "+50%" |
| Psssst | Cretan | 13/16 | ×0.8125 | "−20%" |
| Cauldron | none | none | none | none |
| Baker | Cretan | 8/16 | ×0.5 | "−50%" |

- **Adjacency** (`syn_find`/`syn_loop`): at least one tower of the partner type in one of the
  4 orthogonal neighbour cells (same column with row ±1, or same row with col ±1). Several
  partners do **not** stack. The effect is one-way: only the listed defender is modified. For
  example, a Bride next to a Cretan gains, and the Cretan is unchanged.
- **Factor > 16 (17+) is a bonus; < 16 is a penalty.** `T_SYN = 0` means none.
- **Damage** (`syn_dmg`): `dmg = floor((base × factor + 8) / 16)`. Results: Yiayia 14→**17**,
  Bride 4→**6**, Psssst 5→**4**, Baker 16→**8**.
- **Recomputed only after a build or a sale** (`syn_update`), using `SYN_MAX = 3`:
  1. `syn_cnt = 0`.
  2. Pass 1, in slot order 0..31: towers that **currently hold a bonus** (`T_SYN ≥ 17`). For
     each: no partner → `T_SYN = 0`. Partner with a penalty → set it. Partner with a bonus →
     if `syn_cnt < 3`, `syn_cnt += 1` and set it, otherwise 0.
  3. Pass 2, in slot order: all other towers (`T_SYN < 17`, including towers zeroed in
     pass 1), with the same rule.
  So a tower that already holds a bonus keeps it while it still qualifies. Free bonus places
  go to the waiting towers in slot order (lowest slot index, which is not necessarily the
  oldest tower, since slots are reused). **Penalties always apply and do not use up
  places.**
- HUD preview (`syn_hud`, `syn_room`): with the cursor on an empty cell, the info line shows
  the factor the selected type **would** get there: red for a penalty (always shown), green
  for a bonus (only if `syn_cnt < 3`).

---

## 8. Score (`score.asm`, `pay`, `score_add`)

- 16-bit, saturating at 65535. The display shows 5 digits.
- +4 / +8 / +20 for each drone / guard / tank **killed** (not for one that arrives).
- +the defender's base damage for each one **built**. The same amount is taken off on
  **sale** (floored at 0).
- +`cd_sec` (whole seconds shown) when a wave is **called early**.
- +the **funds left** when a stage is won (after the last wave bonus).
- The wave-clear bonus and the early-call vrouves add to funds only, not to the score.
- High score table: 8 entries, 3-letter names (disk version only).

## 9. Lives, difficulty, restarts (`lives.asm`, `tails.asm`, `main.asm`)

- Difficulty (`difficulty`, key D on the title cycles 0→1→2→3→0): **0 Medium (default) 3
  lives, 1 Hard 2, 2 Hardest 0, 3 Easy 4** (`dif_lives: db 3,2,0,4`).
- Lives last for the whole game (set once in `tails_install`).
- **Stage lost** (`game_over = 2`): if lives > 0, then `lives -= 1`, **score = the score when
  the stage began** (`rt_chk`), and the same stage is replayed from scratch (`game_init`:
  funds 120, hp 100, sacks back, all towers removed, wave 0, countdown 45). If lives = 0, the
  game is over and play returns to the title (high score check).
- **Stage won** (`game_over = 1`): `rt_chk = score`, then the next stage. After stage 7
  comes the ending screen, then the title.
- **Quit** (ESC while paused): `game_over = 0`, back to the title, and the score counts for
  the high score table.

## 10. Pause and other controls (`handle_input`)

- **H** toggles pause. **ESC** pauses; **ESC while paused** quits. While paused, no logic
  ticks run (countdown, enemies, banner timers all frozen). Only L, M, H and ESC work.
- **L** switches language (any time, also in pause). **M** turns music on or off.
- Cursor: cursor keys, joystick or Q/A/O/P (`cursor_input`). Auto-repeat counts **drawn
  frames**: the first move is immediate, the second comes after `REP_FIRST = 4` draws
  (320 ms), then one move every `REP_NEXT = 1` draw (80 ms). The cursor stops at the map
  edges.
- Build: SPACE / RETURN / ENTER / COPY / joystick fire 1 or 2 (`fire_hit`). Sell: S or DEL.
  Next wave: N. Select: 1–6.
- Cursor colours: blinking ok-sprite (every 8 frames) if you can build there and afford it,
  or if the cell holds a tower. Red if you cannot.

## 11. Effects (cosmetic, `fx_tab`)
Lifetimes in ticks: spark 6, puff 12, bash 8, poof 10, boom 12, zap 6. The frame alternates on
bit 2 of the remaining time. Up to 8 at once; extra effects are dropped.

## 12. RNG
`rand`: a 16-bit xorshift-like generator on `seed`. The seed starts at `#A5F3` and is XORed
with `framecnt` when you leave the title. It is used for the Bride crit and the enemy
animation phase (and so for the tank crush phase).

## 13. Ambiguities and differences from the docs

1. **Yiayia target.** MANUAL.md says she bashes "the closest". The code bashes the enemy
   **furthest along the path** within range (`find_target`). Everyone in range is slowed.
2. **Synergy percentages** are labels. The real factors are 19/16 (+18.75%) and 13/16
   (−18.75%), and with rounding the actual damage is 14→17 (+21%) and 5→4 (−20%).
3. **The countdown is N+1 seconds** (shows 45..00, wave at 46 s; 15 → 16 s).
4. **Targeting across paths:** `E_PROG` counts steps on different path lengths (air vs ground),
   so "first" is not always "closest to the base".
5. **Range geometry:** a circle in cell space (1 byte = 3 units, 1 line = 1 unit, 12 units per
   cell), with x quantised to bytes. Physically an ellipse on the CPC display.
6. **Diagonal movement** (air paths) takes 12 steps per cell, like straight movement, so it is
   √2 faster in distance.
7. **Projectiles move per axis** (Chebyshev-like, not normalised) and can miss if the target
   dies (except the dakos).
8. **Cauldron slow (30) overwrites** a Yiayia slow (40) instead of keeping the longer one.
9. The **4-searches-per-tick budget** (`TARGET_BUDGET`) can delay shots when many towers are
   ready. It is a CPU-saving measure; decide whether the port keeps it for exact parity.
10. `E_GEN` is 8-bit and wraps. A recycled slot with a matching gen after 256 spawns could
    misattribute a hit (very unlikely).
11. **The tank crush timer** depends on `E_ANIM`, which starts random and advances every tick
    the tank exists, not per step.
12. The slow halving is a floor (9→4, 7→3), so it is a little more than half speed lost.
13. The etype "air" byte and `E_MAXHP` are not used. There is no enemy health bar.
14. Logic ticks never drop under load; the game slows instead (at most 2 ticks per draw).

---

## 14. Strings (verbatim, English / Greek)

Strings are printed in a 40-column 3x6 font. In multi-line strings, `\n` is a line break. The
story is wrapped to 40 columns by `texts.wrap()` (paragraphs split at `|`).

### 14.1 UI / title strings (`texts.STRINGS`)

**S_TITLE**

EN:
```
LET'S GO FOR VROUVES
```

GR:
```
ΠΑΜΕ ΓΙΑ ΒΡΟΥΒΕΣ
```

**S_LANGHINT**

EN:
```
PRESS 'L' FOR GREEK
```

GR:
```
ΠΑΤΗΣΤΕ 'L' ΓΙΑ ΑΓΓΛΙΚΑ
```

**S_WAVE**

EN:
```
WAVE
```

GR:
```
ΚΥΜΑ
```

**S_FUNDS**

EN:
```
FUNDS
```

GR:
```
ΒΡΟΥΒΕΣ
```

**S_HP**

EN:
```
HP
```

GR:
```
ΖΩΗ
```

**S_NEXT**

EN:
```
NEXT 
```

GR:
```
ΣΕ   
```

**S_GO**

EN:
```
  GO!  
```

GR:
```
ΠΑΜΕ!  
```

**S_PAUSE**

EN:
```
 PAUSE 
```

GR:
```
 ΠΑΥΣΗ 
```

**S_READY**

EN:
```
 READY 
```

GR:
```
 ΕΤΟΙΜΟ
```

**S_SELL**

EN:
```
[S] SELL +
```

GR:
```
[S] ΠΟΥΛΑ +
```

**S_NAME1**

EN:
```
CRETAN
```

GR:
```
ΚΡΗΤΙΚΟΣ
```

**S_NAME2**

EN:
```
YIAYIA
```

GR:
```
ΓΙΑΓΙΑ
```

**S_NAME3**

EN:
```
BRIDE
```

GR:
```
ΝΥΦΗ
```

**S_NAME4**

EN:
```
PSSSST
```

GR:
```
ΨΣΣΣΤ
```

**S_NAME5**

EN:
```
CAULDRON
```

GR:
```
ΚΑΖΑΝΙ
```

**S_NAME6**

EN:
```
BAKER
```

GR:
```
ΦΟΥΡΝΑΡΗΣ
```

**S_INFO1**

EN:
```
[1] CRETAN 35: HUNTING RIFLE, AIR+GND
```

GR:
```
[1] ΚΡΗΤΙΚΟΣ 35: ΤΟΥΦΕΚΙ, ΑΕΡΑΣ+ΓΗ
```

**S_INFO2**

EN:
```
[2] YIAYIA 50: STAFF+POT, SLOWS
```

GR:
```
[2] ΓΙΑΓΙΑ 50: ΜΑΓΚΟΥΡΑ, ΦΡΕΝΑΡΕΙ
```

**S_INFO3**

EN:
```
[3] BRIDE 70: PISTOL, CRITICALS
```

GR:
```
[3] ΝΥΦΗ 70: ΠΙΣΤΟΛΙ, ΚΡΙΤΙΚΑ
```

**S_INFO4**

EN:
```
[4] PSSSST 80: LASER, MELTS ARMOUR
```

GR:
```
[4] ΨΣΣΣΤ 80: ΛΕΙΖΕΡ ΚΑΤΑ ΘΩΡΑΚΩΝ
```

**S_INFO5**

EN:
```
[5] CAULDRON 110: TOXIC CLOUD, AREA
```

GR:
```
[5] ΚΑΖΑΝΙ 110: ΤΟΞΙΚΟ ΣΥΝΝΕΦΟ, ΠΕΡΙΟΧΗ
```

**S_INFO6**

EN:
```
[6] BAKER 60: HURLS DAKOS, SPLASH
```

GR:
```
[6] ΦΟΥΡΝΑΡΗΣ 60: ΠΕΤΑΕΙ ΝΤΑΚΟΥΣ!
```

**B_CALL**

EN:
```
BUILD, THEN PRESS N FOR THE WAVE
```

GR:
```
ΧΤΙΣΕ ΚΑΙ ΠΑΤΑ N ΓΙΑ ΤΟ ΚΥΜΑ
```

**B_CLEAR**

EN:
```
WAVE CLEARED!  BONUS VROUVES!
```

GR:
```
ΤΟ ΚΥΜΑ ΑΠΟΚΡΟΥΣΤΗΚΕ! ΜΠΟΝΟΥΣ!
```

**B_NEXT**

EN:
```
N: NEXT WAVE NOW
```

GR:
```
N: ΕΠΟΜΕΝΟ ΚΥΜΑ ΤΩΡΑ
```

**B_FINAL**

EN:
```
FINAL WAVE! HERE COME THE TANKS!
```

GR:
```
ΤΕΛΙΚΟ ΚΥΜΑ! ΕΡΧΟΝΤΑΙ ΤΑ ΤΑΝΚΣ!
```

**B_NEWDEF**

EN:
```
A NEW DEFENDER JOINS THE VILLAGE!
```

GR:
```
ΝΕΟΣ ΑΜΥΝΤΙΚΟΣ ΣΤΟ ΧΩΡΙΟ!
```

**B_SPACE**

EN:
```
PRESS SPACE / FIRE
```

GR:
```
ΠΑΤΗΣΤΕ SPACE / FIRE
```

**B_PAUSE**

EN:
```
PAUSED
```

GR:
```
ΠΑΥΣΗ
```

**B_PAUSE2**

EN:
```
H: CONTINUE    ESC: QUIT
```

GR:
```
H: ΣΥΝΕΧΕΙΑ    ESC: ΕΞΟΔΟΣ
```

**T_START**

EN:
```
SPACE / FIRE: START
```

GR:
```
SPACE / FIRE: ΕΝΑΡΞΗ
```

**T_CREDIT**

EN:
```
REVIVE8BIT - 2026 - VASPER
```

GR:
```
REVIVE8BIT - 2026 - VASPER
```

**T_DEFHDR**

EN:
```
THE DEFENDERS
```

GR:
```
ΟΙ ΥΠΕΡΑΣΠΙΣΤΕΣ
```

**T_ENEHDR**

EN:
```
THE INVADERS OF F&M CO.
```

GR:
```
ΟΙ ΕΙΣΒΟΛΕΙΣ ΤΗΣ F&M CO.
```

**T_CAST1**

EN:
```
CRETAN - 35
IN MIDNIGHT BLACK. HUNTING RIFLE.
```

GR:
```
ΚΡΗΤΙΚΟΣ - 35
ΜΑΥΡΟΦΟΡΟΣ ΜΕ ΚΥΝΗΓΕΤΙΚΟ ΤΟΥΦΕΚΙ.
```

**T_CAST2**

EN:
```
YIAYIA - 50
STAFF OF CHASTISEMENT. SLOWS ALL.
```

GR:
```
ΓΙΑΓΙΑ - 50
ΜΑΓΚΟΥΡΑ ΚΑΙ ΠΙΚΡΑ ΧΟΡΤΑ. ΦΡΕΝΑΡΕΙ.
```

**T_CAST3**

EN:
```
BRIDE - 70
WEDDING WHITE, RAPID PISTOL.
```

GR:
```
ΝΥΦΗ - 70
ΝΥΦΙΚΟ ΚΑΙ ΓΡΗΓΟΡΟ ΠΙΣΤΟΛΙ.
```

**T_CAST4**

EN:
```
PSSSST - 80
DEFECTED DRONE. LASER MELTS ARMOUR.
```

GR:
```
ΨΣΣΣΤ - 80
ΑΥΤΟΜΟΛΟ ΝΤΡΟΝ. ΛΕΙΖΕΡ ΚΑΙ ΣΠΡΕΙ.
```

**T_CAST5**

EN:
```
CAULDRON - 110
UNLICENSED LIPIDS & ASCORBIC ACIDS.
```

GR:
```
ΚΑΖΑΝΙ - 110
ΑΔΕΙΟΔΟΤΗΤΑ ΛΙΠΙΔΙΑ & ΑΣΚΟΡΒΙΚΑ.
```

**T_CAST6**

EN:
```
BAKER - 60
HURLS DAKOS (BARLEY RUSKS). SPLASH.
```

GR:
```
ΦΟΥΡΝΑΡΗΣ - 60
ΠΕΤΑΕΙ ΚΡΙΘΑΡΟΚΟΥΛΟΥΡΑ. ΠΙΤΣΙΛΙΑ.
```

**T_ENE1**

EN:
```
BIO-DRONE
FAST, FRAGILE. FLIES OVER WALLS.
```

GR:
```
ΒΙΟ-ΝΤΡΟΝ
ΓΡΗΓΟΡΟ, ΕΥΘΡΑΥΣΤΟ. ΠΕΤΑΕΙ ΠΑΝΩ.
```

**T_ENE2**

EN:
```
COMPLIANCE GUARD
ARMOURED. WEED-WHACKER, HERBICIDE.
```

GR:
```
ΦΥΛΑΚΑΣ ΣΥΜΜΟΡΦΩΣΗΣ
ΘΩΡΑΚΙΣΜΕΝΟΣ, ΜΕ ΖΙΖΑΝΙΟΚΤΟΝΟ.
```

**T_ENE3**

EN:
```
WEED DESTROYER
TREADED TANK. CRUSHES CAULDRONS.
```

GR:
```
ΚΑΤΑΣΤΡΟΦΕΑΣ ΧΟΡΤΩΝ
ΕΡΠΥΣΤΡΙΟΦΟΡΟ. ΛΙΩΝΕΙ ΚΑΖΑΝΙΑ.
```

**T_CTRL**

EN:
```
MOVE

BUILD

NEXT WAVE

MUSIC
```

GR:
```
ΚΙΝΗΣΗ

ΧΤΙΣΙΜΟ

ΝΕΟ ΚΥΜΑ

ΜΟΥΣΙΚΗ
```

**T_CTRL2**

EN:
```
CHOOSE

SELL

PAUSE

GREEK
```

GR:
```
ΕΠΙΛΟΓΗ

ΠΟΥΛΗΜΑ

ΠΑΥΣΗ

ΑΓΓΛΙΚΑ
```

### 14.2 Score bar (`texts.SCORE_TEXT`, top bar: text, 5-digit score, text, lives digit)

- EN: `'SCORE '` + score + `' LIVES '` + lives
- GR: `'ΣΚΟΡ '` + score + `' ΖΩΕΣ '` + lives

### 14.3 Title raw texts: high scores and difficulty (`texts.TITLE_RAW`)

| id | English | Greek |
|---|---|---|
| tr_hshdr | HIGH SCORES | ΚΑΛΥΤΕΡΑ ΣΚΟΡ |
| tr_newhs | NEW HIGH SCORE! | ΝΕΟ ΡΕΚΟΡ! |
| tr_name | ENTER YOUR NAME | ΓΡΑΨΕ ΤΟ ΟΝΟΜΑ ΣΟΥ |
| tr_keys | UP/DOWN: LETTER    FIRE: NEXT | ΠΑΝΩ/ΚΑΤΩ: ΓΡΑΜΜΑ   FIRE: ΕΠΟΜΕΝΟ |
| tr_dif0 | 'D' DIFFICULTY: MEDIUM - 3 LIVES | 'D' ΔΥΣΚΟΛΙΑ: ΜΕΤΡΙΑ - 3 ΖΩΕΣ |
| tr_dif1 | 'D' DIFFICULTY: HARD - 2 LIVES | 'D' ΔΥΣΚΟΛΙΑ: ΔΥΣΚΟΛΗ - 2 ΖΩΕΣ |
| tr_dif2 | 'D' DIFFICULTY: HARDEST - NO LIVES | 'D' ΔΥΣΚΟΛΙΑ: ΠΟΛΥ ΔΥΣΚΟΛΗ - 0 ΖΩΕΣ |
| tr_dif3 | 'D' DIFFICULTY: EASY - 4 LIVES | 'D' ΔΥΣΚΟΛΙΑ: ΕΥΚΟΛΗ - 4 ΖΩΕΣ |

Name entry characters (`NAME_CHARS`, UP/DOWN order): `ABCDEFGHIJKLMNOPQRSTUVWXYZΓΔΘΛΞΠΣΦΨΩ0123456789 `

Default high score table (`HISCORES`): VAS 6000, ZON 5000, KRI 4000, YIA 3000, NYF 2500, FOU 2000, PAP 1500, KAT 1000

### 14.4 Story (`texts.STORY_EN` / `STORY_GR`, as wrapped by `texts.wrap`, shown as `T_STORY`)

EN:
```
ARMED WITH EU DIRECTIVE 8647/2026, THE
CORPORATE GOLIATHS AT FRANKENSTEIN &
MOREAU CO. ARE DEPLOYING BIO-DRONES,
HAZARD SQUADS AND HEAVY MACHINERY TO
DESTROY 'VROUVES' - THE WILD,
'COPYRIGHTED' MOUNTAIN GREENS OF CRETE.

IN THE VILLAGE OF ZONIANA, DEPLOY THE
DEFENDERS TO PROTECT THE KAFENIO AND ITS
PRECIOUS SACKS OF BITTER GREENS!

LUCKILY THE REBEL CORPORATE DRONE PSSSST
HAS DEFECTED, AND FIGHTS ALONGSIDE THE
HEAVILY FORTIFIED VILLAGERS.
```

GR:
```
ΟΠΛΙΣΜΕΝΟΙ ΜΕ ΤΗΝ ΟΔΗΓΙΑ ΕΕ 8647/2026,
ΟΙ ΚΟΛΟΣΣΟΙ ΤΗΣ FRANKENSTEIN & MOREAU
CO. ΣΤΕΛΝΟΥΝ ΒΙΟ-ΝΤΡΟΝ, ΣΥΝΕΡΓΕΙΑ ΚΑΙ
ΒΑΡΙΑ ΜΗΧΑΝΗΜΑΤΑ ΓΙΑ ΝΑ ΞΕΡΙΖΩΣΟΥΝ ΤΙΣ
'ΒΡΟΥΒΕΣ' - ΤΑ ΑΓΡΙΑ, 'ΚΑΤΟΧΥΡΩΜΕΝΑ'
ΧΟΡΤΑ ΤΩΝ ΒΟΥΝΩΝ ΤΗΣ ΚΡΗΤΗΣ.

ΣΤΑ ΖΩΝΙΑΝΑ, ΣΤΗΣΕ ΤΟΥΣ ΥΠΕΡΑΣΠΙΣΤΕΣ ΓΙΑ
ΝΑ ΠΡΟΣΤΑΤΕΨΕΙΣ ΤΟ ΚΑΦΕΝΕΙΟ ΚΑΙ ΤΑ
ΠΟΛΥΤΙΜΑ ΣΑΚΙΑ ΜΕ ΤΑ ΠΙΚΡΑ ΧΟΡΤΑ!

ΕΥΤΥΧΩΣ ΤΟ ΕΠΑΝΑΣΤΑΤΗΜΕΝΟ ΝΤΡΟΝ ΨΣΣΣΤ
ΑΥΤΟΜΟΛΗΣΕ ΚΑΙ ΠΟΛΕΜΑ ΔΙΠΛΑ ΣΤΟΥΣ
ΟΧΥΡΩΜΕΝΟΥΣ ΧΩΡΙΑΝΟΥΣ.
```

Raw (unwrapped, `|` = paragraph break):

EN:
```
ARMED WITH EU DIRECTIVE 8647/2026, THE CORPORATE GOLIATHS AT FRANKENSTEIN & MOREAU CO. ARE DEPLOYING BIO-DRONES, HAZARD SQUADS AND HEAVY MACHINERY TO DESTROY 'VROUVES' - THE WILD, 'COPYRIGHTED' MOUNTAIN GREENS OF CRETE.|IN THE VILLAGE OF ZONIANA, DEPLOY THE DEFENDERS TO PROTECT THE KAFENIO AND ITS PRECIOUS SACKS OF BITTER GREENS!|LUCKILY THE REBEL CORPORATE DRONE PSSSST HAS DEFECTED, AND FIGHTS ALONGSIDE THE HEAVILY FORTIFIED VILLAGERS.
```

GR:
```
ΟΠΛΙΣΜΕΝΟΙ ΜΕ ΤΗΝ ΟΔΗΓΙΑ ΕΕ 8647/2026, ΟΙ ΚΟΛΟΣΣΟΙ ΤΗΣ FRANKENSTEIN & MOREAU CO. ΣΤΕΛΝΟΥΝ ΒΙΟ-ΝΤΡΟΝ, ΣΥΝΕΡΓΕΙΑ ΚΑΙ ΒΑΡΙΑ ΜΗΧΑΝΗΜΑΤΑ ΓΙΑ ΝΑ ΞΕΡΙΖΩΣΟΥΝ ΤΙΣ 'ΒΡΟΥΒΕΣ' - ΤΑ ΑΓΡΙΑ, 'ΚΑΤΟΧΥΡΩΜΕΝΑ' ΧΟΡΤΑ ΤΩΝ ΒΟΥΝΩΝ ΤΗΣ ΚΡΗΤΗΣ.|ΣΤΑ ΖΩΝΙΑΝΑ, ΣΤΗΣΕ ΤΟΥΣ ΥΠΕΡΑΣΠΙΣΤΕΣ ΓΙΑ ΝΑ ΠΡΟΣΤΑΤΕΨΕΙΣ ΤΟ ΚΑΦΕΝΕΙΟ ΚΑΙ ΤΑ ΠΟΛΥΤΙΜΑ ΣΑΚΙΑ ΜΕ ΤΑ ΠΙΚΡΑ ΧΟΡΤΑ!|ΕΥΤΥΧΩΣ ΤΟ ΕΠΑΝΑΣΤΑΤΗΜΕΝΟ ΝΤΡΟΝ ΨΣΣΣΤ ΑΥΤΟΜΟΛΗΣΕ ΚΑΙ ΠΟΛΕΜΑ ΔΙΠΛΑ ΣΤΟΥΣ ΟΧΥΡΩΜΕΝΟΥΣ ΧΩΡΙΑΝΟΥΣ.
```

### 14.5 Stage strings (`gen_assets.STAGES[k].strings`)

| Stage | id | English | Greek |
|---|---|---|---|
| 1 | B_STAGE | STAGE 01: THE KAFENIO | ΠΙΣΤΑ 01: ΤΟ ΚΑΦΕΝΕΙΟ |
| 1 | B_WIN | KAFENIO SAVED! NOW, TO THE CHURCH! | ΤΟ ΚΑΦΕΝΕΙΟ ΣΩΘΗΚΕ! ΣΤΗΝ ΕΚΚΛΗΣΙΑ! |
| 1 | B_LOSE | THE KAFENIO HAS FALLEN! | ΤΟ ΚΑΦΕΝΕΙΟ ΕΠΕΣΕ! |
| 2 | B_STAGE | STAGE 02: THE VILLAGE CHURCH | ΠΙΣΤΑ 02: Η ΕΚΚΛΗΣΙΑ ΤΟΥ ΧΩΡΙΟΥ |
| 2 | B_WIN | CHURCH SAVED! NOW, TO THE TOWN HALL! | Η ΕΚΚΛΗΣΙΑ ΣΩΘΗΚΕ! ΣΤΟ ΔΗΜΑΡΧΕΙΟ! |
| 2 | B_LOSE | THE CHURCH HAS FALLEN! | Η ΕΚΚΛΗΣΙΑ ΕΠΕΣΕ! |
| 3 | B_STAGE | STAGE 03: THE TOWN HALL | ΠΙΣΤΑ 03: ΤΟ ΔΗΜΑΡΧΕΙΟ |
| 3 | B_WIN | TOWN HALL SAVED! NOW, TO THE BAKERY! | ΤΟ ΔΗΜΑΡΧΕΙΟ ΣΩΘΗΚΕ! ΣΤΟ ΦΟΥΡΝΟ! |
| 3 | B_LOSE | THE TOWN HALL HAS FALLEN! | ΤΟ ΔΗΜΑΡΧΕΙΟ ΕΠΕΣΕ! |
| 4 | B_STAGE | STAGE 04: THE BAKERY | ΠΙΣΤΑ 04: Ο ΦΟΥΡΝΟΣ |
| 4 | B_WIN | BAKERY SAVED! NOW, TO THE SCHOOL! | Ο ΦΟΥΡΝΟΣ ΣΩΘΗΚΕ! ΣΤΟ ΣΧΟΛΕΙΟ! |
| 4 | B_LOSE | THE BAKERY HAS FALLEN! | Ο ΦΟΥΡΝΟΣ ΕΠΕΣΕ! |
| 5 | B_STAGE | STAGE 05: THE SCHOOL | ΠΙΣΤΑ 05: ΤΟ ΣΧΟΛΕΙΟ |
| 5 | B_WIN | SCHOOL SAVED! NOW, TO THE PITCH! | ΤΟ ΣΧΟΛΕΙΟ ΣΩΘΗΚΕ! ΣΤΟ ΓΗΠΕΔΟ! |
| 5 | B_LOSE | THE SCHOOL HAS FALLEN! | ΤΟ ΣΧΟΛΕΙΟ ΕΠΕΣΕ! |
| 6 | B_STAGE | STAGE 06: THE VILLAGE PITCH | ΠΙΣΤΑ 06: ΤΟ ΓΗΠΕΔΟ ΤΟΥ ΧΩΡΙΟΥ |
| 6 | B_WIN | PITCH SAVED! NOW, TO THE CEMETERY! | ΤΟ ΓΗΠΕΔΟ ΣΩΘΗΚΕ! ΣΤΟ ΝΕΚΡΟΤΑΦΕΙΟ! |
| 6 | B_LOSE | THE PITCH HAS FALLEN! | ΤΟ ΓΗΠΕΔΟ ΕΠΕΣΕ! |
| 7 | B_STAGE | STAGE 07: THE CEMETERY CHURCH | ΠΙΣΤΑ 07: Η ΕΚΚΛΗΣΙΑ ΤΟΥ ΝΕΚΡΟΤΑΦΕΙΟΥ |
| 7 | B_WIN | VICTORY! THE VROUVES ARE SAFE! | ΝΙΚΗ! ΟΙ ΒΡΟΥΒΕΣ ΣΩΘΗΚΑΝ! |
| 7 | B_LOSE | THE CEMETERY CHURCH HAS FALLEN! | Η ΕΚΚΛΗΣΙΑ ΤΟΥ ΝΕΚΡΟΤΑΦΕΙΟΥ ΕΠΕΣΕ! |

### 14.6 Stage start announcements (`gen_assets.UNLOCKS`: defenders available, banner line 1, line 2)

| Stage | defenders (type ids) | line 1 | line 2 |
|---|---|---|---|
| 1 | [1, 4] | S_INFO1 | S_INFO4 |
| 2 | [1, 2, 4] | B_NEWDEF | S_INFO2 |
| 3 | [1, 2, 3, 4] | B_NEWDEF | S_INFO3 |
| 4 | [1, 2, 3, 4, 6] | B_NEWDEF | S_INFO6 |
| 5 | [1, 2, 3, 4, 5, 6] | B_NEWDEF | S_INFO5 |
| 6 | [1, 2, 3, 4, 5, 6] | none | none |
| 7 | [1, 2, 3, 4, 5, 6] | none | none |

### 14.7 Title key-art labels (drawn into the title art, `gen_assets.title_art`)

Keycaps: arrow keys, `SPACE`, `N`, `M`, `1`, `6`, `S`, `H`, `L` (paired with `T_CTRL` / `T_CTRL2` labels).
