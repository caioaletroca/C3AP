from BaseClasses import Item, ItemClassification

from .data import COLORED_GEMS, ITEM_POWERS

GAME_NAME = "Crash Bandicoot 3"
BASE_ID = 7_330_000


class Crash3Item(Item):
    game = GAME_NAME


CRYSTAL = "Crystal"
CLEAR_GEM = "Clear Gem"
VICTORY = "Victory"
NO_LIVES_TRAP = "No Lives Trap"

FILLER_WEIGHTS: dict[str, int] = {
    "Extra Life": 5,
    "Aku Aku Mask": 5,
}

# IDs are permanent once released: never renumber, only append.
item_name_to_id: dict[str, int] = {
    CRYSTAL: BASE_ID + 1,
    **{power.name: BASE_ID + 10 + index for index, power in enumerate(ITEM_POWERS)},
    **{gem.item_name: BASE_ID + 20 + index for index, gem in enumerate(COLORED_GEMS)},
    CLEAR_GEM: BASE_ID + 30,
    **{name: BASE_ID + 40 + index for index, name in enumerate(FILLER_WEIGHTS)},
    NO_LIVES_TRAP: BASE_ID + 50,
}

APPLIED_IN_HUB: tuple[str, ...] = (*FILLER_WEIGHTS, NO_LIVES_TRAP)
"""Items the client writes into the game in the warp room, one at a time, in the order received"""

item_name_groups: dict[str, set[str]] = {
    "Powers": {power.name for power in ITEM_POWERS},
    "Colored Gems": {gem.item_name for gem in COLORED_GEMS},
    "Gems": {gem.item_name for gem in COLORED_GEMS} | {CLEAR_GEM},
    "Filler": set(FILLER_WEIGHTS),
    "Traps": {NO_LIVES_TRAP},
}

DEFAULT_CLASSIFICATION: dict[str, ItemClassification] = {
    CRYSTAL: ItemClassification.progression,
    **{power.name: ItemClassification.progression for power in ITEM_POWERS},
    **{gem.item_name: ItemClassification.progression for gem in COLORED_GEMS},
    CLEAR_GEM: ItemClassification.filler,
    **{name: ItemClassification.filler for name in FILLER_WEIGHTS},
    NO_LIVES_TRAP: ItemClassification.trap,
}
