from .bases import Crash3TestBase


def location_names(test: Crash3TestBase) -> set[str]:
    return {loc.name for loc in test.multiworld.get_locations(test.player) if loc.address is not None}


class TestDefault(Crash3TestBase):
    options = {}


class TestCasual(Crash3TestBase):
    options = {"gem_checks": False, "relic_checks": False}

    def test_only_crystals_exits_and_bosses(self) -> None:
        names = location_names(self)
        self.assertFalse(any("Gem" in name or "Relic" in name for name in names))
        self.assertEqual(len(names), 25 + 25 + 4)
        self.assertFalse(self.get_items_by_name("Red Gem"))
        self.assertFalse(self.get_items_by_name("Toad Village Relic"))

    def test_powers_out_of_logic(self) -> None:
        self.assertFalse(self.get_item_by_name("Double Jump").advancement)
        self.assertFalse(self.get_item_by_name("Crash Dash").advancement)


class TestNoRelics(Crash3TestBase):
    options = {"gem_checks": True, "relic_checks": False}

    def test_gems_behind_the_secret_room_are_left_out(self) -> None:
        names = location_names(self)
        self.assertNotIn("Hang 'em High - Yellow Gem", names)
        self.assertNotIn("Future Frenzy - Clear Gem", names)
        self.assertIn("Hang 'em High - Clear Gem", names)
        self.assertFalse(any(name.startswith("Ski Crazed") for name in names))


class TestShuffleWithinRooms(Crash3TestBase):
    options = {"level_shuffle": "within_rooms"}


class TestShuffleAllRooms(Crash3TestBase):
    options = {"level_shuffle": "all_rooms"}


class TestOldShuffleTrue(Crash3TestBase):
    options = {"level_shuffle": "true"}

    def test_true_means_within_rooms(self) -> None:
        self.assertEqual(self.world.options.level_shuffle.value, 1)


class TestPlatinum(Crash3TestBase):
    options = {"platinum_relics": True}

    def test_platinum_locations(self) -> None:
        self.assertIn("Toad Village - Platinum Relic", location_names(self))


class Test105(Crash3TestBase):
    options = {"goal": "cortex_105", "platinum_relics": True, "level_shuffle": "all_rooms"}


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
        # 25 crystals + 28 exits + 4 bosses + 36 clear gems + 5 colored gems + 28 * 2 relics
        self.assertEqual(len(locations), 25 + 28 + 4 + 36 + 5 + 56)
