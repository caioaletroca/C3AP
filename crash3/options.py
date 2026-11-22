from dataclasses import dataclass

from Options import DeathLink, DefaultOnToggle, OptionGroup, PerGameCommonOptions, Range, Toggle


class GemChecks(DefaultOnToggle):
    """Make the gems of the 25 main levels checks: each level's clear gem, the clear gems behind colored gem paths and
    four of the colored gems. The five colored gems become items that open their gem paths.

    Gems need every box broken (colored gems mostly without dying), so turning this off makes the game much shorter.
    Without gem checks there are exactly as many checks as crystals and powers, so the powers are left out of logic
    (they are still items).
    """

    display_name = "Gem Checks"


class LevelShuffle(Toggle):
    """Shuffle which level each warp room button leads to.

    Levels are shuffled among the buttons of their own warp room; bosses keep their buttons. The client swaps the
    game's level request for the shuffled level (tested in BizHawk, including across warp rooms).
    """

    display_name = "Level Shuffle"


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
    gem_checks: GemChecks
    level_shuffle: LevelShuffle
    trap_chance: TrapChance
    death_link: DeathLink


option_groups: list[OptionGroup] = [
    OptionGroup("Checks", [GemChecks]),
    OptionGroup("Shuffle", [LevelShuffle]),
    OptionGroup("Traps", [TrapChance]),
]

option_presets: dict[str, dict[str, object]] = {
    "Casual": {"gem_checks": False},
    "Full": {"gem_checks": True},
}
