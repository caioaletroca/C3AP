"""Level-order shuffle for the warp room buttons.

Levels are shuffled among the five buttons of their own warp room; bosses keep their buttons. Keeping each level in
its room keeps the logic honest without knowing which levels truly need which powers: a level still opens with the
same crystals and powers as in vanilla, only behind a different button.
"""
from random import Random

from .data import LEVELS_PER_ROOM, MAIN_LEVELS, WARP_ROOMS, Level


def vanilla_order() -> list[Level]:
    """The level on each button, in button order (index 0 = level 1's button)."""
    return list(MAIN_LEVELS)


def shuffle_order(random: Random) -> list[Level]:
    order: list[Level] = []
    for room in range(1, WARP_ROOMS + 1):
        levels = [level for level in MAIN_LEVELS if level.room == room]
        random.shuffle(levels)
        order += levels
    assert len(order) == WARP_ROOMS * LEVELS_PER_ROOM
    return order
