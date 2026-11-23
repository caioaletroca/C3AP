"""Game-state logic for the BizHawk client, kept free of I/O so it can be unit tested.

Each poll the client parses a ``Snapshot`` and calls ``Watcher.step``. The watcher returns ``Actions``: locations to
send, RAM fields to write, and whether the goal was reached or Crash died. The client performs the I/O.

Ownership rules (docs/DESIGN.md):
- The game's "level completed" field (LEVELS_COMPLETED, bit = level ID) is never written. A level's bit set is its exit
  check, a boss's bit its defeat check, Cortex's the goal (once the goal items are held too). A boss's bit is what
  opens the next warp room's fence (BizHawk).
- Items are per level, like C2AP: "Toad Village Crystal" turns on Toad Village's crystal bit, "Toad Village Clear Gem"
  its gem bit, "Toad Village Relic" its sapphire relic bit. Each of those bits mirrors its item. The boss buttons count
  the crystal total and the secret warp room the relic total, so those totals follow the items.
- Power bits mirror the received powers (the game re-adds earned ones on every level load; the client rewrites them
  each poll). Colored gem bits mirror the received colored gems.
- While Crash is in a level whose check is open, that check's bit is held at 0, so the game spawns the reward and can
  award it; the bit then going 0 -> 1 is the check. A relic holds both the sapphire and the gold bit at 0: what the game
  sets tells the tier (sapphire, gold, both = platinum), and a better tier also sends the lower ones.
- The game sets crystal, gem and relic bits back in the warp room, about 200 frames after the level (OK for crystals
  and gems, BizHawk). So the last level played stays "active" (masked and watched) through the warp room until another
  level loads.
- Gem bits that are still unknown (most gem path gems, the race gems) are learned: while Crash is in a level with one
  open unknown gem, a gem bit nobody owns appearing is that gem. The client logs it so the bit can be added to ram.py.
- With level shuffle, a warp room button's level request is swapped for the shuffled level.
- A warp room builds its buttons from the crystal total when Crash walks up to it; changing the total under a built
  room leaves it with no buttons at all (BizHawk). Crossing 5r only changes warp room r. So in the hub, a change that
  crosses 5r while Crash stands in room r (or in an unknown area) is written together with a reload of the hub (scene
  request 02, which fixes it); other changes are written as they are. Nothing is written while the hub is still
  loading. Elsewhere crystals are written freely: the warp room is rebuilt on the way back.
"""
from collections import Counter
from collections.abc import Collection
from dataclasses import dataclass, field, replace

from . import ram
from .data import (
    BOSSES, COLORED_GEMS, FINAL_BOSS, GEM_LEVELS, ITEM_POWERS, LEVEL_BY_LID, MAIN_LEVELS, PATH_GEM_LEVELS,
    RACE_GEM_LEVELS, RELIC_LEVELS, SECRET_LEVELS, Level,
)
from .locations import RELIC_TIERS, location_name_to_id

CRYSTAL_GRACE_POLLS = 6
"""After the game awards a crystal in the warp room, the total is not lowered for this many polls: if the location held
our own Crystal, the item arrives from the server meanwhile and no reload is needed"""
WARP_ROOM_STEP = 5
"""Warp room states change at every 5 crystals (boss buttons at 5, 10, 15, 20, 25)"""
ITEM_POWER_MASK = sum(1 << power.bit for power in ITEM_POWERS)
EXIT_LEVELS: tuple[Level, ...] = MAIN_LEVELS + SECRET_LEVELS


def crystal_stage(crystals: int) -> int:
    return min(bin(crystals).count("1"), WARP_ROOM_STEP * 5) // WARP_ROOM_STEP


def rooms_changed(old: int, new: int) -> set[int]:
    """Warp rooms whose buttons differ between two crystal fields (crossing 5r changes room r)"""
    low, high = sorted((crystal_stage(old), crystal_stage(new)))
    return set(range(low + 1, high + 1))


