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


def make_watcher(level_order: tuple[int, ...] = VANILLA, gem_checks: bool = True, relic_checks: bool = True,
                 goal_items: tuple[str, ...] = ()) -> Watcher:
    locations = frozenset(loc_id for name, loc_id in location_name_to_id.items()
                          if (gem_checks or "Gem" not in name) and (relic_checks or "Relic" not in name))
    return Watcher(SlotInfo(level_order=level_order, locations=locations, gem_checks=gem_checks,
                            relic_checks=relic_checks, goal_items=goal_items))


class WatcherTest(unittest.TestCase):
    def setUp(self) -> None:
        self.watcher = make_watcher()
        self.received: Counter[str] = Counter()
        self.checked: set[int] = set()

    def give_crystals(self, count: int) -> None:
        """Crystal items of the last ``count`` main levels (Toad Village's comes last)"""
        for level in MAIN_LEVELS[::-1][:count]:
            self.received[level.crystal_item] = 1

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
    def test_each_crystal_item_turns_on_its_own_level(self) -> None:
        self.received["Gee Wiz Crystal"] = 1
        self.received["Bug Lite Crystal"] = 1
        self.step(HUB)
        self.assertEqual(self.written(ram.CRYSTALS), crystal_bit("Gee Wiz") | crystal_bit("Bug Lite"))

    def test_crystal_is_masked_then_checked(self) -> None:
        self.received["Toad Village Crystal"] = 1
        level = self.step(self.in_level("Toad Village", crystals=crystal_bit("Toad Village")))
        self.assertFalse(self.written(ram.CRYSTALS) & crystal_bit("Toad Village"), "held at 0 so the crystal spawns")
        level = self.step(replace(level, crystals=0))
        self.step(replace(level, crystals=crystal_bit("Toad Village")))
        self.assertEqual(self.actions.locations, {loc("Toad Village - Crystal")})
        self.step(replace(level, crystals=crystal_bit("Toad Village")))
        self.assertNotIn(ram.CRYSTALS, self.actions.writes, "after the check it mirrors the item again")

    def test_bit_already_there_on_entry_is_not_a_check(self) -> None:
        self.received["Toad Village Crystal"] = 1
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

    def test_masked_level_is_one_lower_until_checked(self) -> None:
        for level in MAIN_LEVELS[:5]:
            self.received[level.crystal_item] = 1
        self.step(self.in_level("Toad Village"))
        self.step(HUB)
        written = self.written(ram.CRYSTALS)
        self.assertEqual(bin(written).count("1"), 4, "accepted: the held level's own crystal is missing for a while")
        self.assertFalse(written & crystal_bit("Toad Village"))

    def test_collected_crystal_without_the_item_is_removed(self) -> None:
        self.checked.add(loc("Toad Village - Crystal"))
        self.step(replace(HUB, crystals=crystal_bit("Toad Village")))
        self.assertEqual(self.written(ram.CRYSTALS), 0)


