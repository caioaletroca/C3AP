# Address verification (milestone M0)

Nothing in `crash3/ram.py` has been seen in a running game yet. The addresses come from GameShark code lists (GS),
the Crash 3 decompilation notes (DECOMP) and guesses from Crash 1's layout. Before C3AP can be played, each test
below needs a short BizHawk run. Record the result (✅ / ❌ + what you saw) and fix `ram.py` where needed.

**Setup:** BizHawk 2.9.1+ (Nymashock core), NTSC-U disc (SCUS-94244), a **new game**, no Archipelago client.
Open `Tools > Lua Console` and run `tools/c3ap_ram_watch.lua`. It draws the watched values on screen and logs every
change with the frame number. After each block of tests, copy the Lua console log and paste it back.

Keys: `U` globals snapshot, `L` globals diff, `G` disc ID search, `O` all crystals, `B` powers off/on, `Y` shuffle test,
`N` +1 life, `M` +1 mask.

## Round 1: the basics (about 10 minutes, warp room 1 only)

| # | Test | Expect | Result |
|---|---|---|---|
| 1 | In the warp room, press `G` | disc ID found; note every offset | |
| 2 | Watch `LEVEL>>8` in the warp room, then enter Toad Village | `02` in the warp room, `0B` in Toad Village | |
| 3 | When entering the level, watch `SCENE_REQ` | goes `FFFFFFFF` → `0000000B` → `FFFFFFFF` (how many frames?) | |
| 4 | In Toad Village: press `U`, die once, wait for the respawn, press `L` | one global goes up by `0x100`. Is it index 5 (`RESPAWN?`)? | |
| 5 | Finish Toad Village normally (no crystal yet is fine) | note what `GAMESTATE?` does on the way back | |
| 6 | Play Toad Village again and grab the crystal, finish | one new `CRYSTALS` bit: write down the bit number (guess: bit 11 = 0x0B) | |
| 7 | Break every box in Toad Village and finish | one new `GEMS` bit (guess: bit 11) | |
| 8 | In the warp room press `N` and `M`, then enter a level | HUD shows +1 life and Aku Aku | |

## Round 2: bosses and room gates

Owner's notes: the game keys warp room state off the crystal **total**. At 5 crystals warp room 1 hides its level
buttons and shows only the boss button; after the boss, the 5 buttons come back with the boss button and the fence to
room 2 drops. So a second "boss beaten" flag must exist. The first try set all 48 crystal bits (`O`), which broke that.