@dataclass(frozen=True)
class SlotInfo:
    level_order: tuple[int, ...]
    """Level ID behind each warp room button; index 0 is level 1's button"""
    locations: frozenset[int]
    """Every location of this slot (checked or not)"""
    gem_checks: bool = True
    relic_checks: bool = True
    goal_items: tuple[str, ...] = ()
    """Items the goal needs besides beating Cortex"""

    @classmethod
    def from_slot_data(cls, slot_data: dict, locations: Collection[int]) -> "SlotInfo":
        return cls(level_order=tuple(slot_data["level_order"]), locations=frozenset(locations),
                   gem_checks=bool(slot_data["gem_checks"]), relic_checks=bool(slot_data.get("relic_checks", False)),
                   goal_items=tuple(slot_data.get("goal_items", ())))


@dataclass(frozen=True)
class Mask:
    """A bit held at 0 so the game can award it; the game awarding it checks ``location``"""
    field: str
    """One of FIELDS"""
    bit: int
    location: int


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
    learned: list[tuple[str, int]] = field(default_factory=list)
    """(location name, GEMS bit) of unknown gem bits learned this poll, for the log"""


FIELDS: dict[str, tuple[int, int]] = {
    "crystals": (ram.CRYSTALS, ram.CRYSTALS_SIZE),
    "gems": (ram.GEMS, ram.GEMS_SIZE),
    "powers": (ram.POWERS, 4),
    "sapphires": (ram.SAPPHIRE_RELICS, ram.RELICS_SIZE),
    "golds": (ram.GOLD_RELICS, ram.RELICS_SIZE),
}


def _bit_set(value: int, bit: int) -> bool:
    return bool(value >> bit & 1)


