import unittest
from collections import Counter
from dataclasses import replace

from .. import ram
from ..data import LEVEL_BY_NAME, MAIN_LEVELS
from ..locations import location_name_to_id
from ..watcher import SlotInfo, Watcher

HUB = ram.Snapshot(level=ram.LID_WARP_ROOM, gamestate=ram.GAMESTATE_PLAYING, respawn_count=0, lives=4 * ram.UNIT, health=0, gems=0,
                   crystals=0, powers=0, scene_id=ram.LID_WARP_ROOM, scene_request=ram.NO_SCENE)
VANILLA = tuple(level.lid for level in MAIN_LEVELS)


def lid(name: str) -> int:
    return LEVEL_BY_NAME[name].lid


def loc(name: str) -> int:
    return location_name_to_id[name]


def crystal_bit(name: str) -> int:
    return 1 << ram.CRYSTAL_BIT_BY_LID[lid(name)]


def make_watcher(level_order: tuple[int, ...] = VANILLA, gem_checks: bool = True) -> Watcher:
    return Watcher(SlotInfo(level_order=level_order, gem_checks=gem_checks))


class WatcherTest(unittest.TestCase):
    def setUp(self) -> None:
        self.watcher = make_watcher()
        self.received: Counter[str] = Counter()
        self.checked: set[int] = set()

    def step(self, snap: ram.Snapshot) -> ram.Snapshot:
        self.actions = self.watcher.step(snap, self.received, self.checked)
        self.checked |= self.actions.locations
        return snap

    def in_level(self, name: str, **kwargs) -> ram.Snapshot:
        return replace(HUB, level=lid(name), scene_id=lid(name), **kwargs)

    def written(self, address: int) -> int | None:
        entry = self.actions.writes.get(address)
        return None if entry is None else entry[0]


class TestCrystals(WatcherTest):
    def test_received_crystals_fill_in_level_order(self) -> None:
        self.received["Crystal"] = 6
        self.step(HUB)
        expected = sum(crystal_bit(level.name) for level in MAIN_LEVELS[:6])
        self.assertEqual(self.written(ram.CRYSTALS), expected)

    def test_crystal_is_masked_then_checked(self) -> None:
        self.received["Crystal"] = 1
        level = self.step(self.in_level("Toad Village", crystals=crystal_bit("Toad Village")))
        self.assertFalse(self.written(ram.CRYSTALS) & crystal_bit("Toad Village"), "held at 0 so the crystal spawns")
        level = self.step(replace(level, crystals=0))
        self.step(replace(level, crystals=crystal_bit("Toad Village")))
        self.assertEqual(self.actions.locations, {loc("Toad Village - Crystal")})
        self.step(replace(level, crystals=crystal_bit("Toad Village")))
        self.assertNotIn(ram.CRYSTALS, self.actions.writes, "after the check it mirrors the item again")

    def test_bit_already_there_on_entry_is_not_a_check(self) -> None:
        self.received["Crystal"] = 1
        self.step(HUB)
        self.step(self.in_level("Toad Village", crystals=crystal_bit("Toad Village")))
        self.assertFalse(self.actions.locations)

    def test_crystal_awarded_back_in_the_warp_room(self) -> None:
        # BizHawk: the game sets the crystal bit ~200 frames after LEVEL is back to the warp room.
        self.step(self.in_level("Toad Village"))
        self.step(HUB)
        self.assertFalse(self.actions.locations)
        self.step(replace(HUB, crystals=crystal_bit("Toad Village")))
        self.assertEqual(self.actions.locations, {loc("Toad Village - Crystal")})

    def test_next_level_ends_the_previous_one(self) -> None:
        self.step(self.in_level("Toad Village"))
        self.step(HUB)
        level = self.step(self.in_level("Under Pressure"))
        self.step(replace(level, crystals=crystal_bit("Toad Village")))
        self.assertFalse(self.actions.locations, "Toad Village is no longer watched")

    def test_masked_level_does_not_cost_a_crystal(self) -> None:
        self.received["Crystal"] = 5
        self.step(self.in_level("Toad Village"))
        self.step(HUB)
        written = self.written(ram.CRYSTALS)
        self.assertEqual(bin(written).count("1"), 5, "the boss button reads the total")
        self.assertFalse(written & crystal_bit("Toad Village"))

    def test_collected_crystal_without_the_item_is_removed(self) -> None:
        self.checked.add(loc("Toad Village - Crystal"))
        self.step(replace(HUB, crystals=crystal_bit("Toad Village")))
        self.assertEqual(self.written(ram.CRYSTALS), 0)