class TestWarpRoomCrystals(WatcherTest):
    """A warp room changed under its built buttons loses them all (BizHawk): reload it or write elsewhere."""

    def test_crossing_a_boss_step_in_the_hub_reloads(self) -> None:
        self.give_crystals(5)
        self.step(HUB)
        self.assertEqual(bin(self.written(ram.CRYSTALS)).count("1"), 5)
        self.assertEqual(self.written(ram.SCENE_REQUEST), ram.LID_WARP_ROOM)
        self.assertTrue(self.actions.reload_hub)

    @unittest.skipIf(ram.HUB_AREA_ROOM_1 is None, "the current warp room is not known yet")
    def test_change_for_another_room_does_not_reload(self) -> None:
        # BizHawk: 10 crystals written in room 1, then walking to room 2 shows its boss button correctly.
        self.give_crystals(10)
        room_1 = replace(HUB, hub_area=(ram.HUB_AREA_ROOM_1 or 0), crystals=sum(crystal_bit(l.name) for l in MAIN_LEVELS[:5]))
        self.step(room_1)
        self.assertEqual(bin(self.written(ram.CRYSTALS)).count("1"), 10)
        self.assertNotIn(ram.SCENE_REQUEST, self.actions.writes)

    def test_change_for_the_room_crash_is_in_reloads(self) -> None:
        self.give_crystals(10)
        room_2 = replace(HUB, hub_area=(ram.HUB_AREA_ROOM_1 or 0) + 1,
                         crystals=sum(crystal_bit(l.name) for l in MAIN_LEVELS[:5]))
        self.step(room_2)
        self.assertTrue(self.actions.reload_hub)

    def test_small_change_in_the_hub_does_not_reload(self) -> None:
        self.give_crystals(1)
        self.step(HUB)
        self.assertIsNotNone(self.written(ram.CRYSTALS))
        self.assertNotIn(ram.SCENE_REQUEST, self.actions.writes)

    def test_nothing_written_while_the_hub_loads(self) -> None:
        self.give_crystals(5)
        self.step(self.in_level("Toad Village"))
        self.give_crystals(10)
        self.step(replace(self.in_level("Toad Village"), scene_id=ram.LID_WARP_ROOM))
        self.assertNotIn(ram.CRYSTALS, self.actions.writes)

    def test_written_freely_in_a_level(self) -> None:
        self.give_crystals(5)
        self.step(self.in_level("Toad Village"))
        self.assertEqual(bin(self.written(ram.CRYSTALS)).count("1"), 5)
        self.assertNotIn(ram.SCENE_REQUEST, self.actions.writes)

    def awarded_in_hub(self) -> ram.Snapshot:
        self.give_crystals(4)
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
        self.received["Toad Village Crystal"] = 1
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
        self.step(replace(level, gems=bit))
        self.assertEqual(self.written(ram.GEMS), 0, "taken back: the bit mirrors the level's Clear Gem item")

    def test_clear_gem_item_turns_on_its_level(self) -> None:
        self.received["Gee Wiz Clear Gem"] = 1
        self.received["Area 51? Clear Gem"] = 1
        self.step(HUB)
        self.assertEqual(self.written(ram.GEMS), (1 << lid("Gee Wiz")) | (1 << lid("Area 51?")))

    def test_clear_gem_is_held_at_zero_in_its_level(self) -> None:
        self.received["Toad Village Clear Gem"] = 1
        self.step(self.in_level("Toad Village", gems=1 << lid("Toad Village")))
        self.assertEqual(self.written(ram.GEMS), 0)

    def test_unknown_gem_bit_is_learned(self) -> None:
        level = self.step(self.in_level("Sphynxinator"))
        self.step(replace(level, gems=1 << 50))
        self.assertEqual(self.actions.locations, {loc("Sphynxinator - Gem Path Clear Gem")})
        self.assertEqual(self.actions.learned, [("Sphynxinator - Gem Path Clear Gem", 50)])

    def test_known_gem_bit_is_not_learned(self) -> None:
        level = self.step(self.in_level("Sphynxinator"))
        self.step(replace(level, gems=1 << lid("Sphynxinator")))
        self.assertEqual(self.actions.locations, {loc("Sphynxinator - Clear Gem")})
        self.assertFalse(self.actions.learned)

    def test_race_gem_is_learned_in_a_secret_level(self) -> None:
        level = self.step(self.in_level("Area 51?"))
        self.step(replace(level, gems=1 << 40))
        self.assertEqual(self.actions.locations, {loc("Area 51? - Race Clear Gem")})

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

    def test_goal_waits_for_the_goal_items(self) -> None:
        self.watcher = make_watcher(goal_items=("Red Gem", "Toad Village Relic"))
        beaten = replace(HUB, levels_completed=1 << lid("Dr. N. Cortex"))
        self.step(HUB)
        self.received["Red Gem"] = 1
        self.step(beaten)
        self.assertFalse(self.actions.goal)
        self.received["Toad Village Relic"] = 1
        self.step(beaten)
        self.assertTrue(self.actions.goal)

    def test_crash_dash_is_an_item(self) -> None:
        self.step(replace(HUB, powers=1 << 4))
        self.assertEqual(self.written(ram.POWERS), 0)
        self.received["Crash Dash"] = 1
        self.step(HUB)
        self.assertEqual(self.written(ram.POWERS), 1 << 4)


