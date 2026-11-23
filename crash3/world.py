from typing import Any, ClassVar, TextIO

from BaseClasses import ItemClassification, Region, Tutorial
from Options import OptionError
from rule_builder.rules import Has, HasAll, HasGroup, Rule, True_
from worlds.AutoWorld import WebWorld, World

from .data import (
    BOSS_BY_ROOM, COLORED_GEMS, CRASH_DASH, FINAL_BOSS, ITEM_POWERS, LEVEL_BY_LID, LEVELS_PER_ROOM, MAIN_LEVELS,
    SECRET_EXITS_BY_HOST, SECRET_LEVELS, WARP_ROOMS, Gem, Level,
)
from .items import (
    CRYSTALS_GROUP, DEFAULT_CLASSIFICATION, FILLER_WEIGHTS, GAME_NAME, GEMS_GROUP, NO_LIVES_TRAP, RELICS_GROUP,
    VICTORY, Crash3Item, item_name_groups, item_name_to_id,
)
from .locations import CORTEX_EVENT, RELIC_TIERS, Crash3Location, location_name_groups, location_name_to_id
from .options import Crash3Options, LevelShuffle, option_groups, option_presets
from .shuffle import shuffle_all_rooms, shuffle_within_rooms, vanilla_order


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


SECRET_ROOM = "Secret Warp Room"
SECRET_ROOM_RELICS = 5
"""The secret warp room's center pad appears at 5 relics (BizHawk)"""
CRYSTALS_PER_BOSS = LEVELS_PER_ROOM
"""Boss r's button needs a total of 5 * r crystals (the game counts the total, BizHawk)"""


def names_rule(names: tuple[str, ...]) -> Rule[Any]:
    return HasAll(*names) if names else True_()


def colors_rule(gems: tuple[Gem, ...]) -> Rule[Any]:
    return names_rule(tuple(gem.item_name for gem in gems))


def crystals(count: int) -> Rule[Any]:
    return HasGroup(CRYSTALS_GROUP, count) if count else True_()


def relics(count: int) -> Rule[Any]:
    return HasGroup(RELICS_GROUP, count) if count else True_()


