from .bases import Crash3TestBase


class TestRoomGates(Crash3TestBase):
    options = {"gem_checks": True}

    def test_room_one_is_open(self) -> None:
        self.assertTrue(self.can_reach_location("Toad Village - Crystal"))
        self.assertFalse(self.can_reach_location("Tiny Tiger - Defeated"))

    def test_tiny_needs_five_crystals(self) -> None:
        self.collect(self.get_items_by_name("Crystal")[:5])
        self.assertTrue(self.can_reach_location("Tiny Tiger - Defeated"))
        self.assertFalse(self.can_reach_location("Gee Wiz - Crystal"), "room 2 also needs Tiny's power")

    def test_room_two_needs_crystals_and_power(self) -> None:
        self.collect_by_name("Super Body Slam")
        self.assertFalse(self.can_reach_location("Gee Wiz - Crystal"))
        self.collect(self.get_items_by_name("Crystal")[:5])
        self.assertTrue(self.can_reach_location("Gee Wiz - Crystal"))

    def test_gem_path_needs_its_color(self) -> None:
        self.assertFalse(self.can_reach_location("Bone Yard - Gem Path Clear Gem"))
        self.collect_by_name("Red Gem")
        self.assertTrue(self.can_reach_location("Bone Yard - Gem Path Clear Gem"))

    def test_bug_lite_path_needs_every_color(self) -> None:
        self.collect_all_but(["Yellow Gem"])
        self.assertFalse(self.can_reach_location("Bug Lite - Gem Path Clear Gem"))
        self.collect_by_name("Yellow Gem")
        self.assertTrue(self.can_reach_location("Bug Lite - Gem Path Clear Gem"))

    def test_victory_needs_everything_to_cortex(self) -> None:
        self.collect_all_but(["Crystal", "Victory"])
        self.assertBeatable(False)
        self.collect(self.get_items_by_name("Crystal"))
        self.assertBeatable(True)
