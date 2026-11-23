# Crash Bandicoot 3: Warped (PS1) for Archipelago

An [Archipelago](https://archipelago.gg) world (apworld) and BizHawk client for **Crash Bandicoot 3: Warped** (PS1,
1998), NTSC-U version (SCUS-94244).

Archipelago is a multi-game randomizer: the items of every game in a session are shuffled across all the players'
worlds. In Crash Bandicoot 3, finishing levels, collecting crystals, gems and relics and beating bosses sends items
to other players (or to yourself), and the crystals, gems, relics and powers come back to you as items.

> **Status: 1.0.** Playtested in BizHawk from a new game to Cortex: per-level items, exits, crystals, gems, relics,
> the secret levels (Hot Coco and Eggipus Rex included) and level shuffle across warp rooms. A few gem bits are still
> learned in play (see below); the test log is in [tools/VERIFY.md](tools/VERIFY.md). Sister project of
> [C1AP](https://github.com/caioaletroca/C1AP).

## What is randomized?

- **Crystals, gems and relics are items, one per level**, as in C2AP: "Toad Village Crystal", "Toad Village Clear
  Gem", "Toad Village Relic". Each one turns on its own level in the game. The bosses open at a total of 5, 10, 15, 20
  and 25 crystals, and the secret warp room at 5, 10, 15, 20 and 25 relics, as in the game.
- **Powers.** Super Body Slam, Double Jump, Death Tornado Spin, Fruit Bazooka and Crash Dash are items.
- **Colored gems** (with *Gem Checks*). Red, Green, Purple, Blue and Yellow are items that open their gem paths.
- **Level shuffle** (optional). Changes which level each warp room button leads to, within its room or across all
  rooms. Bosses and secret levels stay in place.
- **Filler.** Extra lives and Aku Aku masks.
- **Traps** (optional). *No Lives Trap*: you play your next level with 0 lives, then they come back in the warp room.

The locations are each level's normal exit and crystal, the four boss defeats, and optionally every gem (*Gem
Checks*) and the Sapphire and Gold relics (*Relic Checks*, plus Platinum with *Platinum Relics*). The secret levels
Ski Crazed, Area 51? and Rings of Power are included with *Relic Checks*. The secret-exit levels count too: entering
Hot Coco (Road Crash's alien sign) and Eggipus Rex (Dino Might!'s Yellow Gem path, with *Gem Checks* only) is a check,
and so are their exit, gem and relics. As in the game, a level's time trial clock only appears once you own its
crystal, so its relics need its Crystal item. With the defaults there are 164 checks (194 with platinum).

## Goal

Defeat Dr. N. Cortex. With the `goal` option you can also need every gem item, every relic item, or both (105%).

## Options

| Option | Values | Default |
|---|---|---|
| `goal` | `cortex`, `cortex_all_gems`, `cortex_all_relics`, `cortex_105` | `cortex` |
| `gem_checks` | `true` / `false`: gems are checks and items | `true` |
| `relic_checks` | `true` / `false`: Sapphire and Gold relics are checks, relics are items, secret levels included | `true` |
| `platinum_relics` | `true` / `false`: Platinum relics are checks too | `false` |
| `level_shuffle` | `vanilla`, `within_rooms`, `all_rooms` | `vanilla` |
| `trap_chance` | 0-100: % of filler replaced by a No Lives Trap | 0 |
| `death_link` | `true` / `false` | `false` |

## Setup

What you need:

- [Archipelago](https://github.com/ArchipelagoMW/Archipelago/releases) 0.6.8 or newer.
- [BizHawk](https://tasvideos.org/BizHawk/ReleaseHistory) 2.9.1 or newer, with the PSX core set to **Nymashock**.
- `crash3.apworld` from the [releases page](https://github.com/caioaletroca/C3AP/releases).
- Your own NTSC-U disc image of Crash Bandicoot 3: Warped (SCUS-94244) and a PS1 BIOS. These are not provided.

Steps:

1. Double-click `crash3.apworld` to install it, or copy it into `Archipelago/custom_worlds`.
2. Make a YAML with the Archipelago Launcher's *Options Creator*, picking "Crash Bandicoot 3".
3. After the game is generated and hosted, start a **new game** in BizHawk.
4. Open **BizHawk Client** from the Archipelago Launcher.
5. In BizHawk, open `Tools > Lua Console` and run `data/lua/connector_bizhawk_generic.lua` from your Archipelago
   folder.
6. Connect the client to the server and enter your slot name.

The full guides are the [setup guide](crash3/docs/setup_en.md) and the
[game page](crash3/docs/en_Crash%20Bandicoot%203.md).

## Known issues

- Only the NTSC-U version (SCUS-94244) is supported.
- A few RAM details are still marked `VERIFY` in `crash3/ram.py`; the playtested paths are listed in tools/VERIFY.md.
- Death Link only sends deaths.
- Four gem path gems, Future Frenzy's second gem and the two race gems have unknown RAM bits: the client learns
  them when you win them and asks you to report the bit.
- Avoid loading save states in the middle of a level.

## Development

You need an Archipelago 0.6.8+ source checkout (Python 3.11-3.13).

```sh
# link the world into the Archipelago checkout
ln -s /path/to/C3AP/crash3 /path/to/Archipelago/worlds/crash3          # Linux/macOS
mklink /J C:\path\to\Archipelago\worlds\crash3 C:\path\to\C3AP\crash3  # Windows

# from the Archipelago checkout
AP_TEST_WORLDS=crash3 python -m pytest worlds/crash3/test test/general
```

| Path | What |
|---|---|
| `crash3/data.py` | Levels, bosses, powers, gems (static game data) |
| `crash3/world.py` | The Archipelago world: regions, items, rules, slot data |
| `crash3/shuffle.py` | Level-order shuffle (within rooms or across all rooms) |
| `crash3/ram.py` | RAM map (addresses marked `VERIFY` are unconfirmed) |
| `crash3/watcher.py` | Client game logic, pure and unit-tested |
| `crash3/trap.py` | No Lives Trap state |
| `crash3/client.py` | BizHawk I/O |
| `tools/` | BizHawk Lua script used to verify the RAM map, and the checklist |
| `docs/DESIGN.md` | Design notes |

No game data (disc images, BIOS, saves) belongs in this repository.

## AI usage

This project was built with heavy use of AI. Most of the code, tests and documentation were written by
[Claude Code](https://claude.com/claude-code), an AI coding assistant, working under my direction. That includes the
world, the BizHawk client, the RAM research and the Lua test script. Commits it co-wrote are marked
`Co-Authored-By: Claude`.

My part is the design decisions and testing: every client feature gets played in BizHawk, and the RAM addresses are
confirmed against the real game before anything is marked as working (the results go in
[tools/VERIFY.md](tools/VERIFY.md)).

## Credits

- RAM and level data: the Crash 3 decompilation notes (SomeoneIsWorking/crash3-decomp), GameShark code lists, and the Crash 1 decompilation
  ([esplonky/c1](https://github.com/esplonky/c1)) for the shared engine layout.
- Built on Archipelago's BizHawk client framework.

## License

MIT. Crash Bandicoot is a trademark of its owners. This project is not affiliated with them.