class Watcher:
    def __init__(self, slot: SlotInfo) -> None:
        self.slot = slot
        self.button_target: dict[int, int] = {
            vanilla.lid: target for vanilla, target in zip(MAIN_LEVELS, slot.level_order) if vanilla.lid != target
        }
        """Vanilla level ID of a button -> level it should load (only buttons that changed)"""
        self.home_button: dict[int, int] = {target: button for button, target in self.button_target.items()}
        """Shuffled level ID -> vanilla level ID of the button that leads to it"""
        self.previous: ram.Snapshot | None = None
        self.level: Level | None = None
        """Level or boss Crash is in, or played last while back in the warp room"""
        self.masked: list[Mask] = []
        """Bits held at 0 after the last poll"""
        self.crystal_grace = 0
        """Polls left during which the crystal total is not lowered in the warp room"""
        self.redirected_to: int | None = None
        """Level we last asked the loader for, so its load isn't redirected again"""
        self.redirect_arrived = False
        self.pending_finish: tuple[int, int, bool] | None = None
        """(level played, its button, button's bit already set) after a normal finish of a shuffled level, until the
        game sets the button's "level completed" bit back in the warp room and the client moves it to the level"""
        """The level in ``redirected_to`` has loaded; only then may a return to the warp room forget it"""
        self.known_gem_bits: set[int] = {
            *ram.CLEAR_GEM_BIT_BY_LID.values(),
            *(bit for bit in ram.PATH_GEM_BIT_BY_LID.values() if bit is not None),
            *(bit for bit in ram.RACE_GEM_BIT_BY_LID.values() if bit is not None),
            *(bit for bit in ram.COLORED_GEM_BITS.values() if bit is not None),
        }
        """GEMS bits that belong to a known gem; any other gem bit appearing can be learned"""

    def exists(self, name: str) -> bool:
        return location_name_to_id[name] in self.slot.locations

    def step(self, snap: ram.Snapshot, received: Counter[str], checked: Collection[int]) -> Actions:
        actions = Actions()
        previous, self.previous = self.previous, snap

        if snap.on_title:
            self.level = None
            self.masked = []
            return actions

        level = LEVEL_BY_LID.get(snap.level)
        if level is not None:
            self.level = level if level.in_v1 else None
        elif not (snap.in_hub or snap.level == ram.LID_TRANSITION):
            self.level = None
        # else: keep the level just played, whose rewards land in the warp room

        snap = self._move_completed_bit(snap, actions)
        self._detect_checks(snap, previous, received, checked, actions)
        if self.crystal_grace:
            self.crystal_grace -= 1
        if any(mask.field == "crystals" and mask.location in actions.locations for mask in self.masked):
            self.crystal_grace = CRYSTAL_GRACE_POLLS
        self._sync_fields(snap, received, set(checked) | actions.locations, actions)
        self._redirect_level(snap, actions)
        self._fix_return(snap, actions)

        # Every respawn after a death bumps RESPAWN_COUNT; it drops back to 0 in the warp room.
        if (previous is not None and not previous.on_title and not snap.in_hub and snap.level == previous.level
                and snap.respawn_count > previous.respawn_count):
            actions.died = True

        # Lives and masks written in the warp room carry into the next level (BizHawk).
        actions.can_apply_filler = snap.in_hub
        return actions

    # Checks

    def _send(self, name: str, checked: Collection[int], actions: Actions) -> None:
        location = location_name_to_id[name]
        if location in self.slot.locations and location not in checked:
            actions.locations.add(location)

    def _detect_checks(self, snap: ram.Snapshot, previous: ram.Snapshot | None, received: Counter[str],
                       checked: Collection[int], actions: Actions) -> None:
        if previous is None or previous.on_title:
            return

        # Exits and bosses: the game's own "level completed" field. Any set bit whose location is unchecked counts, so
        # they are also sent after a client restart. With level shuffle the client moves the bit the game sets (the
        # button's) to the level played (_move_completed_bit), so a bit always means "this level was finished".
        for level in (*EXIT_LEVELS, *BOSSES):
            if _bit_set(snap.levels_completed, level.lid):
                self._send(level.defeat_location if level.is_boss else level.exit_location, checked, actions)
        if _bit_set(snap.levels_completed, FINAL_BOSS.lid) and all(received[name] for name in self.slot.goal_items):
            actions.goal = True

        if self.level is None:
            return

        # Masked bits: held at 0 last poll, so 0 -> 1 means the game just awarded it.
        for mask in self.masked:
            if mask.field in ("sapphires", "golds"):
                continue  # relics: below, both bits together give the tier
            if not _bit_set(getattr(previous, mask.field), mask.bit) and _bit_set(getattr(snap, mask.field), mask.bit):
                if mask.location not in checked:
                    actions.locations.add(mask.location)

        self._detect_relic(snap, previous, checked, actions)
        if self.slot.gem_checks:
            self._detect_gems(snap, previous, checked, actions)

    def _detect_relic(self, snap: ram.Snapshot, previous: ram.Snapshot, checked: Collection[int],
                      actions: Actions) -> None:
        level = self.level
        assert level is not None
        if not any(mask.field == "sapphires" for mask in self.masked):
            return
        bit = level.lid
        if _bit_set(previous.sapphires, bit) or _bit_set(previous.golds, bit):
            return  # not held at 0 yet
        sapphire, gold = _bit_set(snap.sapphires, bit), _bit_set(snap.golds, bit)
        if not (sapphire or gold):
            return
        tier = 2 if sapphire and gold else 1 if gold else 0
        for name in RELIC_TIERS[:tier + 1]:
            self._send(level.relic_location(name), checked, actions)

    def _detect_gems(self, snap: ram.Snapshot, previous: ram.Snapshot, checked: Collection[int],
                     actions: Actions) -> None:
        level = self.level
        assert level is not None
        new_bits = snap.gems & ~previous.gems

        # Known gem bits that are never masked (a gem path gem the player had no item for is simply not there)
        gems: list[tuple[int | None, str]] = []
        if level.second_gem:
            gems.append((ram.PATH_GEM_BIT_BY_LID.get(level.lid), level.path_gem_location))
        if level.race_gem:
            gems.append((ram.RACE_GEM_BIT_BY_LID.get(level.lid), level.race_gem_location))
        for bit, name in gems:
            if bit is not None and _bit_set(new_bits, bit):
                self._send(name, checked, actions)

        # Unknown gem bits: learn them from the level's one open unknown gem.
        unknown = [name for bit, name in gems
                   if bit is None and self.exists(name) and location_name_to_id[name] not in checked]
        if len(unknown) != 1:
            return
        for bit in range(ram.GEMS_SIZE * 8):
            if _bit_set(new_bits, bit) and bit not in self.known_gem_bits:
                self.known_gem_bits.add(bit)
                self._send(unknown[0], checked, actions)
                actions.learned.append((unknown[0], bit))
                return

    # Writes

    def _masks(self, checked: Collection[int]) -> list[Mask]:
        level = self.level
        if level is None or level.is_boss:
            return []
        masks: list[Mask] = []

        def hold(field_name: str, bit: int | None, name: str) -> None:
            location = location_name_to_id.get(name)
            if bit is not None and location in self.slot.locations and location not in checked:
                masks.append(Mask(field_name, bit, location))

        if level.has_crystal:
            hold("crystals", ram.CRYSTAL_BIT_BY_LID.get(level.lid), level.crystal_location)
        if self.slot.gem_checks:
            hold("gems", ram.CLEAR_GEM_BIT_BY_LID.get(level.lid), level.clear_gem_location)
            if level.second_gem:
                hold("gems", ram.PATH_GEM_BIT_BY_LID.get(level.lid), level.path_gem_location)
            if level.race_gem:
                hold("gems", ram.RACE_GEM_BIT_BY_LID.get(level.lid), level.race_gem_location)
            if level.colored_gem is not None:
                hold("gems", ram.COLORED_GEM_BITS[level.colored_gem.value], level.colored_gem_location)
        if self.slot.relic_checks and level.has_relic:
            open_relics = [location_name_to_id[level.relic_location(tier)] for tier in RELIC_TIERS]
            location = next((loc for loc in open_relics if loc in self.slot.locations and loc not in checked), None)
            if location is not None:
                masks.append(Mask("sapphires", level.lid, location))
                masks.append(Mask("golds", level.lid, location))
        return masks

    def desired(self, snap: ram.Snapshot, received: Counter[str], checked: Collection[int]) -> dict[str, int]:
        """The value each owned field should have now."""
        self.masked = self._masks(checked)
        masked = {(mask.field, mask.bit) for mask in self.masked}

        def mirror(value: int, field_name: str, bit: int | None, owned: bool) -> int:
            if bit is None:
                return value
            if owned and (field_name, bit) not in masked:
                return value | 1 << bit
            return value & ~(1 << bit)

        crystals = snap.crystals
        for level in MAIN_LEVELS:
            crystals = mirror(crystals, "crystals", ram.CRYSTAL_BIT_BY_LID[level.lid], bool(received[level.crystal_item]))

        powers = snap.powers & ~ITEM_POWER_MASK
        for power in ITEM_POWERS:
            if received[power.name]:
                powers |= 1 << power.bit
        values = {"crystals": crystals, "powers": powers}

        if self.slot.gem_checks:
            gems = snap.gems
            for level in GEM_LEVELS:
                gems = mirror(gems, "gems", ram.CLEAR_GEM_BIT_BY_LID[level.lid], bool(received[level.clear_gem_item]))
            for level in PATH_GEM_LEVELS:
                gems = mirror(gems, "gems", ram.PATH_GEM_BIT_BY_LID.get(level.lid), bool(received[level.path_gem_item]))
            for level in RACE_GEM_LEVELS:
                gems = mirror(gems, "gems", ram.RACE_GEM_BIT_BY_LID.get(level.lid), bool(received[level.race_gem_item]))
            for gem in COLORED_GEMS:
                gems = mirror(gems, "gems", ram.COLORED_GEM_BITS[gem.value], bool(received[gem.item_name]))
            values["gems"] = gems

        if self.slot.relic_checks:
            # A Relic item is that level's sapphire relic; gold bits are only the game's, while a time trial is open.
            sapphires, golds = snap.sapphires, snap.golds
            for level in RELIC_LEVELS:
                sapphires = mirror(sapphires, "sapphires", level.lid, bool(received[level.relic_item]))
                golds = mirror(golds, "golds", level.lid, False)
            values["sapphires"], values["golds"] = sapphires, golds
        return values

    def _sync_fields(self, snap: ram.Snapshot, received: Counter[str], checked: Collection[int],
                     actions: Actions) -> None:
        for name, value in self.desired(snap, received, checked).items():
            current = getattr(snap, name)
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

    def _move_completed_bit(self, snap: ram.Snapshot, actions: Actions) -> ram.Snapshot:
        """A normal finish sets the "level completed" bit of LAST_LEVEL, which _fix_return points at the button
        (BizHawk: Gee Wiz behind Under Pressure's button set bit 14). The game reads a level's own bit, for example to
        offer its time trial (BizHawk: no clock in Gee Wiz), so move the bit to the level played. The button's bit is
        kept if its own level had already been finished. Returns the snapshot as it will be after the write."""
        level = self.level
        if (self.pending_finish is None and level is not None and level.lid in self.home_button
                and snap.gamestate == ram.GAMESTATE_LEVEL_DONE):
            button = self.home_button[level.lid]
            self.pending_finish = (level.lid, button, _bit_set(snap.levels_completed, button))
        if self.pending_finish is None:
            return snap
        played, button, button_was_set = self.pending_finish
        if snap.level not in (played, ram.LID_WARP_ROOM, ram.LID_TRANSITION):
            self.pending_finish = None  # another level loaded: give up
            return snap
        if not (snap.in_hub and _bit_set(snap.levels_completed, button)):
            return snap  # the game hasn't set it yet
        self.pending_finish = None
        value = snap.levels_completed | 1 << played
        if not button_was_set:
            value &= ~(1 << button)
        if value == snap.levels_completed:
            return snap
        actions.writes[ram.LEVELS_COMPLETED] = (value, ram.LEVELS_COMPLETED_SIZE)
        actions.guards[ram.LEVELS_COMPLETED] = (snap.levels_completed, ram.LEVELS_COMPLETED_SIZE)
        return replace(snap, levels_completed=value)

    def _fix_return(self, snap: ram.Snapshot, actions: Actions) -> None:
        """Back in the warp room, Crash spawns at the button of the level in LAST_LEVEL, which the game sets to the
        level just played (BizHawk). When leaving a shuffled level, point it once at the button that leads there, so
        Crash comes back to the warp room he left. Only the level just played is rewritten: the button's own level may
        be shuffled too, and rewriting that again would walk around the shuffle (BizHawk: landed at Midnight Run)."""
        level = self.level
        if level is None or level.lid != snap.last_level or level.lid not in self.home_button:
            return
        if snap.gamestate in (ram.GAMESTATE_LEVEL_DONE, ram.GAMESTATE_QUIT) or snap.hub_loading_or_in:
            actions.writes[ram.LAST_LEVEL] = (self.home_button[level.lid] << 8, 4)
            actions.guards[ram.LAST_LEVEL] = (snap.last_level << 8, 4)

    def _redirect_level(self, snap: ram.Snapshot, actions: Actions) -> None:
        """Level shuffle: load the shuffled level instead of the button's vanilla one.

        The button's request sits in SCENE_REQUEST for 3 frames, so it can be missed; then the vanilla
        level loads and asking for the shuffled one replaces it. A level we asked for ourselves is never redirected.
        """
        if not self.button_target:
            return
        # LEVEL lags the loaded scene by ~345 frames (BizHawk), so right after a swapped request LEVEL still reads
        # "warp room": a redirect is only forgotten once its level was reached and Crash is back in the warp room.
        if self.redirected_to is not None and snap.level == self.redirected_to:
            self.redirect_arrived = True
        if self.redirect_arrived and snap.hub_ready:
            self.redirected_to = None
            self.redirect_arrived = False
        if snap.scene_request in self.button_target and snap.scene_request != self.redirected_to:
            self._ask_for(self.button_target[snap.scene_request], snap.scene_request, actions)
        elif (not snap.in_hub and snap.level in self.button_target and snap.level != self.redirected_to
              and snap.scene_request == ram.NO_SCENE):
            self._ask_for(self.button_target[snap.level], ram.NO_SCENE, actions)

    def _ask_for(self, target: int, guard: int, actions: Actions) -> None:
        actions.writes[ram.SCENE_REQUEST] = (target, 4)
        actions.guards[ram.SCENE_REQUEST] = (guard, 4)
        self.redirected_to = target
        self.redirect_arrived = False
