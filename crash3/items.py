from BaseClasses import Item, ItemClassification

from .data import (
    COLORED_GEMS, GEM_LEVELS, ITEM_POWERS, MAIN_LEVELS, PATH_GEM_LEVELS, RACE_GEM_LEVELS, RELIC_LEVELS,
)

GAME_NAME = "Crash Bandicoot 3"
BASE_ID = 7_330_000


class Crash3Item(Item):
    game = GAME_NAME


VICTORY = "Victory"
NO_LIVES_TRAP = "No Lives Trap"

FILLER_WEIGHTS: dict[str, int] = {
    "Extra Life": 5,
    "Aku Aku Mask": 5,
}

CRYSTAL_ITEMS: tuple[str, ...] = tuple(level.crystal_item for level in MAIN_LEVELS)
CLEAR_GEM_ITEMS: tuple[str, ...] = (
    *(level.clear_gem_item for level in GEM_LEVELS),
    *(level.path_gem_item for level in PATH_GEM_LEVELS),
    *(level.race_gem_item for level in RACE_GEM_LEVELS),
)
RELIC_ITEMS: tuple[str, ...] = tuple(level.relic_item for level in RELIC_LEVELS)

# IDs are permanent once released: never renumber, only append. v1.0 retired 7330001 ("Crystal") and 7330030
# ("Clear Gem"), replaced by one item per level, numbered from its level ID.
CRYSTAL_ITEM_OFFSET = 0x1000
CLEAR_GEM_ITEM_OFFSET = 0x1100
PATH_GEM_ITEM_OFFSET = 0x1200
RELIC_ITEM_OFFSET = 0x1300
RACE_GEM_ITEM_OFFSET = 0x1400

item_name_to_id: dict[str, int] = {
    **{power.name: BASE_ID + 10 + index for index, power in enumerate(ITEM_POWERS)},  # Crash Dash = 14
    **{gem.item_name: BASE_ID + 20 + index for index, gem in enumerate(COLORED_GEMS)},
    **{name: BASE_ID + 40 + index for index, name in enumerate(FILLER_WEIGHTS)},
    NO_LIVES_TRAP: BASE_ID + 50,
    **{level.crystal_item: BASE_ID + CRYSTAL_ITEM_OFFSET + level.lid for level in MAIN_LEVELS},
    **{level.clear_gem_item: BASE_ID + CLEAR_GEM_ITEM_OFFSET + level.lid for level in GEM_LEVELS},
    **{level.path_gem_item: BASE_ID + PATH_GEM_ITEM_OFFSET + level.lid for level in PATH_GEM_LEVELS},
    **{level.relic_item: BASE_ID + RELIC_ITEM_OFFSET + level.lid for level in RELIC_LEVELS},
    **{level.race_gem_item: BASE_ID + RACE_GEM_ITEM_OFFSET + level.lid for level in RACE_GEM_LEVELS},
}

APPLIED_IN_HUB: tuple[str, ...] = (*FILLER_WEIGHTS, NO_LIVES_TRAP)
"""Items the client writes into the game in the warp room, one at a time, in the order received"""

CRYSTALS_GROUP = "Crystals"
RELICS_GROUP = "Relics"
GEMS_GROUP = "Gems"

item_name_groups: dict[str, set[str]] = {
    CRYSTALS_GROUP: set(CRYSTAL_ITEMS),
    RELICS_GROUP: set(RELIC_ITEMS),
    "Powers": {power.name for power in ITEM_POWERS},
    "Colored Gems": {gem.item_name for gem in COLORED_GEMS},
    "Clear Gems": set(CLEAR_GEM_ITEMS),
    GEMS_GROUP: {gem.item_name for gem in COLORED_GEMS} | set(CLEAR_GEM_ITEMS),
    "Filler": set(FILLER_WEIGHTS),
    "Traps": {NO_LIVES_TRAP},
}

DEFAULT_CLASSIFICATION: dict[str, ItemClassification] = {
    **{name: ItemClassification.progression for name in CRYSTAL_ITEMS},
    **{power.name: ItemClassification.progression for power in ITEM_POWERS},
    **{gem.item_name: ItemClassification.progression for gem in COLORED_GEMS},
    **{name: ItemClassification.filler for name in CLEAR_GEM_ITEMS},   # progression with a gem goal
    **{name: ItemClassification.progression for name in RELIC_ITEMS},  # they open the secret levels
    **{name: ItemClassification.filler for name in FILLER_WEIGHTS},
    NO_LIVES_TRAP: ItemClassification.trap,
}
