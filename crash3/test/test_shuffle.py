import unittest
from random import Random

from ..data import MAIN_LEVELS
from ..shuffle import shuffle_all_rooms, shuffle_within_rooms, vanilla_order


class TestShuffle(unittest.TestCase):
    def test_vanilla(self) -> None:
        self.assertEqual(vanilla_order(), list(MAIN_LEVELS))

    def test_within_rooms(self) -> None:
        for seed in range(50):
            order = shuffle_within_rooms(Random(seed))
            self.assertCountEqual(order, MAIN_LEVELS)
            for button, level in zip(MAIN_LEVELS, order):
                self.assertEqual(button.room, level.room, "levels stay in their warp room")

    def test_all_rooms(self) -> None:
        moved = False
        for seed in range(50):
            order = shuffle_all_rooms(Random(seed))
            self.assertCountEqual(order, MAIN_LEVELS)
            moved |= any(button.room != level.room for button, level in zip(MAIN_LEVELS, order))
        self.assertTrue(moved)
