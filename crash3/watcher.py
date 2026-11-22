"""Game-state logic for the BizHawk client, kept free of I/O so it can be unit tested.

Each poll the client parses a ``Snapshot`` and calls ``Watcher.step``. The watcher returns ``Actions``: locations to
send, RAM fields to write, and whether the goal was reached or Crash died. The client performs the I/O.

Ownership rules (the same scheme that works in Crash 1, see docs/DESIGN.md):
- Bosses: the game's "level completed" field (LEVELS_COMPLETED, bit = level ID) is never written; a boss's bit set is
  its defeat check (Cortex's: the goal). A boss's bit is what opens the next warp room's fence (BizHawk).
- Crystal bits mirror the received Crystal items, filled in level order (warp room 1's five first), so N crystals
  open the first N // 5 boss buttons. Power bits mirror the received powers (the game
  re-adds earned ones on every level load; the client rewrites them each poll). Colored gem bits (once their bit is known)
  mirror the received colored gems.
- While Crash is in a level whose crystal (or colored gem, or boss power) location is unchecked, that bit is held at 0,
  so the game spawns the crystal and can award it; the bit then going 0 -> 1 is the check.
- The game sets the crystal and gem bits back in the warp room, about 200 frames after the level (OK, BizHawk). So
  the last level played stays "active" (masked and watched) through the warp room until another level loads.
- Clear gem bits are never written: the active level's clear gem bit (or its gem path gem's bit) appearing is that
  check.
- With level shuffle, a warp room button's level request is swapped for the shuffled level.
- A warp room builds its buttons from the crystal total when Crash walks up to it; changing the total under a built
  room leaves it with no buttons at all (BizHawk). Crossing 5r only changes warp room r. So in the hub, a change that
  crosses 5r while Crash stands in room r (or in an unknown area) is written together with a reload of the hub (scene
  request 02, which fixes it); other changes are written as they are (the affected room is rebuilt when Crash walks
  there). Nothing is written while the hub is still loading. Elsewhere crystals are written freely: the warp room is rebuilt on the way back.
"""
CRYSTAL_GRACE_POLLS = 6
"""After the game awards a crystal in the warp room, the total is not lowered for this many polls: if the location held
our own Crystal, the item arrives from the server meanwhile and no reload is needed"""
WARP_ROOM_STEP = 5
"""Warp room states change at every 5 crystals (boss buttons at 5, 10, 15, 20, 25)"""


def crystal_stage(crystals: int) -> int:
    return min(bin(crystals).count("1"), WARP_ROOM_STEP * 5) // WARP_ROOM_STEP


def rooms_changed(old: int, new: int) -> set[int]:
    """Warp rooms whose buttons differ between two crystal fields (crossing 5r changes room r)"""
    low, high = sorted((crystal_stage(old), crystal_stage(new)))
    return set(range(low + 1, high + 1))
from collections import Counter
from collections.abc import Collection
from dataclasses import dataclass, field

from . import ram
from .data import (
    BOSSES, COLORED_GEMS, FINAL_BOSS, ITEM_POWERS, LEVEL_BY_LID, MAIN_LEVELS, Kind, Level,
)
from .items import CRYSTAL
from .locations import location_name_to_id

ITEM_POWER_MASK = sum(1 << power.bit for power in ITEM_POWERS)


@dataclass(frozen=True)
class SlotInfo:
    level_order: tuple[int, ...]
    """Level ID behind each warp room button; index 0 is level 1's button"""
    gem_checks: bool

    @classmethod
    def from_slot_data(cls, slot_data: dict) -> "SlotInfo":
        return cls(level_order=tuple(slot_data["level_order"]), gem_checks=bool(slot_data["gem_checks"]))


@dataclass(frozen=True)
class Mask:
    """A bit held at 0 so the game can award it; the game awarding it checks ``location`` (None: the goal)"""
    field: str
    """One of FIELDS: crystals, gems or powers"""
    bit: int
    location: int | None


@dataclass
class Actions:
    locations: set[int] = field(default_factory=set)
    writes: dict[int, tuple[int, int]] = field(default_factory=dict)
    """address -> (value, size in bytes)"""
    guards: dict[int, tuple[int, int]] = field(default_factory=dict)
    """address -> (value, size) that must still be there for ``writes`` to apply"""
    goal: bool = False
    died: bool = False
    can_apply_filler: bool = False
    reload_hub: bool = False
    """The writes include a warp room reload"""