class TestWarpRoomCrystals(WatcherTest):
    """A warp room changed under its built buttons loses them all (BizHawk): reload it or write elsewhere."""

    def test_crossing_a_boss_step_in_the_hub_reloads(self) -> None:
        self.received["Crystal"] = 5
        self.step(HUB)
        self.assertEqual(bin(self.written(ram.CRYSTALS)).count("1"), 5)
        self.assertEqual(self.written(ram.SCENE_REQUEST), ram.LID_WARP_ROOM)
        self.assertTrue(self.actions.reload_hub)

    @unittest.skipIf(ram.HUB_AREA_ROOM_1 is None, "the current warp room is not known yet")
    def test_change_for_another_room_does_not_reload(self) -> None:
        # BizHawk: 10 crystals written in room 1, then walking to room 2 shows its boss button correctly.
        self.received["Crystal"] = 10
        room_1 = replace(HUB, hub_area=(ram.HUB_AREA_ROOM_1 or 0), crystals=sum(crystal_bit(l.name) for l in MAIN_LEVELS[:5]))
        self.step(room_1)
        self.assertEqual(bin(self.written(ram.CRYSTALS)).count("1"), 10)
        self.assertNotIn(ram.SCENE_REQUEST, self.actions.writes)

    def test_change_for_the_room_crash_is_in_reloads(self) -> None:
        self.received["Crystal"] = 10
        room_2 = replace(HUB, hub_area=(ram.HUB_AREA_ROOM_1 or 0) + 1,
                         crystals=sum(crystal_bit(l.name) for l in MAIN_LEVELS[:5]))
        self.step(room_2)
        self.assertTrue(self.actions.reload_hub)

    def test_small_change_in_the_hub_does_not_reload(self) -> None:
        self.received["Crystal"] = 1
        self.step(HUB)
        self.assertIsNotNone(self.written(ram.CRYSTALS))
        self.assertNotIn(ram.SCENE_REQUEST, self.actions.writes)

    def test_nothing_written_while_the_hub_loads(self) -> None:
        self.received["Crystal"] = 5
        self.step(self.in_level("Toad Village"))
        self.received["Crystal"] = 10
        self.step(replace(self.in_level("Toad Village"), scene_id=ram.LID_WARP_ROOM))
        self.assertNotIn(ram.CRYSTALS, self.actions.writes)

    def test_written_freely_in_a_level(self) -> None:
        self.received["Crystal"] = 5
        self.step(self.in_level("Toad Village"))
        self.assertEqual(bin(self.written(ram.CRYSTALS)).count("1"), 5)
        self.assertNotIn(ram.SCENE_REQUEST, self.actions.writes)

    def awarded_in_hub(self) -> ram.Snapshot:
        self.received["Crystal"] = 4
        level = self.step(self.in_level("Toad Village"))
        self.step(replace(level, crystals=self.written(ram.CRYSTALS)))
        hub = self.step(replace(HUB, crystals=self.written(ram.CRYSTALS) or level.crystals))
        hub = replace(hub, crystals=self.watcher.desired(hub, self.received, self.checked)["crystals"])
        self.step(hub)
        awarded = replace(hub, crystals=hub.crystals | crystal_bit("Toad Village"))
        self.step(awarded)
        self.assertEqual(self.actions.locations, {loc("Toad Village - Crystal")})
        return awarded

    def test_own_crystal_arriving_needs_no_reload(self) -> None:
        awarded = self.awarded_in_hub()
        self.step(awarded)
        self.assertNotIn(ram.CRYSTALS, self.actions.writes, "grace: wait for the item")
        self.received["Crystal"] = 5
        self.step(awarded)
        self.assertNotIn(ram.SCENE_REQUEST, self.actions.writes)

    def test_someone_elses_crystal_is_taken_back_with_a_reload(self) -> None:
        awarded = self.awarded_in_hub()
        for _ in range(10):
            self.step(awarded)
            if ram.CRYSTALS in self.actions.writes:
                break
        self.assertEqual(bin(self.written(ram.CRYSTALS)).count("1"), 4)
        self.assertTrue(self.actions.reload_hub)


class TestGems(WatcherTest):
    def test_clear_gem_bit_appearing_is_the_check(self) -> None:
        bit = 1 << ram.CLEAR_GEM_BIT_BY_LID[lid("Under Pressure")]
        level = self.step(self.in_level("Under Pressure"))
        self.step(replace(level, gems=bit))
        self.assertEqual(self.actions.locations, {loc("Under Pressure - Clear Gem")})
        self.assertNotIn(ram.GEMS, self.actions.writes, "clear gem bits are never written")

    def test_clear_gem_awarded_back_in_the_warp_room(self) -> None:
        bit = 1 << ram.CLEAR_GEM_BIT_BY_LID[lid("Toad Village")]
        self.step(self.in_level("Toad Village"))
        self.step(replace(HUB, level=ram.LID_TRANSITION))
        self.step(HUB)
        self.step(replace(HUB, gems=bit))
        self.assertEqual(self.actions.locations, {loc("Toad Village - Clear Gem")})

    def test_gem_path_gem_is_checked(self) -> None:
        # BizHawk: Bone Yard's red path gem set GEMS bit 1 back in the warp room.
        self.step(self.in_level("Bone Yard"))
        self.step(HUB)
        self.step(replace(HUB, gems=1 << 1))
        self.assertEqual(self.actions.locations, {loc("Bone Yard - Gem Path Clear Gem")})

    def test_no_gem_checks(self) -> None:
        self.watcher = make_watcher(gem_checks=False)
        bit = 1 << ram.CLEAR_GEM_BIT_BY_LID[lid("Under Pressure")]
        level = self.step(self.in_level("Under Pressure"))
        self.step(replace(level, gems=bit))
        self.assertFalse(self.actions.locations)

    def test_all_received_colored_gems_are_written(self) -> None:
        for gem in ("Red", "Green", "Purple", "Blue", "Yellow"):
            self.received[f"{gem} Gem"] = 1
        self.step(HUB)
        self.assertEqual(self.written(ram.GEMS), sum(1 << bit for bit in range(58, 63)))

    def test_purple_gem_mirrors_and_is_checked_in_the_warp_room(self) -> None:
        bit = 1 << ram.COLORED_GEM_BITS["Purple"]
        self.received["Purple Gem"] = 1
        self.step(HUB)
        self.assertEqual(self.written(ram.GEMS), bit)
        self.step(self.in_level("High Time", gems=bit))
        self.assertEqual(self.written(ram.GEMS), 0, "held at 0 so the gem can be won")
        # BizHawk: the gem bit lands back in the warp room, after the level.
        self.step(self.in_level("High Time"))
        self.step(HUB)
        self.step(replace(HUB, gems=bit))
        self.assertEqual(self.actions.locations, {loc("High Time - Purple Gem")})


