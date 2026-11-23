"""Static game data for Crash Bandicoot 3: Warped (PS1, NTSC-U SCUS-94244).

Sources (see docs/DESIGN.md):
- Level IDs: CrateModLoader ``Crash3_Common.cs`` (the ``S00000xx.NSF`` file IDs). 0x0A = Orient Express and
  0x11 = Midnight Run are confirmed by the "Play as Coco" GameShark code, 0x02 = warp room by the crash3-decomp notes.
- Warp rooms, bosses, powers and gems: the game's own structure as described by the N. Sane Trilogy guides
  (PowerPyx, The Escapist), cross-checked against each other.

Anything marked VERIFY still has to be confirmed in an emulator (tools/VERIFY.md).
"""
from dataclasses import dataclass, field
from enum import Enum


class Kind(Enum):
    LEVEL = "level"
    BOSS = "boss"
    FINAL_BOSS = "final_boss"
    SECRET = "secret"
    """Opened from the secret warp room by the relic count"""
    SECRET_EXIT = "secret_exit"
    """Hot Coco and Eggipus Rex: reached through another level's secret exit (not in v1.0 yet)"""


class Gem(Enum):
    RED = "Red"
    GREEN = "Green"
    PURPLE = "Purple"
    BLUE = "Blue"
    YELLOW = "Yellow"

    @property
    def item_name(self) -> str:
        return f"{self.value} Gem"


COLORED_GEMS: tuple[Gem, ...] = (Gem.RED, Gem.GREEN, Gem.PURPLE, Gem.BLUE, Gem.YELLOW)


@dataclass(frozen=True)
class Level:
    name: str
    lid: int
    """Level ID (the LEVEL global >> 8, the NSF file number)"""
    number: int
    """Level number in the game (1-25 main, 26-30 secret); bosses use 0"""
    room: int
    """Warp room (1-5); 6 = the secret warp room"""
    kind: Kind = Kind.LEVEL
    path_gem: tuple[Gem, ...] = field(default=())
    """Colored gems needed for this level's second (gem path) clear gem; empty if it has none"""
    colored_gem: Gem | None = None
    """The colored gem found in this level"""
    path_powers: tuple[str, ...] = ()
    """Powers the gem path needs beyond what the warp room already requires (owner, BizHawk)"""
    pad_relics: int = 0
    """Secret levels: relics that open their secret warp room pad"""
    gem_relics: int = 0
    """Relics needed for this level's gem, reached through a secret warp room pad (Hang 'em High's Yellow Gem = pad
    27, Future Frenzy's clear gem = pad 29)"""
    race_gem: bool = False
    """Secret levels with a second clear gem for first place in the race"""

    @property
    def in_v1(self) -> bool:
        return self.kind != Kind.SECRET_EXIT

    @property
    def has_crystal(self) -> bool:
        return self.kind == Kind.LEVEL

    @property
    def has_relic(self) -> bool:
        """Has a time trial: every main and secret level"""
        return self.kind in (Kind.LEVEL, Kind.SECRET, Kind.SECRET_EXIT)

    @property
    def relic_needs_dash(self) -> bool:
        return self.number not in RELIC_WITHOUT_DASH

    @property
    def exit_location(self) -> str:
        return f"{self.name} - Exit"

    @property
    def race_gem_location(self) -> str:
        return f"{self.name} - Race Clear Gem"

    def relic_location(self, tier: str) -> str:
        return f"{self.name} - {tier} Relic"

    # Items (one per level and kind, like C2AP: each turns on its own level's bit)

    @property
    def crystal_item(self) -> str:
        return f"{self.name} Crystal"

    @property
    def clear_gem_item(self) -> str:
        return f"{self.name} Clear Gem"

    @property
    def path_gem_item(self) -> str:
        return f"{self.name} Gem Path Clear Gem"

    @property
    def race_gem_item(self) -> str:
        return f"{self.name} Race Clear Gem"

    @property
    def relic_item(self) -> str:
        return f"{self.name} Relic"

    @property
    def is_boss(self) -> bool:
        return self.kind in (Kind.BOSS, Kind.FINAL_BOSS)

    @property
    def crystal_location(self) -> str:
        return f"{self.name} - Crystal"

    @property
    def defeat_location(self) -> str:
        return f"{self.name} - Defeated"

    @property
    def clear_gem_location(self) -> str:
        return f"{self.name} - Clear Gem"

    @property
    def path_gem_location(self) -> str:
        return f"{self.name} - Gem Path Clear Gem"

    @property
    def colored_gem_location(self) -> str:
        assert self.colored_gem is not None
        return f"{self.name} - {self.colored_gem.item_name}"


