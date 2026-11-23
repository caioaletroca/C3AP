"""Level-order shuffle for the warp room buttons.

Bosses and secret levels keep their places. Logic is per level (see world.py), so a level needs the same items behind
any button: only the crystal total that opens its warp room changes.
"""
from random import Random

from .data import LEVELS_PER_ROOM, MAIN_LEVELS, WARP_ROOMS, Level


def vanilla_order() -> list[Level]:
    """The level on each button, in button order (index 0 = level 1's button)."""
    return list(MAIN_LEVELS)


def shuffle_within_rooms(random: Random) -> list[Level]:
    order: list[Level] = []
    for room in range(1, WARP_ROOMS + 1):
        levels = [level for level in MAIN_LEVELS if level.room == room]
        random.shuffle(levels)
        order += levels
    assert len(order) == WARP_ROOMS * LEVELS_PER_ROOM
    return order


def shuffle_all_rooms(random: Random) -> list[Level]:
    order = list(MAIN_LEVELS)
    random.shuffle(order)
    return order
