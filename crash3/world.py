from typing import Any, ClassVar, TextIO

from BaseClasses import ItemClassification, Region, Tutorial
from Options import OptionError
from rule_builder.rules import Has, HasAll, Rule, True_
from worlds.AutoWorld import WebWorld, World

from .data import (
    BOSS_BY_ROOM, COLORED_GEMS, CRYSTAL_COUNT, CRYSTALS_PER_BOSS, FINAL_BOSS, ITEM_POWERS, LEVEL_BY_LID,
    LEVELS_PER_ROOM, MAIN_LEVELS, WARP_ROOMS, Level, Power, powers_before_room,
)
from .items import (
    CRYSTAL, DEFAULT_CLASSIFICATION, FILLER_WEIGHTS, GAME_NAME, NO_LIVES_TRAP, VICTORY, Crash3Item, item_name_groups,
    item_name_to_id,
)
from .locations import CORTEX_EVENT, Crash3Location, location_name_groups, location_name_to_id
from .options import Crash3Options, option_groups, option_presets
from .shuffle import shuffle_order, vanilla_order


class Crash3Web(WebWorld):
    game = GAME_NAME
    theme = "partyTime"
    bug_report_page = "https://github.com/caioaletroca/C3AP/issues"
    option_groups = option_groups
    options_presets = option_presets
    tutorials = [
        Tutorial(
            "Multiworld Setup Guide",
            "A guide to setting up Crash Bandicoot 3: Warped (PS1) for Archipelago with BizHawk.",
            "English",
            "setup_en.md",
            "setup/en",
            ["C3AP contributors"],
        ),
    ]


def room_region_name(room: int) -> str:
    return f"Warp Room {room}"


def powers_rule(powers: tuple[Power, ...]) -> Rule[Any]:
    return HasAll(*(power.name for power in powers)) if powers else True_()


POWER_NAMES = frozenset(power.name for power in ITEM_POWERS)


