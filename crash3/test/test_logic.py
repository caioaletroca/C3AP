from ..data import MAIN_LEVELS
from .bases import Crash3TestBase


def crystal_items(count: int) -> list[str]:
    return [level.crystal_item for level in MAIN_LEVELS[:count]]


class TestRoomGates(Crash3TestBase):
    options = {"gem_checks": True, "relic_checks": True}

    def test_room_one_is_open(self) -> None:
        self.assertTrue(self.can_reach_location("Toad Village - Crystal"))
        self.assertTrue(self.can_reach_location("Toad Village - Exit"))
        self.assertFalse(self.can_reach_location("Tiny Tiger - Defeated"))

    def test_any_five_crystals_open_tiny_and_room_two(self) -> None:
        self.collect_by_name([level.crystal_item for level in MAIN_LEVELS[-5:]])
        self.assertTrue(self.can_reach_location("Tiny Tiger - Defeated"))
        self.assertTrue(self.can_reach_location("Gee Wiz - Crystal"), "levels and crystals need no powers")
        self.assertFalse(self.can_reach_location("Dingodile - Defeated"))

    def test_gem_powers_per_level(self) -> None:
        self.collect_by_name(crystal_items(25))
        for level, power in (("High Time", "Double Jump"), ("Dino Might!", "Super Body Slam"),
                             ("Tomb Wader", "Death Tornado Spin"), ("Flaming Passion", "Fruit Bazooka")):
            with self.subTest(level=level):
                self.assertFalse(self.can_reach_location(f"{level} - Clear Gem"), f"needs {power}")
        self.assertTrue(self.can_reach_location("Gee Wiz - Clear Gem"), "warp rooms 1-2: no powers")
        self.assertTrue(self.can_reach_location("Tell No Tales - Clear Gem"), "ride levels: no powers")
        self.collect_by_name("Death Tornado Spin")
        self.assertTrue(self.can_reach_location("Tomb Wader - Clear Gem"))

    def test_box_gems_behind_a_colored_path(self) -> None:
        self.collect_by_name(crystal_items(25) + ["Super Body Slam"])
        self.assertFalse(self.can_reach_location("Tomb Time - Clear Gem"))
        self.assertFalse(self.can_reach_location("Dino Might! - Clear Gem"))
        self.collect_by_name(["Purple Gem", "Yellow Gem"])
        self.assertTrue(self.can_reach_location("Tomb Time - Clear Gem"))
        self.assertTrue(self.can_reach_location("Dino Might! - Clear Gem"))

    def test_future_frenzy_gems_need_pad_29(self) -> None:
        self.collect_by_name(crystal_items(25) + ["Death Tornado Spin"])
        self.assertFalse(self.can_reach_location("Future Frenzy - Clear Gem"))
        self.collect_by_name([level.relic_item for level in MAIN_LEVELS[:20]])
        self.assertTrue(self.can_reach_location("Future Frenzy - Clear Gem"))
        self.assertTrue(self.can_reach_location("Future Frenzy - Secret Entrance Clear Gem"))

    def test_gem_path_needs_its_color(self) -> None:
        self.assertFalse(self.can_reach_location("Bone Yard - Gem Path Clear Gem"))
        self.collect_by_name("Red Gem")
        self.assertFalse(self.can_reach_location("Bone Yard - Gem Path Clear Gem"), "the red path needs Double Jump")
        self.collect_by_name("Double Jump")
        self.assertTrue(self.can_reach_location("Bone Yard - Gem Path Clear Gem"))

    def test_bug_lite_path_needs_every_color(self) -> None:
        self.collect_all_but(["Yellow Gem"])
        self.assertFalse(self.can_reach_location("Bug Lite - Gem Path Clear Gem"))
        self.collect_by_name("Yellow Gem")
        self.assertTrue(self.can_reach_location("Bug Lite - Gem Path Clear Gem"))

    def test_relics_need_crash_dash_except_rides(self) -> None:
        self.assertFalse(self.can_reach_location("Toad Village - Sapphire Relic"))
        self.assertTrue(self.can_reach_location("Orient Express - Gold Relic"), "a ride level")
        self.collect_by_name("Crash Dash")
        self.assertTrue(self.can_reach_location("Toad Village - Sapphire Relic"))

    def test_secret_levels_follow_the_relic_count(self) -> None:
        relics = [level.relic_item for level in MAIN_LEVELS]
        self.assertFalse(self.can_reach_location("Ski Crazed - Exit"))
        self.collect_by_name(relics[:5])
        self.assertTrue(self.can_reach_location("Ski Crazed - Exit"))
        self.assertFalse(self.can_reach_location("Hang 'em High - Yellow Gem"))
        self.assertFalse(self.can_reach_location("Area 51? - Exit"))
        self.collect_by_name(crystal_items(5) + ["Super Body Slam"] + relics[5:10])
        self.assertTrue(self.can_reach_location("Hang 'em High - Yellow Gem"))
        self.collect_by_name(relics[10:15])
        self.assertTrue(self.can_reach_location("Area 51? - Exit"))
        self.assertFalse(self.can_reach_location("Rings of Power - Exit"))
        self.collect_by_name(relics[15:25])
        self.assertTrue(self.can_reach_location("Rings of Power - Race Clear Gem"))

    def test_victory_needs_25_crystals(self) -> None:
        self.collect_all_but([*crystal_items(1), "Victory"])
        self.assertBeatable(False)
        self.collect_by_name(crystal_items(1))
        self.assertBeatable(True)


class TestGemGoal(Crash3TestBase):
    options = {"goal": "cortex_all_gems", "gem_checks": False}

    def test_gem_checks_forced_on(self) -> None:
        self.assertTrue(self.world.options.gem_checks)

    def test_cortex_needs_every_gem(self) -> None:
        self.collect_all_but(["Toad Village Clear Gem", "Victory"])
        self.assertBeatable(False)
        self.collect_by_name("Toad Village Clear Gem")
        self.assertBeatable(True)


class TestRelicGoal(Crash3TestBase):
    options = {"goal": "cortex_all_relics", "relic_checks": False}

    def test_cortex_needs_every_relic(self) -> None:
        self.assertTrue(self.world.options.relic_checks)
        self.collect_all_but(["Rings of Power Relic", "Victory"])
        self.assertBeatable(False)
