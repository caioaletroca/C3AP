from dataclasses import dataclass

from Options import Choice, DeathLink, DefaultOnToggle, OptionGroup, PerGameCommonOptions, Range, Toggle


class Goal(Choice):
    """What you need to win. Beating Dr. N. Cortex (25 crystals) is always required.

    - Cortex: nothing more.
    - Cortex All Gems: also hold every gem item (turns on Gem Checks).
    - Cortex All Relics: also hold every relic item (turns on Relic Checks).
    - Cortex 105: also hold every gem and relic item (turns on both).

    Gems and relics are counted as received items, so they can come from anywhere in the multiworld.
    """

    display_name = "Goal"
    option_cortex = 0
    option_cortex_all_gems = 1
    option_cortex_all_relics = 2
    option_cortex_105 = 3
    default = 0

    @property
    def needs_gems(self) -> bool:
        return self.value in (self.option_cortex_all_gems, self.option_cortex_105)

    @property
    def needs_relics(self) -> bool:
        return self.value in (self.option_cortex_all_relics, self.option_cortex_105)


class GemChecks(DefaultOnToggle):
    """Make the gems checks: every level's clear gem, the clear gems behind colored gem paths and the five colored gems.
    Each level's clear gem becomes an item, and the five colored gems become items that open their gem paths.

    Gems need every box broken (colored gems mostly without dying), so turning this off makes the game much shorter.
    """

    display_name = "Gem Checks"


class RelicChecks(DefaultOnToggle):
    """Make the time trial relics checks: a Sapphire and a Gold relic in each level. Each level's relic becomes an item;
    the relic items you hold open the secret warp room (5, 10, 15, 20 and 25 relics), as in the game.

    Off: no relic checks or items, so the secret levels and the two gems behind the secret warp room are left out.
    """

    display_name = "Relic Checks"


class PlatinumRelics(Toggle):
    """Also make each level's Platinum relic a check (needs Relic Checks). Platinum times are hard."""

    display_name = "Platinum Relics"


class LevelShuffle(Choice):
    """Shuffle which level each warp room button leads to. Bosses and secret levels keep their places.

    - Vanilla: no shuffle.
    - Within Rooms: levels are shuffled among the buttons of their own warp room.
    - All Rooms: the 25 levels are shuffled across all warp rooms.

    The client swaps the game's level request for the shuffled level (tested in BizHawk, across warp rooms too).
    """

    display_name = "Level Shuffle"
    option_vanilla = 0
    option_within_rooms = 1
    option_all_rooms = 2
    alias_false = 0
    alias_true = 1
    default = 0


class TrapChance(Range):
    """Chance (in percent) for each filler item to be a trap instead.

    No Lives Trap: you play your next level with 0 lives, so one death is a game over. Back in the warp room, your lives
    come back (plus any you picked up in the level).
    """

    display_name = "Trap Chance"
    range_start = 0
    range_end = 100
    default = 0


@dataclass
class Crash3Options(PerGameCommonOptions):
    goal: Goal
    gem_checks: GemChecks
    relic_checks: RelicChecks
    platinum_relics: PlatinumRelics
    level_shuffle: LevelShuffle
    trap_chance: TrapChance
    death_link: DeathLink


option_groups: list[OptionGroup] = [
    OptionGroup("Checks", [GemChecks, RelicChecks, PlatinumRelics]),
    OptionGroup("Shuffle", [LevelShuffle]),
    OptionGroup("Traps", [TrapChance]),
]

option_presets: dict[str, dict[str, object]] = {
    "Casual": {"gem_checks": False, "relic_checks": False},
    "Full": {"gem_checks": True, "relic_checks": True, "level_shuffle": "all_rooms"},
    "105%": {"goal": "cortex_105", "gem_checks": True, "relic_checks": True, "platinum_relics": True,
             "level_shuffle": "all_rooms"},
}
