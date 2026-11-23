# C3AP design notes

## Scope (v0.1)

- NTSC-U (SCUS-94244), BizHawk (Nymashock), Archipelago 0.6.8+.
- The 25 main levels in warp rooms 1-5 and the five bosses. Secret levels (Ski Crazed, Area 51?, Rings of Power,
  Hot Coco, Eggipus Rex), time trial relics and the Yellow Gem's location (Hang 'em High's secret-warp-room route)
  are out of scope.
- No game patching: the client only reads and writes RAM, the same approach as C1AP.

## Items and locations

| Items | Count |
|---|---|
| Crystal | 25 |
| Super Body Slam, Double Jump, Death Tornado Spin, Fruit Bazooka | 4 |
| Red, Green, Purple, Blue, Yellow Gem (with `gem_checks`) | 5 |
| Extra Life, Aku Aku Mask, No Lives Trap (`trap_chance`) | the rest |

| Locations | Count |
|---|---|
| `<level> - Crystal` | 25 |
| `<boss> - Defeated` (Tiny Tiger, Dingodile, N. Tropy, N. Gin) | 4 |
| `<level> - Clear Gem` (with `gem_checks`) | 25 |
| `<level> - Gem Path Clear Gem` (Bone Yard, Tomb Time, Dino Might!, Sphynxinator, Gone Tomorrow, Bug Lite) | 6 |
| `<level> - <color> Gem` (Deep Trouble, High Time, Tomb Wader, Flaming Passion) | 4 |

Dr. N. Cortex is an event location holding the locked Victory item. Crash Dash, his reward, stays vanilla.

## Logic

- Warp room r (and its levels) needs `5 * (r - 1)` crystals: in the game you reach room r by beating boss r - 1,
  whose button needs that room's five crystals.
- Boss r needs `5 * r` crystals.
- The powers a level needs are not mapped per level. Instead, room r also needs every item power from the bosses of
  rooms 1 .. r - 1 (`powers_before_room`), which is the vanilla state when you arrive there. Shuffle keeps levels in
  their own room, so this stays honest.