| # | Test | Expect | Result |
|---|---|---|---|
| 9 | Load a save state from **before** the first `O`. Press `O` once in warp room 1 | log says 5 crystals total; level buttons hide, boss button shows | |
| 10 | Press `U`, beat Tiny Tiger, back in the warp room wait ~10 s, press `L` | the diff shows `POWERS` and the "boss beaten" flag (a word or bit we don't know yet) | |
| 11 | Press `B` in the warp room | log says `poke B: powers ...`; does the fence to room 2 stay down? | |
| 12 | Enter a room 2 level with powers off (`B`) and try a body slam / double jump, then `B` again | difference between powers off and on | |

## Round 2c: what really controls powers and rooms

Save a state in the warp room after beating Tiny first. `T` and `V` each poke one candidate; press again to undo.

| # | Test | Expect | Result |
|---|---|---|---|
| 12a | Warp room: press `B`, then wait ~30 s **without pausing**, then pause and unpause | which one brings `POWERS` back (log line `POWERS 00000000 -> 00000001`)? | |
| 12b | In a level: press `B` (don't pause), try the Super Body Slam (jump, then crouch in the air) | does it still work with bit 0 = 0? | |
| 12c | Warp room: press `T`, then pause/unpause and look at the fence to room 2 | fence back up? `POWERS` drops to 0? | |
| 12d | Load the state, press `V`, same checks | same questions | |

## Round 2e: recovering a stuck room (do this before 2d)

| # | Test | Expect | Result |
|---|---|---|---|
| 12i | From the new-game state, stand at warp room 1 with buttons showing, press `O`, walk far away and back | stuck: no buttons (reproduces round 2b) | |
| 12j | Then press `R` (reload the warp room) and walk to warp room 1 | boss button only? (if so, the client can fix a room by reloading it) | |
| 12k | From the new-game state, enter Toad Village, press `O` **inside the level**, exit with the pause menu | back in the warp room: boss button only? (the client writing between levels) | |
| 12l | From the new-game state, stand at warp room 1 with buttons showing, poke `CRYSTALS` from 0 to 1 bit (hex editor at `0x06912C`, write `00 08`), walk far away and back | buttons still there (the client only reloads when the total crosses 5, 10, 15...) | |

## Round 2d: find the source of the powers

`B`, `T` and `V` now **hold** their value every frame (as the client would) until pressed again. Start each test from
a warp room save state taken after beating Tiny, with nothing held.

| # | Test | Expect | Result |
|---|---|---|---|
| 12d1 | From a warp room 1 state after Tiny (5 crystals): press `U`, walk to warp room 2, press `L` | a word that says which warp room Crash is in (1 → 2) | |
| 12d2 | Load the state, press `O` in warp room 1 (10 crystals: the change only affects room 2), then walk to warp room 2 | room 2 shows only its boss button: changes for other rooms need no reload | |
| 12e | Press `T`, enter any level | does `POWERS` bit 0 come back on level load? **If not, 0x80068F64 is the source** | |
| 12f | Load the state, press `V`, enter any level | same question for 0x80069010 / 0x800691F0 | |
| 12g | Whichever worked: keep it held, exit back to the warp room | is the fence to room 2 back up? do the 5 level buttons hide? | |
| 12h | Load the state, press `B` (hold powers at 0), enter a level and exit back | fence still down? (the client will hold item powers like this) | |

## Round 2f: what builds warp room 1's buttons

✅ 12m (owner, from a clean after-Tiny state): `T` + `R` raises the fence. Releasing `T` and reloading keeps it up:
the boss field is persistent game state (nothing recomputes it), so it really is the source. (The script now puts the
old value back on release.)
✅ 12m: with the boss field at 0, room 1 still shows all 6 buttons after `R` (only the fence reacts). ✅ 12n: powers
held at 0 + `R`: room 1 stays open and the fence stays down, so taking away powers the player hasn't received is
safe for the warp rooms. ✅ 12o: powers held at 0 through a level load (Gee Wiz): the game's rebuild is overwritten.
Room 1's after-boss buttons come from something else (not the boss field, not the powers alone): harmless for the
client, which never writes the boss field.

| # | Test | Expect | Result |
|---|---|---|---|
| 12m | Load the after-Tiny state, press `T` (boss field held at 0), press `R` (reload hub) | room 1: boss button only? fence to room 2 up? | |
| 12n | Release `T`, load the state, press `B` (powers held at 0), press `R` | room 1 must keep 5 levels + boss, fence down (**the client removes powers you don't own**) | |
| 12o | Still holding `B`, enter a level and try the Super Body Slam | gone | |

## Round 3: gems

| # | Test | Expect | Result |
|---|---|---|---|
| 14 | Get the Red Gem in Deep Trouble (or use `O` and go straight there) | one new `GEMS` bit: note it (`COLORED_GEM_BITS["Red"]`) | |
| 15 | Same for Purple (High Time), Blue (Tomb Wader), Green (Flaming Passion) | note each bit | |
| 16 | In the warp room, set the Red bit by hand, enter Bone Yard | the red gem path platform appears | |
| 17 | Bone Yard's red path clear gem | a second Bone Yard `GEMS` bit: note it (`PATH_GEM_BIT_BY_LID`) | |

## Round 4: level shuffle (EXPERIMENTAL)

| # | Test | Expect | Result |
|---|---|---|---|
| 18 | In warp room 1 press `Y`, then enter Toad Village's button | Under Pressure loads instead, no hang. Log says "caught" or "missed" | |
| 19 | Finish (or exit) that Under Pressure | back in warp room 1 at Toad Village's button, no crash | |
| 20 | Repeat 18 a few times | never hangs. **A hang means level shuffle must stay off.** | |

## Round 5: lives and game over (for the trap)

| # | Test | Expect | Result |
|---|---|---|---|
| 21 | In a level, collect an extra life | does `LIVES` change right away or only at the level end? | |
| 22 | In the warp room set `LIVES` to 0 (hex editor at `0x068F58`), enter a level, die | game over; note `GAMESTATE?` values on the way | |
| 23 | Beat Dr. N. Cortex | `POWERS` bit4 (Crash Dash) appears: that is the goal signal | |

## Round 6: needed for the v1.0 design (docs/DESIGN.md "Target design")

| # | Test | Expect | Result |
|---|---|---|---|
| 24 | Press `Y` **twice** (cross-room test), enter Toad Village's button | Future Frenzy (warp room 4) loads, no hang; finish or exit it and land back in room 1 | |
| 25 | `U` in a level, finish it normally, `L` back in the warp room | which globals changed on a normal exit (a "level done" bit or counter?) | |
| 26 | `U` in a level, exit through the pause menu, `L` | compare with test 25: the exit check must not fire here | |
| 27 | Win a time trial relic (Sapphire is enough) | which globals changed (`U` before the run, `L` after): the relic field and how the tier is stored | |
| 28 | If test 27 found the relic field: set relic bits by hand in the warp room until the first secret level should open | does the center pad open? With more relics, do levels 26-30 open one by one? | |
| 29 | After test 28, take relics away again | do the secret levels close again (recomputed from the count) or stay open (a separate flag)? | |
| 30 | Beat Cortex, then clear the Crash Dash bit (`POWERS` bit 4) in a level | Crash runs at normal speed (the bit really is the boots) | |

## What each test unlocks

- 1: the client recognizes the game (`SERIAL_KNOWN_OFFSETS` in `client.py`).
- 2, 3: the client knows where Crash is; level shuffle can catch the request.
- 4: Death Link (`RESPAWN_COUNT`).
- 6, 7: crystal and clear gem checks (`CRYSTAL_BIT_BY_LID`, `CLEAR_GEM_BIT_BY_LID`).
- 8, 21, 22: filler and the No Lives Trap (`GAMESTATE_GAME_OVER`).
- 9-13: bosses are checks, powers are items, room gates count crystals.
- 14-17: colored gems as items, gem path checks.
- 18-20: level shuffle.
- 23: the goal.
- 24: shuffling levels across warp rooms.
- 25, 26: "exit the level" checks.
- 27-29: relic checks, relics as items, secret levels as items (or as one progressive item).
- 30: Crash Dash as an item.

## Results log

**Round 2b (owner's warp room test, from a new game):** all five warp rooms sit in one place; a room's buttons
appear with a transition when Crash walks up to it. Writing crystals (`O`):
- far from warp room 1, then walking up: ✅ only the boss button, as in vanilla;
- next to warp room 1 with its buttons showing: nothing changes; stepping a little away and back still shows the 5
  level buttons; only after walking **far** away and back do they hide.
- ❌ and then the room is **stuck with no buttons at all, not even the boss button** (screenshot: warp room 1, 5
  crystals, empty). Changing the total while a room shows its buttons breaks the room's button state.
In vanilla the boss-only state appears as soon as the warp room loads after the 5th level (during the black screen).
So the client must not change the crystal total while Crash stands in the warp room, unless it reloads the room.

**Round 2d, part C:** ✅ **0x80068F64 is the "boss beaten" flag field.** It gained bit 6 (Tiny's scene 06) when Tiny
was beaten. With `T` holding it at 0, loading the warp room 1 state brought **the fence to room 2 back up**
(screenshot). Holding it at 0 and entering Gee Wiz did not take the Super Body Slam away (`POWERS` stayed 1; the
level-load rebuild may only add powers). Guess: bit = boss scene ID (Dingodile 03, N. Tropy 04, N. Gin 05,
Cortex 07); VERIFY with the next bosses. 0x80069010 gains a bit on entering a level (0x48 → 0x58 in Gee Wiz) and
0x800691F0 changes during transitions: not boss flags.
⚠️ But warp room 1 still showed the after-Tiny state (5 level buttons + boss button). Likely because the save
state already had room 1's buttons built; to check with a reload (round 2f).



**Round 2d, parts A and B:** the warp rooms are areas of one hub level (no elevator). Walking from room 1 to
room 2 changes 0x80068FA4 (index 43) **0x13 → 0x14**: ❌ but it changes far too often in play: not the room value. The rest of the diff is positions and camera. ✅ B: 10 crystals written in room 1, then walking to
room 2 shows only its boss button: a change for another room needs no reload.

**Round 3d (Bone Yard red path, with `J` all gems and `C` all powers):** ✅ the red path needs Double Jump.
**Bone Yard's path gem = `GEMS` bit 1**, set in the warp room after the level. Level-completed bit 12 set. The other
path gems are probably low bits too (0, 2-9): the `V` key tests them one at a time.

**Round 3c (`J` key, one bit at a time, pause menu):** ✅ colored gems are plain bits in `GEMS`: **56 none, 57 none,
58 Red, 59 Green, 60 Purple, 61 Blue, 62 Yellow, 63 none**. (Each `J` press clears the previous test bit, which is
why only one gem showed at a time.)

**Round 3b (Tomb Wader, blue gem):** ✅ Tomb Wader is scene 0x18; finishing it set level-completed bit 24.
**Blue Gem = `GEMS` bit 61**, again set in the warp room after the level. Guess from vanilla level order (Hang 'em
High's Yellow, Deep Trouble's Red, High Time's Purple, Tomb Wader's Blue, Flaming Passion's Green): Yellow 58, Red 59,
Green 62. To check with the `J` key on the pause menu.

**Round 3 (High Time, purple gem; opened with `O` ×3 + `H`):**
- ✅ `H` (boss field |= 0x78) + 20 crystals opened every warp room. Only Double Jump came along (`POWERS` 1 → 3 in the
  hub), not Death Tornado Spin or Fruit Bazooka: the power rebuild doesn't simply follow bits 4 and 5.
- ✅ High Time is scene 0x1A. **Purple Gem = `GEMS` bit 60**, set back in the warp room ~200 frames after the level,
  like crystals.
- ✅ **0x80068F64 is a "level completed" field, bit = level ID**: finishing High Time normally set bit 26 (0x1A),
  2 frames after returning to the warp room. Bosses are just levels in it (Tiny = bit 6). This gives the v1.0
  "exit the level" check for free.

**Round 2e:** ✅ 12i reproduced the empty room. ✅ 12j: requesting scene 02 (`R`) reloads the warp room and fixes it
(boss button only). ✅ 12k: crystals written inside a level show correctly back in the warp room.

**Round 2c (state loads in between):**
- ✅ `POWERS` **is** the live switch: with bit 0 cleared the Super Body Slam stops working right away, in the warp
  room and in levels, and the pause menu shows no powers. Pausing does not bring it back.
- The game rebuilds `POWERS` **on level load** (just before the scene request), from a source we haven't found.
  For the client that's fine: it rewrites `POWERS` every poll, so a power the player lacks only exists during loading.
- ❌ 0x80069104 is not the source: it is 0 during transitions, 1 in levels and 3 in the warp room after Tiny
  (recomputed). ❌ 0x80069150 bit 16 is set when Tiny's level **loads**, before the fight. Poking either one changed
  nothing.
- New candidates from the round 2 diff: 0x80068F64 (index 27) 0 → 0x40 (bit 6 = Tiny's scene 06), 0x80069010
  (index 70) 0 → 0x48, 0x800691F0 (index 190) 0 → 0x200.

**Round 2 (Tiny Tiger):**
- ✅ `O` (5 crystals: bits 10, 11, 12, 14, 25) shows only the boss button, as in vanilla. Beating Tiny gives the
  normal state (5 buttons + boss, fence down).
- ✅ Tiny is scene 06. `POWERS` bit 0 is set **inside the boss level**, at the defeat (frame 26814, ~380 frames before
  the exit). So the defeat check can be the power bit, as planned.
- Boss exit goes 06 → 3A (a cutscene; 3A is the cutscene scene) → 02, with `GAMESTATE` 0x300 after each.
- ❌ `POWERS` is **not** the source of truth: after `B` cleared it in the warp room, the game set bit 0 again ~980
  frames later (the owner had opened the pause menu, which showed no powers). The game rebuilds `POWERS` from
  something else.
- Diff candidates for the "boss beaten" flag: **0x80069104** (index 131) 1 → 3, **0x80069150** (index 150) 0 → 0x10000.
  Also 0x80068F48 (index 20) 0x63 → 0x600 (looks like "last level" << 8).

**Round 2, first try:** ❌ the old `O` set all 48 crystal bits: the warp room logic broke (it reads the total). `O`
now adds one warp room's five crystals per press. `B` seemed to do nothing (log needed).
Found online: Codebreaker "Have All Sapphires" writes 6 bytes at **0x800691B4**: the sapphire relic field. Gold and
platinum likely follow.

**Round 1 (Toad Village, new game):**
- ✅ 1: disc ID `SCUS_942.44` at MainRAM 0x0092A4, 0x009E19, 0x00B8B7 (in `SERIAL_KNOWN_OFFSETS`).
- ✅ 2: `LEVEL` 02 in the warp room, 0B in Toad Village. `SCENE_ID` changes at once, `LEVEL` ~345 frames later.
  Some entries go through scene **0x3A** first (warp room → 3A → level), others go straight to the level.
- ✅ 3: `SCENE_REQ` holds the level ID for 3 frames, then back to `FFFFFFFF`.
- ✅ 4: respawn counter is index 5 (0x80068F0C): +0x100 per respawn, 0 again in the warp room.
- ✅ 5: `GAMESTATE` 0x100 while playing **and** in the warp room, 0 during level start and respawn, **0x300 on a
  normal exit, 0x400 on a pause-menu exit** (game over still unknown).
- ✅ 6, 7: Toad Village crystal = `CRYSTALS` bit 11, clear gem = `GEMS` bit 11 (bit = level ID). ⚠️ Both bits are set
  **back in the warp room, ~200 frames after `LEVEL` returns to 02**, not in the level. The client now keeps the last
  level watched through the warp room.
- ✅ 8: lives and masks written in the warp room carry into the next level (the warp room HUD shows them). Writes
  inside a level are lost: the level writes lives, masks and fruit back on exit (normal or pause menu).
  Fruit is index 26 (0x80068F60).
