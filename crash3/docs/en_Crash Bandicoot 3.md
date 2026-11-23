# Crash Bandicoot 3

## What does randomization do to this game?

- **Crystals, gems and relics are items, one per level** ("Toad Village Crystal", "Toad Village Clear Gem", "Toad
  Village Relic"). Each one turns on that level's crystal, gem or relic in the game, so the warp rooms and the pause
  menu show what you hold. The boss buttons open at a total of 5, 10, 15, 20 and 25 crystals; the secret warp room
  opens at 5 relics, and its levels at 5, 10, 15, 20 and 25.
- **Powers** (Super Body Slam, Double Jump, Death Tornado Spin, Fruit Bazooka, Crash Dash) are items. Beating a boss is
  a check; the power you get comes from wherever its item was found.
- **Colored gems** (Red, Green, Purple, Blue, Yellow) are items, when *Gem Checks* is on. Their gem paths open once you
  receive them.
- **Level shuffle** (optional) changes which level each warp room button leads to, within the same room or across all
  rooms.
- Leftover slots are filled with extra lives and Aku Aku masks. With *Trap Chance*, some of them are *No Lives Traps*
  instead: you play your next level with 0 lives (one death is a game over). Back in the warp room you get your lives
  back, plus any you picked up; a game over ends the trap without giving them back.

## What is the goal?

Defeat Dr. N. Cortex. Depending on the `goal` option, you also need every gem item, every relic item, or both.

## What are the locations?

- Finishing each of the 25 main levels normally (the exit), and its crystal.
- Defeating Tiny Tiger, Dingodile, N. Tropy and N. Gin.
- With *Gem Checks*: each level's clear gem, the clear gems behind the six gem paths, and the five colored gems.
- With *Relic Checks*: each level's Sapphire and Gold relic (Platinum too with *Platinum Relics*). Winning a better
  relic straight away also sends the lower ones. The secret levels Ski Crazed, Area 51? and Rings of Power (exit,
  clear gems, relics), and the two gems behind the secret warp room (Hang 'em High's Yellow Gem, Future Frenzy's
  clear gem) are included.

Relics need Crash Dash in logic, except in the ride levels.

## What does another world's item look like in Crash Bandicoot 3?

The game shows nothing special. The item is sent as soon as the client sees the check.

## When the player receives an item, what happens?

Crystals, gems, relics and powers are written into the game right away. Filler (lives, masks) and traps are applied
the next time you are in a warp room, and carry into the next level.

## Known limitations

- NTSC-U (SCUS-94244) only.
- Hot Coco and Eggipus Rex are not included yet.
- While you play a level, its own crystal, gem and relic are hidden so the game can award them; the warp room may
  count one less until you leave it.
- Death Link only sends deaths.
