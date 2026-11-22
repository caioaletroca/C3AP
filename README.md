# Crash Bandicoot 3: Warped (PS1) for Archipelago

An [Archipelago](https://archipelago.gg) world (apworld) and BizHawk client for **Crash Bandicoot 3: Warped** (PS1,
1998), NTSC-U version (SCUS-94244).

Archipelago is a multi-game randomizer: the items of every game in a session are shuffled across all the players'
worlds. In Crash Bandicoot 3, collecting crystals and gems and beating bosses sends items to other players (or to
yourself), and the crystals, powers and colored gems come back to you as items.

> **Status: pre-alpha, not playable yet.** The world generates, but none of the client's RAM addresses have been
> confirmed in an emulator. The checklist is in [tools/VERIFY.md](tools/VERIFY.md). Sister project of
> [C1AP](https://github.com/caioaletroca/C1AP).

## What is randomized?

- **Crystals.** Each warp room's boss opens with five more crystals, as in the game, but the crystals are items.
- **Powers.** Super Body Slam, Double Jump, Death Tornado Spin and Fruit Bazooka are items. Beating a boss is a check.
- **Colored gems** (with *Gem Checks*). Red, Green, Purple, Blue and Yellow are items that open their gem paths.
- **Level shuffle** (optional, experimental). Changes which level each warp room button leads to, within its room.
- **Filler.** Extra lives and Aku Aku masks.
- **Traps** (optional). *No Lives Trap*: you play your next level with 0 lives, then they come back in the warp room.

The locations are each main level's crystal, the four boss defeats and (with *Gem Checks*) the clear gems, the gem
path clear gems and four colored gems: 64 in total.

## Goal

Defeat Dr. N. Cortex.

## Options

| Option | Values | Default |
|---|---|---|
| `gem_checks` | `true` / `false`: gems are locations, colored gems are items | `true` |
| `level_shuffle` | `true` / `false` (experimental) | `false` |
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
- The RAM map is unconfirmed (see the status note above).
- Death Link only sends deaths.
- Time trials, relics, the secret levels and the Yellow Gem's location are not included yet.
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
| `crash3/shuffle.py` | Level-order shuffle |
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