class TestBossesAndGoal(WatcherTest):
    def test_received_power_is_written(self) -> None:
        self.received["Double Jump"] = 1
        self.step(replace(HUB, powers=1 << 5))
        self.assertEqual(self.written(ram.POWERS), (1 << 1) | (1 << 5), "unknown bits are kept")

    def test_boss_beaten_bit_is_the_defeat_check(self) -> None:
        level = self.step(self.in_level("Tiny Tiger"))
        self.step(replace(level, levels_completed=1 << lid("Tiny Tiger")))
        self.assertEqual(self.actions.locations, {loc("Tiny Tiger - Defeated")})
        self.assertNotIn(ram.LEVELS_COMPLETED, self.actions.writes, "the game owns the boss field")

    def test_earned_power_without_the_item_is_removed(self) -> None:
        # The game re-adds earned powers on level load; only the item may grant them.
        self.step(replace(self.in_level("Gee Wiz"), powers=1, levels_completed=1 << lid("Tiny Tiger")))
        self.assertEqual(self.written(ram.POWERS), 0)

    def test_defeat_is_sent_after_a_restart(self) -> None:
        self.step(HUB)
        self.step(replace(HUB, levels_completed=1 << lid("Tiny Tiger")))
        self.assertIn(loc("Tiny Tiger - Defeated"), self.actions.locations)

    def test_cortex_bit_is_the_goal(self) -> None:
        level = self.step(self.in_level("Dr. N. Cortex"))
        self.step(replace(level, levels_completed=1 << lid("Dr. N. Cortex")))
        self.assertTrue(self.actions.goal)


class TestDeathAndFiller(WatcherTest):
    def test_respawn_is_a_death(self) -> None:
        level = self.step(self.in_level("Toad Village"))
        self.step(replace(level, respawn_count=0x100))
        self.assertTrue(self.actions.died)

    def test_new_level_reset_is_not_a_death(self) -> None:
        self.step(self.in_level("Toad Village", respawn_count=0x200))
        self.step(HUB)
        self.assertFalse(self.actions.died)

    def test_filler_only_in_the_hub(self) -> None:
        self.step(self.in_level("Toad Village"))
        self.assertFalse(self.actions.can_apply_filler)
        self.step(HUB)
        self.assertTrue(self.actions.can_apply_filler)

    def test_title_does_nothing(self) -> None:
        self.received["Crystal"] = 5
        self.step(replace(HUB, level=ram.LID_TITLE))
        self.assertFalse(self.actions.writes)


class TestLevelShuffle(WatcherTest):
    def setUp(self) -> None:
        super().setUp()
        order = list(VANILLA)
        order[0], order[1] = order[1], order[0]  # Toad Village's button loads Under Pressure and back
        self.watcher = make_watcher(level_order=tuple(order))

    def test_caught_request_is_swapped(self) -> None:
        self.step(replace(HUB, scene_request=lid("Toad Village")))
        self.assertEqual(self.written(ram.SCENE_REQUEST), lid("Under Pressure"))
        self.assertEqual(self.actions.guards[ram.SCENE_REQUEST][0], lid("Toad Village"))

    def test_missed_request_reloads(self) -> None:
        self.step(HUB)
        self.step(self.in_level("Toad Village"))
        self.assertEqual(self.written(ram.SCENE_REQUEST), lid("Under Pressure"))
        self.step(self.in_level("Under Pressure"))
        self.assertNotIn(ram.SCENE_REQUEST, self.actions.writes, "our own redirect is not redirected again")

    def test_unchanged_buttons_are_left_alone(self) -> None:
        self.step(HUB)
        self.step(self.in_level("Orient Express"))
        self.assertNotIn(ram.SCENE_REQUEST, self.actions.writes)

    def test_vanilla_order_never_redirects(self) -> None:
        self.watcher = make_watcher()
        self.step(replace(HUB, scene_request=lid("Toad Village")))
        self.assertNotIn(ram.SCENE_REQUEST, self.actions.writes)
