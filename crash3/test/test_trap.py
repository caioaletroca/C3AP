import unittest
from dataclasses import replace

from .. import ram
from ..trap import TrapState, advance, spring
from .test_watcher import HUB, lid

LIVES = 7 * ram.UNIT
ON_MAP = replace(HUB, lives=LIVES)
IN_LEVEL = replace(HUB, level=lid("Toad Village"), lives=0)


class TestNoLivesTrap(unittest.TestCase):
    def test_spring_saves_lives_and_zeroes_them(self) -> None:
        state, lives = spring(None, ON_MAP)
        self.assertEqual((state, lives), (TrapState(LIVES), 0))

    def test_second_trap_before_the_level_is_used_up(self) -> None:
        state, lives = spring(TrapState(LIVES), replace(ON_MAP, lives=0))
        self.assertEqual((state, lives), (TrapState(LIVES), None))

    def test_waits_on_the_map_until_a_level_is_played(self) -> None:
        self.assertEqual(advance(TrapState(LIVES), replace(ON_MAP, lives=0)), (TrapState(LIVES), None))

    def test_one_level_then_lives_come_back(self) -> None:
        state, restore = advance(TrapState(LIVES), IN_LEVEL)
        self.assertEqual((state, restore), (TrapState(LIVES, played=True), None))
        state, restore = advance(state, replace(IN_LEVEL, scene_request=ram.LID_WARP_ROOM))
        self.assertIsNone(restore, "not until the map is reached")
        state, restore = advance(state, replace(ON_MAP, lives=2 * ram.UNIT))
        self.assertEqual((state, restore), (None, LIVES + 2 * ram.UNIT), "lives picked up in the level are kept")

    def test_game_over_ends_the_trap(self) -> None:
        state, _ = advance(TrapState(LIVES), IN_LEVEL)
        self.assertEqual(advance(state, replace(IN_LEVEL, gamestate=ram.GAMESTATE_GAME_OVER)), (None, None))

    def test_restore_is_capped(self) -> None:
        _, restore = advance(TrapState(90 * ram.UNIT, played=True), replace(ON_MAP, lives=20 * ram.UNIT))
        self.assertEqual(restore, ram.MAX_LIVES)

    def test_state_round_trips_through_data_storage(self) -> None:
        state = TrapState(LIVES, played=True)
        self.assertEqual(TrapState.from_json(state.to_json()), state)
        self.assertIsNone(TrapState.from_json(None))
