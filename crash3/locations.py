from BaseClasses import Location

from .data import BOSSES, COLORED_GEM_LEVELS, FINAL_BOSS, MAIN_LEVELS, PATH_GEM_LEVELS
from .items import BASE_ID, GAME_NAME


class Crash3Location(Location):
    game = GAME_NAME


CORTEX_EVENT = FINAL_BOSS.defeat_location
"""Event location (no ID) that holds the locked Victory item"""

# IDs are derived from the level ID so they never change when the list is reordered.
CRYSTAL_OFFSET = 0x000
BOSS_OFFSET = 0x000      # bosses and levels share one ID range: their level IDs never collide
CLEAR_GEM_OFFSET = 0x100
PATH_GEM_OFFSET = 0x200
COLORED_GEM_OFFSET = 0x300

location_name_to_id: dict[str, int] = {
    **{level.crystal_location: BASE_ID + CRYSTAL_OFFSET + level.lid for level in MAIN_LEVELS},
    **{boss.defeat_location: BASE_ID + BOSS_OFFSET + boss.lid for boss in BOSSES},
    **{level.clear_gem_location: BASE_ID + CLEAR_GEM_OFFSET + level.lid for level in MAIN_LEVELS},
    **{level.path_gem_location: BASE_ID + PATH_GEM_OFFSET + level.lid for level in PATH_GEM_LEVELS},
    **{level.colored_gem_location: BASE_ID + COLORED_GEM_OFFSET + level.lid for level in COLORED_GEM_LEVELS},
}

location_name_groups: dict[str, set[str]] = {
    "Crystals": {level.crystal_location for level in MAIN_LEVELS},
    "Bosses": {boss.defeat_location for boss in BOSSES},
    "Clear Gems": {level.clear_gem_location for level in MAIN_LEVELS}
                  | {level.path_gem_location for level in PATH_GEM_LEVELS},
    "Colored Gems": {level.colored_gem_location for level in COLORED_GEM_LEVELS},
    **{
        f"Warp Room {room}": {
            name
            for level in MAIN_LEVELS + BOSSES if level.room == room
            for name in (level.crystal_location, level.defeat_location, level.clear_gem_location,
                         level.path_gem_location,
                         level.colored_gem_location if level.colored_gem else "")
            if name in location_name_to_id
        }
        for room in range(1, 6)
    },
}