FIELDS: dict[str, tuple[int, int]] = {
    "crystals": (ram.CRYSTALS, ram.CRYSTALS_SIZE),
    "gems": (ram.GEMS, ram.GEMS_SIZE),
    "powers": (ram.POWERS, 4),
}


def _field(snap: ram.Snapshot, name: str) -> int:
    return getattr(snap, name)


class Watcher:
    def __init__(self, slot: SlotInfo) -> None:
        self.slot = slot
        self.button_target: dict[int, int] = {
            vanilla.lid: target for vanilla, target in zip(MAIN_LEVELS, slot.level_order) if vanilla.lid != target
        }
        """Vanilla level ID of a button -> level it should load (only buttons that changed)"""
        self.previous: ram.Snapshot | None = None
        self.level: Level | None = None
        """Main level or boss Crash is in, or played last while back in the warp room"""
        self.masked: list[Mask] = []
        """Bits held at 0 after the last poll"""
        self.crystal_grace = 0
        """Polls left during which the crystal total is not lowered in the warp room"""
        self.redirected_to: int | None = None
        """Level we last asked the loader for, so its load isn't redirected again"""

    def step(self, snap: ram.Snapshot, received: Counter[str], checked: Collection[int]) -> Actions:
        actions = Actions()
        previous, self.previous = self.previous, snap

        if snap.on_title:
            self.level = None
            self.masked = []
            return actions

        level = LEVEL_BY_LID.get(snap.level)
        if level is not None:
            self.level = level if level.kind != Kind.SECRET else None
        elif not (snap.in_hub or snap.level == ram.LID_TRANSITION):
            self.level = None
        # else: keep the level just played, whose rewards land in the warp room

        self._detect_checks(snap, previous, checked, actions)
        if self.crystal_grace:
            self.crystal_grace -= 1
        if any(mask.field == "crystals" and mask.location in actions.locations for mask in self.masked):
            self.crystal_grace = CRYSTAL_GRACE_POLLS
        self._sync_fields(snap, received, set(checked) | actions.locations, actions)
        self._redirect_level(snap, actions)

        # Every respawn after a death bumps RESPAWN_COUNT (VERIFY for Crash 3); it drops back to 0 when a level starts.
        if (previous is not None and not previous.on_title and not snap.in_hub and snap.level == previous.level
                and snap.respawn_count > previous.respawn_count):
            actions.died = True

        # Lives and masks are applied in the warp room and carry into the next level (VERIFY, as in Crash 1).
        actions.can_apply_filler = snap.in_hub
        return actions

    # Checks

    def _detect_checks(self, snap: ram.Snapshot, previous: ram.Snapshot | None, checked: Collection[int],
                       actions: Actions) -> None:
        if previous is None or previous.on_title:
            return

        # Bosses: the game's own "level completed" field (never written by the client). Any set bit whose location is
        # unchecked counts, so a defeat is also sent after a client restart.
        for boss in (*BOSSES, FINAL_BOSS):
            if snap.levels_completed & (1 << boss.lid):
                if boss is FINAL_BOSS:
                    actions.goal = True
                else:
                    location = location_name_to_id[boss.defeat_location]
                    if location not in checked:
                        actions.locations.add(location)

        if self.level is None:
            return

        # Masked bits: held at 0 last poll, so 0 -> 1 means the game just awarded it.
        for mask in self.masked:
            bit = 1 << mask.bit
            if not _field(previous, mask.field) & bit and _field(snap, mask.field) & bit:
                if mask.location is None:
                    actions.goal = True
                elif mask.location not in checked:
                    actions.locations.add(mask.location)

        # Clear gems: the level's own bit appearing (never written by the client).
        if self.slot.gem_checks and self.level.kind == Kind.LEVEL:
            gem_bits = [(ram.CLEAR_GEM_BIT_BY_LID.get(self.level.lid), self.level.clear_gem_location)]
            if self.level.path_gem:
                gem_bits.append((ram.PATH_GEM_BIT_BY_LID.get(self.level.lid), self.level.path_gem_location))
            for bit, name in gem_bits:
                if bit is not None and not previous.gems & (1 << bit) and snap.gems & (1 << bit):
                    actions.locations.add(location_name_to_id[name])

    # Writes

    def _masks(self, checked: Collection[int]) -> list[Mask]:
        level = self.level
        if level is None:
            return []
        masks: list[Mask] = []
        if level.kind == Kind.LEVEL:
            location = location_name_to_id[level.crystal_location]
            bit = ram.CRYSTAL_BIT_BY_LID.get(level.lid)
            if bit is not None and location not in checked:
                masks.append(Mask("crystals", bit, location))
            if self.slot.gem_checks and level.colored_gem is not None:
                location = location_name_to_id[level.colored_gem_location]
                bit = ram.COLORED_GEM_BITS[level.colored_gem.value]
                if bit is not None and location not in checked:
                    masks.append(Mask("gems", bit, location))
        return masks

    def desired(self, snap: ram.Snapshot, received: Counter[str], checked: Collection[int]) -> dict[str, int]:
        """The value each owned field should have now."""
        self.masked = self._masks(checked)
        masked = {(mask.field, mask.bit) for mask in self.masked}

        crystals = snap.crystals
        # Boss buttons read the total (OK per the owner), so fill the first unmasked bits: a level held at 0 while its
        # crystal is unchecked never costs a received crystal.
        owned = min(received[CRYSTAL], len(MAIN_LEVELS))
        for level in MAIN_LEVELS:
            bit = ram.CRYSTAL_BIT_BY_LID[level.lid]
            if owned > 0 and ("crystals", bit) not in masked:
                crystals |= 1 << bit
                owned -= 1
            else:
                crystals &= ~(1 << bit)

        powers = snap.powers & ~ITEM_POWER_MASK
        for power in ITEM_POWERS:
            if received[power.name]:
                powers |= 1 << power.bit

        gems = snap.gems
        if self.slot.gem_checks:
            for gem in COLORED_GEMS:
                bit = ram.COLORED_GEM_BITS[gem.value]
                if bit is None:
                    continue
                if received[gem.item_name] and ("gems", bit) not in masked:
                    gems |= 1 << bit
                else:
                    gems &= ~(1 << bit)

        return {"crystals": crystals, "powers": powers, "gems": gems}

    def _sync_fields(self, snap: ram.Snapshot, received: Counter[str], checked: Collection[int],
                     actions: Actions) -> None:
        for name, value in self.desired(snap, received, checked).items():
            current = _field(snap, name)
            if value == current:
                continue
            if name == "crystals" and snap.hub_loading_or_in:
                if not snap.hub_ready:
                    continue  # the room may be building its buttons: wait
                if self.crystal_grace and bin(value).count("1") < bin(current).count("1"):
                    continue  # the crystal just awarded may be our own: wait for the item
                changed = rooms_changed(current, value)
                if changed and (snap.warp_room is None or snap.warp_room in changed):
                    actions.writes[ram.SCENE_REQUEST] = (ram.LID_WARP_ROOM, 4)
                    actions.guards[ram.SCENE_REQUEST] = (ram.NO_SCENE, 4)
                    actions.reload_hub = True
            address, size = FIELDS[name]
            actions.writes[address] = (value, size)
            actions.guards[address] = (current, size)

    def _redirect_level(self, snap: ram.Snapshot, actions: Actions) -> None:
        """Level shuffle (EXPERIMENTAL): load the shuffled level instead of the button's vanilla one.

        The button's request usually sits in SCENE_REQUEST for a single frame, so it is mostly missed; then the vanilla
        level loads and asking for the shuffled one replaces it. A level we asked for ourselves is never redirected.
        """
        if not self.button_target:
            return
        if snap.in_hub:
            self.redirected_to = None
        if snap.scene_request in self.button_target:
            target = self.button_target[snap.scene_request]
            actions.writes[ram.SCENE_REQUEST] = (target, 4)
            actions.guards[ram.SCENE_REQUEST] = (snap.scene_request, 4)
            self.redirected_to = target
        elif (not snap.in_hub and snap.level in self.button_target and snap.level != self.redirected_to
              and snap.scene_request == ram.NO_SCENE):
            target = self.button_target[snap.level]
            actions.writes[ram.SCENE_REQUEST] = (target, 4)
            actions.guards[ram.SCENE_REQUEST] = (ram.NO_SCENE, 4)
            self.redirected_to = target
