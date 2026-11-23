import unittest

from BaseClasses import MultiWorld
from Fill import distribute_items_restrictive
from worlds.AutoWorld import call_all
from test.general import setup_solo_multiworld

from ..world import Crash3World

SEEDS = range(30)


def generate(options: dict[str, object], seed: int) -> MultiWorld:
    multiworld = setup_solo_multiworld(Crash3World, (), seed=seed)
    for name, value in options.items():
        option = getattr(multiworld.worlds[1].options, name)
        setattr(multiworld.worlds[1].options, name, type(option).from_any(value))
    for step in ("generate_early", "create_regions", "create_items", "set_rules", "connect_entrances",
                 "generate_basic", "pre_fill"):
        call_all(multiworld, step)
    distribute_items_restrictive(multiworld)
    call_all(multiworld, "post_fill")
    return multiworld


class TestManySeeds(unittest.TestCase):
    """The tightest settings for the first sphere: few checks, and levels from any room behind room 1's buttons"""

    def check(self, options: dict[str, object]) -> None:
        for seed in SEEDS:
            with self.subTest(seed=seed):
                multiworld = generate(options, seed)
                self.assertTrue(multiworld.can_beat_game())

    def test_casual_all_rooms(self) -> None:
        self.check({"gem_checks": False, "relic_checks": False, "level_shuffle": "all_rooms"})

    def test_full_all_rooms(self) -> None:
        self.check({"goal": "cortex_105", "platinum_relics": True, "level_shuffle": "all_rooms"})