class TestExits(WatcherTest):
    def test_level_completed_bit_is_the_exit_check(self) -> None:
        self.step(self.in_level("Toad Village"))
        self.step(replace(HUB, levels_completed=1 << lid("Toad Village")))
        self.assertEqual(self.actions.locations, {loc("Toad Village - Exit")})

    def test_level_ids_past_31_are_read(self) -> None:
        self.step(HUB)
        self.step(replace(HUB, levels_completed=1 << lid("Bug Lite")))
        self.assertEqual(self.actions.locations, {loc("Bug Lite - Exit")})

    def test_secret_level_exit(self) -> None:
        self.step(HUB)
        self.step(replace(HUB, levels_completed=1 << lid("Ski Crazed")))
        self.assertEqual(self.actions.locations, {loc("Ski Crazed - Exit")})


class TestRelics(WatcherTest):
    def run_trial(self, name: str, sapphire: bool, gold: bool) -> None:
        bit = 1 << lid(name)
        self.step(self.in_level(name))
        self.step(HUB)
        self.step(replace(HUB, sapphires=bit if sapphire else 0, golds=bit if gold else 0))

    def test_sapphire(self) -> None:
        self.run_trial("Toad Village", sapphire=True, gold=False)
        self.assertEqual(self.actions.locations, {loc("Toad Village - Sapphire Relic")})

    def test_gold_sends_sapphire_too(self) -> None:
        self.run_trial("Toad Village", sapphire=False, gold=True)
        self.assertEqual(self.actions.locations,
                         {loc("Toad Village - Sapphire Relic"), loc("Toad Village - Gold Relic")})

    def test_platinum_sends_every_tier(self) -> None:
        self.run_trial("Orient Express", sapphire=True, gold=True)
        self.assertEqual(self.actions.locations, {loc(f"Orient Express - {tier} Relic")
                                                  for tier in ("Sapphire", "Gold", "Platinum")})

    def test_relic_item_is_a_sapphire_bit(self) -> None:
        self.received["Gee Wiz Relic"] = 1
        self.received["Ski Crazed Relic"] = 1
        self.step(replace(HUB, golds=1 << lid("Under Pressure")))
        self.assertEqual(self.written(ram.SAPPHIRE_RELICS), (1 << lid("Gee Wiz")) | (1 << lid("Ski Crazed")))
        self.assertEqual(self.written(ram.GOLD_RELICS), 0, "gold bits are only the game's, during a trial")

    def test_level_relic_bits_are_held_at_zero(self) -> None:
        self.received["Toad Village Relic"] = 1
        self.step(self.in_level("Toad Village", sapphires=1 << lid("Toad Village")))
        self.assertEqual(self.written(ram.SAPPHIRE_RELICS), 0)

    def test_held_until_every_open_tier_is_checked(self) -> None:
        self.received["Toad Village Relic"] = 1
        bit = 1 << lid("Toad Village")
        self.checked.add(loc("Toad Village - Sapphire Relic"))
        self.step(self.in_level("Toad Village", sapphires=bit))
        self.assertEqual(self.written(ram.SAPPHIRE_RELICS), 0, "gold is still open")
        self.checked |= {loc("Toad Village - Gold Relic"), loc("Toad Village - Platinum Relic")}
        self.step(self.in_level("Toad Village", sapphires=bit))
        self.assertNotIn(ram.SAPPHIRE_RELICS, self.actions.writes, "all tiers done: mirrors the item")

    def test_no_relic_checks_leaves_relics_alone(self) -> None:
        self.watcher = make_watcher(relic_checks=False)
        self.received["Gee Wiz Relic"] = 1
        self.step(replace(HUB, sapphires=1 << lid("Toad Village")))
        self.assertNotIn(ram.SAPPHIRE_RELICS, self.actions.writes)


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
        self.give_crystals(5)
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

    def test_own_request_is_not_swapped_again(self) -> None:
        self.step(replace(HUB, scene_request=lid("Toad Village")))
        self.step(replace(HUB, scene_request=lid("Under Pressure")))  # our own write, still in SCENE_REQUEST
        self.assertNotIn(ram.SCENE_REQUEST, self.actions.writes, "Under Pressure's button is shuffled too")

    def test_request_after_intro_cutscene_is_swapped(self) -> None:
        # First visit: warp room -> scene 3A (intro) -> the level's request comes from the cutscene (BizHawk, round 4)
        cutscene = replace(HUB, level=ram.LID_TRANSITION, scene_id=ram.LID_TRANSITION)
        self.step(HUB)
        self.step(cutscene)
        self.step(replace(cutscene, scene_request=lid("Toad Village")))
        self.assertEqual(self.written(ram.SCENE_REQUEST), lid("Under Pressure"))

    def test_missed_request_reloads(self) -> None:
        self.step(HUB)
        self.step(self.in_level("Toad Village"))
        self.assertEqual(self.written(ram.SCENE_REQUEST), lid("Under Pressure"))
        self.step(self.in_level("Under Pressure"))
        self.assertNotIn(ram.SCENE_REQUEST, self.actions.writes, "our own redirect is not redirected again")

    def test_normal_finish_returns_to_the_button(self) -> None:
        # Toad Village's button loads Under Pressure: after a normal finish the game sets LAST_LEVEL to Under Pressure,
        # and the warp room would spawn Crash at Under Pressure's own button.
        level = self.step(self.in_level("Under Pressure", last_level=lid("Under Pressure")))
        self.assertNotIn(ram.LAST_LEVEL, self.actions.writes, "not while the level is played")
        self.step(replace(level, gamestate=ram.GAMESTATE_LEVEL_DONE))
        self.assertEqual(self.written(ram.LAST_LEVEL), lid("Toad Village") << 8)

    def test_return_is_rewritten_only_once(self) -> None:
        # Under Pressure's own button is shuffled too (it loads Toad Village): never rewrite again from there.
        level = self.step(self.in_level("Under Pressure", last_level=lid("Under Pressure")))
        self.step(replace(level, gamestate=ram.GAMESTATE_LEVEL_DONE, last_level=lid("Toad Village")))
        self.assertNotIn(ram.LAST_LEVEL, self.actions.writes)
        self.step(replace(HUB, last_level=lid("Toad Village")))
        self.assertNotIn(ram.LAST_LEVEL, self.actions.writes)

    def test_button_bit_is_the_shuffled_levels_exit(self) -> None:
        # The game sets the bit of LAST_LEVEL, now the button (Toad Village's), after finishing Under Pressure.
        self.step(HUB)
        self.step(replace(HUB, levels_completed=1 << lid("Toad Village")))
        self.assertEqual(self.actions.locations, {loc("Under Pressure - Exit")})

    def test_unshuffled_last_level_is_left_alone(self) -> None:
        self.step(replace(HUB, last_level=lid("Orient Express")))
        self.assertNotIn(ram.LAST_LEVEL, self.actions.writes)

    def test_unchanged_buttons_are_left_alone(self) -> None:
        self.step(HUB)
        self.step(self.in_level("Orient Express"))
        self.assertNotIn(ram.SCENE_REQUEST, self.actions.writes)

    def test_vanilla_order_never_redirects(self) -> None:
        self.watcher = make_watcher()
        self.step(replace(HUB, scene_request=lid("Toad Village")))
        self.assertNotIn(ram.SCENE_REQUEST, self.actions.writes)