ALL_COLORS = COLORED_GEMS

LEVELS: tuple[Level, ...] = (
    # Warp room 1
    Level("Toad Village", 0x0B, 1, 1),
    Level("Under Pressure", 0x0E, 2, 1),
    Level("Orient Express", 0x0A, 3, 1),
    Level("Bone Yard", 0x0C, 4, 1, path_gem=(Gem.RED,), path_powers=("Double Jump",)),
    Level("Makin' Waves", 0x19, 5, 1),
    # Warp room 2
    Level("Gee Wiz", 0x0F, 6, 2),
    Level("Hang 'em High", 0x16, 7, 2, colored_gem=Gem.YELLOW, gem_relics=10),  # Yellow Gem: secret pad 27
    Level("Hog Ride", 0x15, 8, 2),
    Level("Tomb Time", 0x12, 9, 2, path_gem=(Gem.PURPLE,)),
    Level("Midnight Run", 0x11, 10, 2),
    # Warp room 3
    Level("Dino Might!", 0x10, 11, 3, path_gem=(Gem.YELLOW,)),
    Level("Deep Trouble", 0x1C, 12, 3, colored_gem=Gem.RED),
    Level("High Time", 0x1A, 13, 3, colored_gem=Gem.PURPLE),
    Level("Road Crash", 0x14, 14, 3),
    Level("Double Header", 0x1D, 15, 3),
    # Warp room 4
    Level("Sphynxinator", 0x1E, 16, 4, path_gem=(Gem.BLUE,)),
    Level("Bye Bye Blimps", 0x13, 17, 4),
    Level("Tell No Tales", 0x0D, 18, 4),
    Level("Future Frenzy", 0x1B, 19, 4, gem_relics=20),  # its clear gem: secret pad 29
    Level("Tomb Wader", 0x18, 20, 4, colored_gem=Gem.BLUE),
    # Warp room 5
    Level("Gone Tomorrow", 0x23, 21, 5, path_gem=(Gem.GREEN,)),
    Level("Orange Asphalt", 0x20, 22, 5),
    Level("Flaming Passion", 0x22, 23, 5, colored_gem=Gem.GREEN),
    Level("Mad Bombers", 0x17, 24, 5),
    Level("Bug Lite", 0x24, 25, 5, path_gem=ALL_COLORS),
    # Bosses: the sixth button of each warp room
    Level("Tiny Tiger", 0x06, 0, 1, Kind.BOSS),
    Level("Dingodile", 0x03, 0, 2, Kind.BOSS),
    Level("N. Tropy", 0x04, 0, 3, Kind.BOSS),
    Level("N. Gin", 0x05, 0, 4, Kind.BOSS),
    Level("Dr. N. Cortex", 0x07, 0, 5, Kind.FINAL_BOSS),
    # Secret warp room. Its pad slots open with the relic count (BizHawk: live, 5 per slot, the pad at
    # 5): 26 Ski Crazed (5), 27 = Hang 'em High's second entry, to the Yellow Gem (10), 28 Area 51? (15), 29 = Future
    # Frenzy's second entry, to its gem (20), 30 Rings of Power (25). Hot Coco (Road Crash's alien sign) and Eggipus Rex
    # (Dino Might!'s Yellow Gem path, second pterodactyl) are secret exits.
    # No crystals there: clear gems (all boxes; Area 51? and Rings of Power also first place in the race) and a relic.
    Level("Ski Crazed", 0x21, 26, 6, Kind.SECRET, pad_relics=5),
    Level("Area 51?", 0x25, 28, 6, Kind.SECRET, pad_relics=15, race_gem=True),
    Level("Rings of Power", 0x1F, 30, 6, Kind.SECRET, pad_relics=25, race_gem=True),
    Level("Hot Coco", 0x27, 31, 6, Kind.SECRET_EXIT),
    Level("Eggipus Rex", 0x26, 32, 6, Kind.SECRET_EXIT),
)

