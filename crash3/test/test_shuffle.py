import unittest
from random import Random

from ..data import MAIN_LEVELS
from ..shuffle import shuffle_order, vanilla_order


class TestShuffle(unittest.TestCase):
    def test_vanilla(self) -> None:
        self.assertEqual(vanilla_order(), list(MAIN_LEVELS))

    def test_shuffle_is_a_permutation(self) -> None:
        for seed in range(50):
            order = shuffle_order(Random(seed))
            self.assertCountEqual(order, MAIN_LEVELS)
            for button, level in zip(MAIN_LEVELS, order):
                self.assertEqual(button.room, level.room, "levels stay in their warp room")
