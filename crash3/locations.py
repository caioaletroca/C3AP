from BaseClasses import Location

from .data import (
    BOSSES, COLORED_GEM_LEVELS, FINAL_BOSS, GEM_LEVELS, LEVELS, MAIN_LEVELS, PATH_GEM_LEVELS, RACE_GEM_LEVELS,
    RELIC_LEVELS, SECRET_LEVELS,
)
from .items import BASE_ID, GAME_NAME


class Crash3Location(Location):
    game = GAME_NAME


CORTEX_EVENT = FINAL_BOSS.defeat_location
"""Event location (no ID) that holds the locked Victory item"""

RELIC_TIERS: tuple[str, ...] = ("Sapphire", "Gold", "Platinum")

# IDs are derived from the level ID so they never change when the list is reordered.
CRYSTAL_OFFSET = 0x000
BOSS_OFFSET = 0x000      # bosses and levels share one ID range: their level IDs never collide
CLEAR_GEM_OFFSET = 0x100
PATH_GEM_OFFSET = 0x200
COLORED_GEM_OFFSET = 0x300
EXIT_OFFSET = 0x400
RELIC_OFFSETS: dict[str, int] = {"Sapphire": 0x500, "Gold": 0x600, "Platinum": 0x700}
RACE_GEM_OFFSET = 0x800

EXIT_LEVELS = MAIN_LEVELS + SECRET_LEVELS

location_name_to_id: dict[str, int] = {
    **{level.crystal_location: BASE_ID + CRYSTAL_OFFSET + level.lid for level in MAIN_LEVELS},
    **{boss.defeat_location: BASE_ID + BOSS_OFFSET + boss.lid for boss in BOSSES},
    **{level.clear_gem_location: BASE_ID + CLEAR_GEM_OFFSET + level.lid for level in GEM_LEVELS},
    **{level.path_gem_location: BASE_ID + PATH_GEM_OFFSET + level.lid for level in PATH_GEM_LEVELS},
    **{level.colored_gem_location: BASE_ID + COLORED_GEM_OFFSET + level.lid for level in COLORED_GEM_LEVELS},
    **{level.exit_location: BASE_ID + EXIT_OFFSET + level.lid for level in EXIT_LEVELS},
    **{level.relic_location(tier): BASE_ID + RELIC_OFFSETS[tier] + level.lid
       for level in RELIC_LEVELS for tier in RELIC_TIERS},
    **{level.race_gem_location: BASE_ID + RACE_GEM_OFFSET + level.lid for level in RACE_GEM_LEVELS},
}


def level_location_names(level_name: str) -> set[str]:
    return {name for name in location_name_to_id if name.startswith(f"{level_name} - ")}


location_name_groups: dict[str, set[str]] = {
    "Crystals": {level.crystal_location for level in MAIN_LEVELS},
    "Bosses": {boss.defeat_location for boss in BOSSES},
    "Exits": {level.exit_location for level in EXIT_LEVELS},
    "Clear Gems": {level.clear_gem_location for level in GEM_LEVELS}
                  | {level.path_gem_location for level in PATH_GEM_LEVELS}
                  | {level.race_gem_location for level in RACE_GEM_LEVELS},
    "Colored Gems": {level.colored_gem_location for level in COLORED_GEM_LEVELS},
    "Relics": {level.relic_location(tier) for level in RELIC_LEVELS for tier in RELIC_TIERS},
    "Secret Levels": {name for level in SECRET_LEVELS for name in level_location_names(level.name)},
    **{level.name: level_location_names(level.name) for level in LEVELS if level_location_names(level.name)},
}