class Crash3World(World):
    """
    Crash Bandicoot 3: Warped (PS1, 1998). Travel through time with Crash and Coco to collect the crystals before
    Dr. Neo Cortex and Uka Uka do. Crystals, boss powers and colored gems are shuffled into the multiworld.
    """

    game = GAME_NAME
    web = Crash3Web()
    options_dataclass = Crash3Options
    options: Crash3Options
    topology_present = True

    item_name_to_id: ClassVar[dict[str, int]] = item_name_to_id
    location_name_to_id: ClassVar[dict[str, int]] = location_name_to_id
    item_name_groups = item_name_groups
    location_name_groups = location_name_groups

    level_order: list[Level]
    """Level behind each warp room button; index 0 is level 1's button"""

    powers_in_logic: bool
    """Powers gate warp rooms in logic (with gem checks); without gem checks there's no room for them"""

    def generate_early(self) -> None:
        # Universal Tracker regenerates from slot data so the tracked level order matches the real seed.
        passthrough: dict[str, Any] = getattr(self.multiworld, "re_gen_passthrough", {}).get(self.game, {})
        if passthrough:
            self.options.gem_checks.value = passthrough["gem_checks"]
            self.level_order = [LEVEL_BY_LID[lid] for lid in passthrough["level_order"]]
        elif self.options.level_shuffle:
            self.level_order = shuffle_order(self.random)
        else:
            self.level_order = vanilla_order()
        self.powers_in_logic = bool(self.options.gem_checks)

    def needed_powers(self, room: int) -> Rule[Any]:
        """Powers a vanilla player has when warp room ``room`` opens.

        Requiring them is conservative on purpose: the client hands out powers only as items, levels may need them for
        boxes, and the game may check them (VERIFY) when it opens the next room.
        """
        return powers_rule(powers_before_room(room)) if self.powers_in_logic else True_()

    def room_rule(self, room: int) -> Rule[Any]:
        """Opening warp room ``room``: beat the previous boss, so that room's crystals (and the powers)."""
        if room == 1:
            return True_()
        return Has(CRYSTAL, CRYSTALS_PER_BOSS * (room - 1)) & self.needed_powers(room)

    # Regions and locations

    def create_regions(self) -> None:
        menu = Region("Menu", self.player, self.multiworld)
        self.multiworld.regions.append(menu)

        previous = menu
        for room in range(1, WARP_ROOMS + 1):
            region = Region(room_region_name(room), self.player, self.multiworld)
            self.multiworld.regions.append(region)
            self.create_entrance(previous, region, self.room_rule(room))
            previous = region

            buttons = self.level_order[(room - 1) * LEVELS_PER_ROOM:room * LEVELS_PER_ROOM]
            for level in buttons:
                self.add_level_locations(region, level)
            self.add_boss(region, BOSS_BY_ROOM[room])

    def add_level_locations(self, region: Region, level: Level) -> None:
        # Wherever it is, a level needs the powers a vanilla player has in its own warp room.
        needs = self.needed_powers(level.room)
        self.set_rule(self.add_location(region, level.crystal_location), needs)
        if not self.options.gem_checks:
            return
        self.set_rule(self.add_location(region, level.clear_gem_location), needs)
        if level.path_gem:
            self.set_rule(self.add_location(region, level.path_gem_location),
                          needs & HasAll(*(gem.item_name for gem in level.path_gem)))
        if level.colored_gem is not None:
            self.set_rule(self.add_location(region, level.colored_gem_location), needs)

    def add_boss(self, region: Region, boss: Level) -> None:
        crystals = Has(CRYSTAL, CRYSTALS_PER_BOSS * boss.room)
        if boss is FINAL_BOSS:
            event = Crash3Location(self.player, CORTEX_EVENT, None, region)
            event.place_locked_item(Crash3Item(VICTORY, ItemClassification.progression, None, self.player))
            region.locations.append(event)
            self.set_rule(event, crystals)
            return
        self.set_rule(self.add_location(region, boss.defeat_location), crystals)

    def add_location(self, region: Region, name: str) -> Crash3Location:
        location = Crash3Location(self.player, name, self.location_name_to_id[name], region)
        region.locations.append(location)
        return location

    # Items

    def create_item(self, name: str) -> Crash3Item:
        classification = DEFAULT_CLASSIFICATION[name]
        if name in POWER_NAMES and not getattr(self, "powers_in_logic", True):
            classification = ItemClassification.useful
        return Crash3Item(name, classification, self.item_name_to_id[name], self.player)

    def create_items(self) -> None:
        pool: list[Crash3Item] = [self.create_item(CRYSTAL) for _ in range(CRYSTAL_COUNT)]
        pool += [self.create_item(power.name) for power in ITEM_POWERS]
        if self.options.gem_checks:
            pool += [self.create_item(gem.item_name) for gem in COLORED_GEMS]

        unfilled = len(self.multiworld.get_unfilled_locations(self.player))
        if len(pool) > unfilled:
            raise OptionError(f"{self.player_name}: {len(pool)} items for only {unfilled} locations")
        pool += [self.create_filler() for _ in range(unfilled - len(pool))]
        self.multiworld.itempool += pool

    def get_filler_item_name(self) -> str:
        if self.random.randint(0, 99) < self.options.trap_chance.value:
            return NO_LIVES_TRAP
        names = list(FILLER_WEIGHTS)
        return self.random.choices(names, weights=[FILLER_WEIGHTS[name] for name in names])[0]

    # Logic

    def set_rules(self) -> None:
        self.set_completion_rule(Has(VICTORY))

    # Output

    def fill_slot_data(self) -> dict[str, Any]:
        return {
            "level_order": [level.lid for level in self.level_order],
            "gem_checks": self.options.gem_checks.value,
            "death_link": self.options.death_link.value,
            "world_version": ".".join(map(str, self.world_version)),  # from archipelago.json
        }

    def interpret_slot_data(self, slot_data: dict[str, Any]) -> dict[str, Any]:
        """Universal Tracker: return the slot data so it is passed back in through re_gen_passthrough."""
        return slot_data

    def write_spoiler(self, spoiler_handle: TextIO) -> None:
        if not self.options.level_shuffle:
            return
        spoiler_handle.write(f"\n\nCrash Bandicoot 3 level order ({self.player_name}):\n\n")
        for button, level in zip(MAIN_LEVELS, self.level_order):
            spoiler_handle.write(f"  Level {button.number:2} button ({button.name}): {level.name}\n")

    def extend_hint_information(self, hint_data: dict[int, dict[int, str]]) -> None:
        if not self.options.level_shuffle:
            return
        info: dict[int, str] = {}
        for button, level in zip(MAIN_LEVELS, self.level_order):
            entrance = f"{room_region_name(button.room)}, button {button.number} ({button.name})"
            for name in (level.crystal_location, level.clear_gem_location, level.path_gem_location,
                         level.colored_gem_location if level.colored_gem else ""):
                if name in self.location_name_to_id:
                    info[self.location_name_to_id[name]] = entrance
        hint_data[self.player] = info
