# Crash Bandicoot 3: Warped (PS1) Setup Guide

## Required software

- [Archipelago](https://github.com/ArchipelagoMW/Archipelago/releases) 0.6.8 or newer.
- [BizHawk](https://tasvideos.org/BizHawk/ReleaseHistory) 2.9.1 or newer (2.10 recommended), Windows prerequisites
  installed.
- `crash3.apworld` from the [C3AP releases](https://github.com/caioaletroca/C3AP/releases).
- Your own NTSC-U disc image of Crash Bandicoot 3: Warped (SCUS-94244) and a PS1 BIOS. These are not provided.

## Installation

1. Double-click `crash3.apworld` (or copy it to `Archipelago/custom_worlds`).
2. In BizHawk, set the PSX core to **Nymashock** (`Config > Preferred Cores > PSX`).

## Create a YAML

Use the Archipelago Launcher's *Options Creator* or *Generate Template Options*, and pick "Crash Bandicoot 3".

## Playing

1. Start a **new game** (save files from vanilla play will confuse the client).
2. Open the Archipelago Launcher and click **BizHawk Client**.
3. In BizHawk, open `Tools > Lua Console` and run `data/lua/connector_bizhawk_generic.lua` from your
   Archipelago folder.
4. In the client, connect to the server (`/connect address:port`) and enter your slot name.

Keep the client running while you play: it handles crystals, powers, gems and level shuffle live.
Avoid loading save states in the middle of a level: a state with different crystals or gems can look like a new
check to the client.