class Crash3World(World):
    """
    Crash Bandicoot 3: Warped (PS1, 1998). Travel through time with Crash and Coco to collect the crystals before
    Dr. Neo Cortex and Uka Uka do. Crystals, gems, relics and boss powers are shuffled into the multiworld.
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

    def generate_early(self) -> None:
        # Universal Tracker regenerates from slot data so the tracked level order matches the real seed.
        passthrough: dict[str, Any] = getattr(self.multiworld, "re_gen_passthrough", {}).get(self.game, {})
        if passthrough:
            for name in ("goal", "gem_checks", "relic_checks", "platinum_relics"):
                getattr(self.options, name).value = passthrough[name]
            self.level_order = [LEVEL_BY_LID[lid] for lid in passthrough["level_order"]]
            return

        if self.options.goal.needs_gems:
            self.options.gem_checks.value = True
        if self.options.goal.needs_relics:
            self.options.relic_checks.value = True
        if not self.options.relic_checks:
            self.options.platinum_relics.value = False
        shuffle = self.options.level_shuffle.value
        if shuffle == LevelShuffle.option_all_rooms:
            self.level_order = shuffle_all_rooms(self.random)
        elif shuffle == LevelShuffle.option_within_rooms:
            self.level_order = shuffle_within_rooms(self.random)
        else:
            self.level_order = vanilla_order()

    # Logic helpers

    @staticmethod
    def gem_powers(level: Level) -> Rule[Any]:
        """Powers to get a level's gems (owner's rule, data.Level.gem_powers). Tied to the level, not to its button,
        so shuffle stays honest."""
        return names_rule(level.gem_powers)

    @staticmethod
    def relic_rule(level: Level) -> Rule[Any]:
        """Time trials need Crash Dash, except in the ride levels (owner). As in the game, a main level's time trial
        clock only appears once its crystal is owned (BizHawk: no clock in Gee Wiz until the Gee Wiz Crystal item came);
        the secret levels have no crystal."""
        rule: Rule[Any] = Has(CRASH_DASH) if level.relic_needs_dash else True_()
        return rule & Has(level.crystal_item) if level.has_crystal else rule

    # Regions and locations

    def create_regions(self) -> None:
        menu = Region("Menu", self.player, self.multiworld)
        self.multiworld.regions.append(menu)

        previous = menu
        first_room: Region | None = None
        for room in range(1, WARP_ROOMS + 1):
            region = Region(room_region_name(room), self.player, self.multiworld)
            self.multiworld.regions.append(region)
            # Warp room r opens when boss r - 1 is beaten, whose button needs 5 * (r - 1) crystals.
            self.create_entrance(previous, region, crystals(CRYSTALS_PER_BOSS * (room - 1)))
            previous = region
            first_room = first_room or region

            buttons = self.level_order[(room - 1) * LEVELS_PER_ROOM:room * LEVELS_PER_ROOM]
            for level in buttons:
                self.add_level_locations(region, level)
            self.add_boss(region, BOSS_BY_ROOM[room])

        if self.options.relic_checks:
            assert first_room is not None
            secret = Region(SECRET_ROOM, self.player, self.multiworld)
            self.multiworld.regions.append(secret)
            self.create_entrance(first_room, secret, relics(SECRET_ROOM_RELICS))
            for level in SECRET_LEVELS:
                self.add_secret_level(secret, level)

    def secret_exit_levels(self) -> list[Level]:
        """Hot Coco always; Eggipus Rex only with gem checks, since its entrance needs the Yellow Gem item"""
        return [level for levels in SECRET_EXITS_BY_HOST.values() for level in levels
                if self.options.gem_checks or not level.entry_gems]

    def add_level_locations(self, region: Region, level: Level) -> None:
        for secret in SECRET_EXITS_BY_HOST.get(level.name, ()):
            if secret in self.secret_exit_levels():
                self.add_secret_exit(region, secret)
        # Every level can be finished, and its crystal taken, with no powers (owner).
        self.add_location(region, level.crystal_location)
        self.add_location(region, level.exit_location)
        self.add_relics(region, level)
        if not self.options.gem_checks:
            return
        powers = self.gem_powers(level)
        # Hang 'em High's Yellow Gem and Future Frenzy's clear gem are reached through a secret warp room pad.
        behind_pad = relics(level.gem_relics)
        reachable = not level.gem_relics or bool(self.options.relic_checks)
        box_gem = powers & colors_rule(level.box_gem_colors)
        if level.colored_gem is not None:
            self.set_rule(self.add_location(region, level.clear_gem_location), box_gem)
            if reachable:
                self.set_rule(self.add_location(region, level.colored_gem_location), powers & behind_pad)
        elif reachable:
            self.set_rule(self.add_location(region, level.clear_gem_location), box_gem & behind_pad)
        if level.second_gem and reachable:
            self.set_rule(self.add_location(region, level.path_gem_location),
                          powers & behind_pad & colors_rule(level.path_gem) & names_rule(level.path_powers))

    def add_secret_level(self, region: Region, level: Level) -> None:
        pad = relics(level.pad_relics)
        self.set_rule(self.add_location(region, level.exit_location), pad)
        self.add_relics(region, level, pad)
        if self.options.gem_checks:
            self.set_rule(self.add_location(region, level.clear_gem_location), pad)
            if level.race_gem:
                self.set_rule(self.add_location(region, level.race_gem_location), pad)

    def add_secret_exit(self, region: Region, level: Level) -> None:
        """Reached through the host level's secret exit, so from the warp room of the host's button (level shuffle
        moves it with the host). Box gem, finish gem and relics need no powers (owner)."""
        access = colors_rule(level.entry_gems)
        self.set_rule(self.add_location(region, level.entry_location), access)
        self.set_rule(self.add_location(region, level.exit_location), access)
        if self.options.gem_checks:
            self.set_rule(self.add_location(region, level.clear_gem_location), access)
        self.add_relics(region, level, access)

    def add_relics(self, region: Region, level: Level, access: Rule[Any] | None = None) -> None:
        if not self.options.relic_checks:
            return
        tiers = RELIC_TIERS if self.options.platinum_relics else RELIC_TIERS[:2]
        for tier in tiers:
            self.set_rule(self.add_location(region, level.relic_location(tier)),
                          self.relic_rule(level) & (access if access is not None else True_()))

    def add_boss(self, region: Region, boss: Level) -> None:
        needs = crystals(CRYSTALS_PER_BOSS * boss.room)
        if boss is FINAL_BOSS:
            event = Crash3Location(self.player, CORTEX_EVENT, None, region)
            event.place_locked_item(Crash3Item(VICTORY, ItemClassification.progression, None, self.player))
            region.locations.append(event)
            goal_items = self.goal_item_names()
            self.set_rule(event, needs & (HasAll(*goal_items) if goal_items else True_()))
            return
        self.set_rule(self.add_location(region, boss.defeat_location), needs)

    def add_location(self, region: Region, name: str) -> Crash3Location:
        location = Crash3Location(self.player, name, self.location_name_to_id[name], region)
        region.locations.append(location)
        return location

    # Items

    def pool_names(self) -> list[str]:
        """Every non-filler item of this seed"""
        names = [level.crystal_item for level in MAIN_LEVELS]
        names += [power.name for power in ITEM_POWERS]
        if self.options.gem_checks:
            names += [gem.item_name for gem in COLORED_GEMS]
            names += [level.clear_gem_item for level in MAIN_LEVELS]
            names += [level.path_gem_item for level in MAIN_LEVELS if level.second_gem]
            if self.options.relic_checks:
                names += [level.clear_gem_item for level in SECRET_LEVELS]
                names += [level.race_gem_item for level in SECRET_LEVELS if level.race_gem]
        if self.options.gem_checks:
            names += [level.clear_gem_item for level in self.secret_exit_levels()]
        if self.options.relic_checks:
            names += [level.relic_item for level in (*MAIN_LEVELS, *SECRET_LEVELS, *self.secret_exit_levels())]
        return names

    def goal_item_names(self) -> list[str]:
        """Items the goal needs besides beating Cortex (every gem and/or relic item of this seed)"""
        wanted: set[str] = set()
        if self.options.goal.needs_gems:
            wanted |= item_name_groups[GEMS_GROUP]
        if self.options.goal.needs_relics:
            wanted |= item_name_groups[RELICS_GROUP]
        return [name for name in self.pool_names() if name in wanted]

    def create_item(self, name: str) -> Crash3Item:
        classification = DEFAULT_CLASSIFICATION[name]
        options = getattr(self, "options", None)
        if options is not None:
            if name in item_name_groups["Clear Gems"] and options.goal.needs_gems:
                classification = ItemClassification.progression
            elif name == CRASH_DASH and not options.relic_checks:
                classification = ItemClassification.useful  # only relics need it
            elif name in item_name_groups["Powers"] and name != CRASH_DASH and not options.gem_checks:
                classification = ItemClassification.useful  # only gems need them
        return Crash3Item(name, classification, self.item_name_to_id[name], self.player)

    def create_items(self) -> None:
        pool = [self.create_item(name) for name in self.pool_names()]
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
            "goal": self.options.goal.value,
            "goal_items": self.goal_item_names(),
            "gem_checks": self.options.gem_checks.value,
            "relic_checks": self.options.relic_checks.value,
            "platinum_relics": self.options.platinum_relics.value,
            "death_link": self.options.death_link.value,
            "world_version": ".".join(map(str, self.world_version)),  # from archipelago.json
        }

    def interpret_slot_data(self, slot_data: dict[str, Any]) -> dict[str, Any]:
        """Universal Tracker: return the slot data so it is passed back in through re_gen_passthrough."""
        return slot_data

    def write_spoiler(self, spoiler_handle: TextIO) -> None:
        if self.level_order == vanilla_order():
            return
        spoiler_handle.write(f"\n\nCrash Bandicoot 3 level order ({self.player_name}):\n\n")
        for button, level in zip(MAIN_LEVELS, self.level_order):
            spoiler_handle.write(f"  Level {button.number:2} button ({button.name}): {level.name}\n")

    def extend_hint_information(self, hint_data: dict[int, dict[int, str]]) -> None:
        if self.level_order == vanilla_order():
            return
        info: dict[int, str] = {}
        for button, level in zip(MAIN_LEVELS, self.level_order):
            entrance = f"{room_region_name(button.room)}, button {button.number} ({button.name})"
            for name in location_name_groups[level.name]:
                info[self.location_name_to_id[name]] = entrance
        hint_data[self.player] = info
