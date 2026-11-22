# Crash Bandicoot 3

## What does randomization do to this game?

- **Crystals** are items. The game's own boss gates work as usual: each warp room's boss (and the elevator to the next
  room) opens once you hold enough crystals. Five crystals per room, so 25 for Dr. N. Cortex.
- **Powers** (Super Body Slam, Double Jump, Death Tornado Spin, Fruit Bazooka) are items. Beating a boss is a check;
  the power you get comes from wherever its item was found. Crash Dash (Cortex's reward) stays vanilla.
- **Colored gems** (Red, Green, Purple, Blue, Yellow) are items, when *Gem Checks* is on. Their gem paths open once you
  receive them.
- **Level shuffle** (optional) changes which level each warp room button leads to, within the same room.
- Leftover slots are filled with extra lives and Aku Aku masks. With *Trap Chance*, some of them are *No Lives Traps*
  instead: you play your next level with 0 lives (one death is a game over). Back in the warp room you get your lives
  back, plus any you picked up; a game over ends the trap without giving them back.

## What is the goal?

Defeat Dr. N. Cortex.

## What are the locations?

- Each of the 25 main levels' crystal.
- Defeating Tiny Tiger, Dingodile, N. Tropy and N. Gin.
- With *Gem Checks*: each main level's clear gem, the second clear gem behind the six gem paths, and the Red, Purple,
  Blue and Green gems.

Time trial relics and the secret levels are not part of v0.1.

## What does another world's item look like in Crash Bandicoot 3?

The game shows nothing special. The item is sent as soon as the client sees the check.

## When the player receives an item, what happens?

Crystals, powers and colored gems are written into the game right away. Filler (lives, masks) and traps are applied
the next time you are in a warp room, and carry into the next level.

## Known limitations (v0.1)

- NTSC-U (SCUS-94244) only.
- The RAM map has not been fully confirmed in an emulator yet (see `tools/VERIFY.md`).
- Death Link only sends deaths.
- No time trials, relics, secret levels or the Yellow Gem's location (the Yellow Gem is still an item).
