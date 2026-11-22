from .bases import Crash3TestBase


class TestDefault(Crash3TestBase):
    options = {}


class TestNoGems(Crash3TestBase):
    options = {"gem_checks": False}

    def test_no_gem_locations_or_items(self) -> None:
        locations = {loc.name for loc in self.multiworld.get_locations(self.player)}
        self.assertFalse(any("Gem" in name for name in locations))
        self.assertFalse(self.get_items_by_name("Red Gem"))

    def test_pool_is_exactly_crystals_and_powers(self) -> None:
        self.assertEqual(len(self.get_items_by_name("Crystal")), 25)
        self.assertEqual(len(self.get_items_by_name("Double Jump")), 1)
        self.assertFalse(self.get_items_by_name("Crash Dash"), "Cortex keeps handing out Crash Dash")

    def test_powers_out_of_logic(self) -> None:
        self.collect(self.get_items_by_name("Crystal")[:5])
        self.assertTrue(self.can_reach_location("Gee Wiz - Crystal"))
        self.assertFalse(self.get_item_by_name("Double Jump").advancement)


class TestShuffle(Crash3TestBase):
    options = {"level_shuffle": True}


class TestTraps(Crash3TestBase):
    options = {"trap_chance": 100}

    def test_all_filler_is_traps(self) -> None:
        self.assertTrue(self.get_items_by_name("No Lives Trap"))
        self.assertFalse(self.get_items_by_name("Extra Life"))


class TestPoolSize(Crash3TestBase):
    def test_item_count_matches_locations(self) -> None:
        locations = [loc for loc in self.multiworld.get_locations(self.player) if loc.address is not None]
        items = [item for item in self.multiworld.itempool if item.player == self.player]
        self.assertEqual(len(locations), len(items))
        # 25 crystals, 4 bosses, 25 clear gems, 6 gem-path gems, 4 colored gems
        self.assertEqual(len(locations), 64)
        self.assertFalse(self.get_items_by_name("No Lives Trap"))