LEVEL_BY_NAME: dict[str, Level] = {level.name: level for level in LEVELS}
LEVEL_BY_LID: dict[int, Level] = {level.lid: level for level in LEVELS}

WARP_ROOMS = 5
LEVELS_PER_ROOM = 5
MAIN_LEVELS: tuple[Level, ...] = tuple(level for level in LEVELS if level.kind == Kind.LEVEL)
RELIC_WITHOUT_DASH: frozenset[int] = frozenset({3, 5, 8, 14, 17, 18, 22, 24, 26, 28, 30})
"""Level numbers whose time trial (relic) doesn't need Crash Dash: the ride levels (owner). Hot Coco (31) unknown."""
SECRET_LEVELS: tuple[Level, ...] = tuple(level for level in LEVELS if level.kind == Kind.SECRET)
"""Secret levels 26/28/30 have no crystal: only clear gems (all boxes; first place in the race) and a relic (wiki
guides, owner). 25 box gems + 6 path gems + these 5 = 36 of the 40 clear gems; Hot Coco and Eggipus Rex hold the rest."""
GEM_LEVELS: tuple[Level, ...] = MAIN_LEVELS + SECRET_LEVELS
"""Levels with a box clear gem in v1.0"""
RELIC_LEVELS: tuple[Level, ...] = tuple(level for level in LEVELS if level.has_relic and level.in_v1)
BOSSES: tuple[Level, ...] = tuple(level for level in LEVELS if level.kind == Kind.BOSS)
FINAL_BOSS: Level = LEVEL_BY_NAME["Dr. N. Cortex"]
BOSS_BY_ROOM: dict[int, Level] = {level.room: level for level in LEVELS if level.is_boss}


@dataclass(frozen=True)
class Power:
    name: str
    boss: str
    """Boss that grants it in vanilla"""
    bit: int
    """Bit in the POWERS global (VERIFY: assumed to be in the order the bosses grant them)"""


POWERS: tuple[Power, ...] = (
    Power("Super Body Slam", "Tiny Tiger", 0),
    Power("Double Jump", "Dingodile", 1),
    Power("Death Tornado Spin", "N. Tropy", 2),
    Power("Fruit Bazooka", "N. Gin", 3),
    Power("Crash Dash", "Dr. N. Cortex", 4),
)
CRASH_DASH = "Crash Dash"
POWER_BY_BOSS: dict[str, Power] = {power.boss: power for power in POWERS}
ITEM_POWERS: tuple[Power, ...] = POWERS
"""Every power is an item, Crash Dash included (the goal is read from the "level completed" field, not the powers)"""


def powers_before_room(room: int) -> tuple[Power, ...]:
    """Powers a player has in vanilla when warp room ``room`` opens (one per boss already beaten)."""
    return tuple(POWER_BY_BOSS[BOSS_BY_ROOM[r].name] for r in range(1, room))


PATH_GEM_LEVELS: tuple[Level, ...] = tuple(level for level in MAIN_LEVELS if level.path_gem)
COLORED_GEM_LEVELS: tuple[Level, ...] = tuple(level for level in MAIN_LEVELS if level.colored_gem is not None)
RACE_GEM_LEVELS: tuple[Level, ...] = tuple(level for level in SECRET_LEVELS if level.race_gem)

assert len(MAIN_LEVELS) == WARP_ROOMS * LEVELS_PER_ROOM
assert all(sum(1 for level in MAIN_LEVELS if level.room == room) == LEVELS_PER_ROOM for room in range(1, 6))
assert [level.number for level in MAIN_LEVELS] == list(range(1, 26))
assert len(LEVEL_BY_LID) == len(LEVELS), "level IDs must be unique"
assert len(COLORED_GEM_LEVELS) == len(COLORED_GEMS)
assert len(RELIC_LEVELS) == 28  # Hot Coco and Eggipus Rex's relics come later