- Gem path clear gems also need their colored gems (Bug Lite's needs all five).
- Without `gem_checks` there are exactly as many locations as crystals + powers, so there is no room to fill
  powers in logic: they become `useful` and are left out of logic.

## Client: who owns which bit

Same scheme as C1AP, which has been verified live there.

- **Crystals.** The `CRYSTALS` bits mirror the number of Crystal items received, filled in level order (warp room
  1's five first), so N crystals open the first N // 5 boss buttons.
- **Colored gems.** Once their bits are known, they mirror the colored gem items.
- **Masks.** While Crash is in a level whose crystal (or colored gem) location is unchecked, its bit is held at 0, so
  the game spawns the crystal and can award it. The bit going 0 -> 1 is the check, and the bit then goes back to
  mirroring the item. 
- **Bosses.** The game's "level completed" field (0x80068F64, bit = level ID, set after a normal finish) is never
  written: a boss's bit set is its defeat check, Cortex's is the goal. In v1.0 the same field gives the "exit the
  level" checks. That field, not the powers, opens the next room's fence (BizHawk).
- **Powers** are rebuilt by the game from the bosses beaten on every level load; the client rewrites them every poll,
  so only received powers stay.
- **Clear gems** are never written: a level's clear gem bit appearing while in it is the check.
- **Filler and traps** are applied in the warp room and carry into the next level (VERIFY: in Crash 1 lives only
  sync at level end).
- **Death Link** sends when the respawn counter goes up inside the same level.
- **Level shuffle** watches `SCENE_REQUEST` (0x80060AC0, -1 when idle). A button's request is swapped for the
  shuffled level if caught; if missed, the vanilla level loads and the client requests the shuffled one right away.
  ✅ BizHawk round 4: swaps within a room and across rooms load with no hang, and leaving the level returns
  to the button's room. Still off by default, as an option.

## Target design (v1.0, C2AP style)

Agreed with the project owner on 2026-11-22. **Built on 2026-11-22** (VERIFY round 7 is its playtest). The v0.1
sections above are history; where they differ, this section wins. What v1.0 does beyond the plan below:

- Items: one per level and kind (crystal, clear gem, gem path gem, race gem, relic), item IDs from the level ID.
  Crash Dash is an item. The goal is read from Cortex's "level completed" bit, so the powers can all be items.
- `level_shuffle` is `vanilla` / `within_rooms` / `all_rooms` (old `true` = within rooms).
- Relic items set their level's sapphire bit. While a level is active, its sapphire and gold bits are held at 0 until
  every relic tier enabled for it is checked.
- Unknown gem bits (five gem path gems, both race gems) are learned: in a level with exactly one open unknown gem, a
  gem bit no known gem owns appearing is that gem; the client logs the bit.
- The "level completed" field is read as 8 bytes (level IDs reach 0x27). VERIFY for IDs of 32 and up.
- Hot Coco and Eggipus Rex (secret exits, owner + BizHawk): entry, exit, clear gem and relics are checks, 30 relics in
  all. Hot Coco (0x27) is behind Road Crash's alien sign (GAMESTATE 0x400 then scene 0x27; a finish returns to Road
  Crash's button) and needs nothing; its gem is the box gem. Eggipus Rex (0x26) is behind Dino Might!'s Yellow Gem path
  (Yellow Gem only, no Super Body Slam); its gem is for finishing (no boxes). Its locations exist only with gem checks,
  since the Yellow Gem is only an item then. Their region is the host's button's warp room. Gem bits 38/39 are confirmed
  (BizHawk), Eggipus Rex's exit and relic bits too. Their time trial is open from the first visit, with or without
  the gem (BizHawk: Eggipus Rex), so their relics need only the level.
- The client only writes the gem and relic bits of locations the seed has, so a gem or relic that isn't a check stays
  vanilla (secret levels' gems without relic checks, Eggipus Rex without gem checks).
- Gem powers (owner's rule, 2026-11-22, data.Level.gem_powers): no powers for gems in warp rooms 1-2 and in the
  ride levels; in warp room 3 only High Time (Double Jump) and Dino Might! (Super Body Slam, its bonus round); Death
  Tornado Spin for the other warp room 4 levels, Fruit Bazooka for Gone Tomorrow and Flaming Passion (Bug Lite needs
  none, owner). Path extras: Bone
  Yard's red path needs Double Jump, Sphynxinator's blue path Double Jump (a gap crossed with Double Jump + Death
  Tornado Spin, GameFAQs).
- Gem layout (GameFAQs guides by josher1212, NickWhiz1, Nemesis): Tomb Time has one gem, which needs Purple (20 of
  its boxes are on the path). Dino Might! and Gone Tomorrow need their color for both gems. Future Frenzy has two
  gems, both behind secret pad 29 (20 relics): its box gem and a "Secret Entrance Clear Gem".
- Without `relic_checks`, Hang 'em High's Yellow Gem and Future Frenzy's clear gem (behind secret pads 27 and 29) are
  left out; their items stay.

**Shuffle.** The 25 main levels are shuffled across all warp rooms. The 5 secret levels and the 5 bosses stay in place.

**Locations**

| Check | Count | Option |
|---|---|---|
| Exit a level normally | 25 + 5 secret | always |
| Beat a boss (Tiny, Dingodile, N. Tropy, N. Gin) | 4 | always |
| Crystal | 25 | always |
| Clear gems and colored gems | 45 | `gem_checks` |
| Sapphire and Gold relic | 2 × 30 | `relic_checks` |
| Platinum relic | 30 | `platinum_relics` (needs `relic_checks`) |

Getting a better relic tier straight away also sends the lower tiers.

**Items:** 25 Crystals, the gems (clear and colored), Relics, the 5 powers (Crash Dash included), and Extra Life /
Wumpa Fruit as filler (plus the optional No Lives Trap).

**Item style** (decided 2026-11-22): level-specific items, like C2AP: "Toad Village Crystal", "Toad Village Clear
Gem", "Toad Village Relic". Each item turns on its own level's bit, so the warp room shows exactly what the player
holds; logic counts the group (any 5 crystals open Tiny, etc.). A level's bit is still held at 0 while its check is
open there, so the total can be one lower until the next level (accepted).

**Relics and the secret levels** (decided 2026-11-22, like C2AP's secret hub). Secret levels are **not** items: the
game opens them from the relic count, live (BizHawk), so the Relic items are that count. The client writes the sapphire bit of
each received level Relic item; the game then opens the secret
levels by itself. The secret warp room's pad slots open at 5, 10, 15, 20 and 25 relics (owner, BizHawk; the center pad appears at 5):
26 Ski Crazed, 27 Hang 'em High's second entry (to the Yellow Gem), 28 Area 51?, 29 Future Frenzy's second entry (to
its gem), 30 Rings of Power. Hot Coco (Road Crash's alien sign) and Eggipus Rex (Dino Might!'s Yellow Gem path) are
secret exits, not relic-gated. A main level's time trial clock only appears once you own its crystal, as in the
game: the client keeps a level's crystal bit off until its Crystal item arrives, so relic checks need that item in logic
(BizHawk: no clock in Gee Wiz after finishing it, clock right after receiving the Gee Wiz Crystal). Relics need Crash
Dash except in the ride levels 3, 5, 8, 14, 17, 18, 22, 24, 26, 28,
30, and in Hot Coco and Eggipus Rex (owner). Secret levels 26, 28 and 30 have no crystal, only clear gems and a relic:
Ski Crazed one (all boxes), Area 51? and Rings of Power two each (all boxes; first in the race). Hot Coco and Eggipus
Rex have one each, so 38 of the 40 clear gems are known. A level's own
sapphire and gold bits are held at 0 while it is the active level, so the game can award the relic; what it awards
(sapphire bit, gold bit, both = platinum) gives that level's relic checks, lower tiers included.

**Goal** (`goal` option). Beating Dr. N. Cortex is always required. Gems and relics are items, so the extra goals
count received items (no RAM needed):

| Value | Beat Cortex while holding |
|---|---|
| `cortex` (default) | nothing more |
| `cortex_all_gems` | all 45 gems (forces `gem_checks` on) |
| `cortex_all_relics` | all 30 relics, any tier (forces `relic_checks` on) |
| `cortex_105` | all 25 crystals, 45 gems and 30 relics (forces both on) |

The Cortex event then needs those items too, and the client only sends the goal once they are received.

**Logic**

- Bosses open at a total of 5, 10, 15, 20 and 25 crystals (the game counts the total, not per room). Warp room r is
  reached by beating boss r - 1, so a level behind a room r button needs `5 * (r - 1)` crystals. Archipelago's fill
  guarantees the first 5 crystals are reachable from room 1 alone. A unit test will check that on many seeds.
- Every level can be finished, and its crystal collected, with no powers.
- Gems and relics are tracked per level, not per room, because shuffle moves levels across rooms:
  - **Gems:** a table of the powers needed to break every box. For example, some warp room 4 levels need Death
    Tornado Spin for a bonus round gap, and some warp room 5 levels need Fruit Bazooka for boxes out of reach.
    Speedrun tricks are never required.
  - **Relics:** need Crash Dash, except in the vehicle levels. The owner will provide the list of no-boots levels.
- Secret levels need their vanilla relic count of Relic items.

**Risks to test before building**

1. ✅ *Secret levels follow the relic count live* (no separate flag): Relic items drive them (see above).
2. ~~*Detecting a normal level exit.*~~ ✅ the "level completed" field 0x80068F64 (bit = level ID).
3. ✅ *Relic bits and tiers:* sapphire 0x800691B4, gold 0x800691BC (8 bytes each, bit = level ID), platinum =
   both bits.
4. ✅ *Cross-room level swap.* Future Frenzy loaded from Toad Village's button, no hang; leaving it returns to room 1.
5. *Crash Dash bit.* Masking it so beating Cortex can still be seen, while the item controls it.
6. *Warp room state follows the crystal total.* At 5 crystals, warp room 1 hides its level buttons until Tiny is
   beaten (a separate "boss beaten" flag). So received crystals can hide unplayed levels until that room's boss is
   beaten. That is fine for logic, because the boss needs the same crystals, but the flag must be found, and the
   client must never write more crystal bits than the 25 main levels.
   **Changing the total while a room shows its buttons leaves the room with no buttons at all** (BizHawk, round 2b).
   So crystal changes must happen outside the warp room (in a level, applied on the way back) or be followed by a
   reload of the warp room (round 2e: both work). The client writes crystals freely outside the warp room; in it,
   it waits until the room has loaded, and a change that crosses a multiple of 5 is written together with a reload
   (scene request 02). After the game awards a crystal there, the total isn't lowered for a few polls, in case the
   item was our own Crystal.
   Owner's optimization (implemented; ✅ round 2d B): crossing 5r only changes warp room r, so the reload only
   happens when Crash stands in room r. ❌ The room value guessed from round 2d (0x80068FA4) is wrong, so for now the
   client always reloads on crossing 5r while in the hub.
   A room reads the total only when it is rebuilt (Crash walks far away and back, or comes back from a level), so
   crystals received while standing at a room appear late. Open risk: right after a level the game sets the crystal
   bit in the warp room; if that crystal's item belongs to someone else, the total is one too high for one poll
   until the client clears it again. If the room reacts in that moment (the boss button rising), the room may show
   the wrong state until it is rebuilt. Test with the client.

## Open questions (see tools/VERIFY.md)

1. Bit layout of `CRYSTALS` and `GEMS` (guess: bit = level ID).
2. Bits of the colored gems and of the six gem path clear gems.
3. Which globals are the respawn counter and the game state (guessed from Crash 1's layout).
4. Whether a boss's power bit appears in the boss level (needed for the defeat check) or only back in the warp room.
5. Whether a room's elevator or boss button reads the power bits (it must not, or received powers would open rooms).
6. Whether lives/masks written in the warp room carry into the next level.
7. Where the disc ID sits in RAM (`SERIAL_KNOWN_OFFSETS`).
8. Whether late scene requests are safe (level shuffle).
