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
    Level("Bone Yard", 0x0C, 4, 1, path_gem=(Gem.RED,)),
    Level("Makin' Waves", 0x19, 5, 1),
    # Warp room 2
    Level("Gee Wiz", 0x0F, 6, 2),
    Level("Hang 'em High", 0x16, 7, 2),  # the Yellow Gem is behind a secret-warp-room entrance (not in v0.1)
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
    Level("Future Frenzy", 0x1B, 19, 4),  # its second gem uses a secret-warp-room entrance (not in v0.1)
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
    # Secret warp room (relic-gated) and secret exits: not in v0.1, listed for the level-ID table
    Level("Ski Crazed", 0x21, 26, 6, Kind.SECRET),
    Level("Area 51?", 0x25, 27, 6, Kind.SECRET),
    Level("Rings of Power", 0x1F, 28, 6, Kind.SECRET),
    Level("Hot Coco", 0x27, 29, 6, Kind.SECRET),
    Level("Eggipus Rex", 0x26, 30, 6, Kind.SECRET),
)

LEVEL_BY_NAME: dict[str, Level] = {level.name: level for level in LEVELS}
LEVEL_BY_LID: dict[int, Level] = {level.lid: level for level in LEVELS}

WARP_ROOMS = 5
LEVELS_PER_ROOM = 5
MAIN_LEVELS: tuple[Level, ...] = tuple(level for level in LEVELS if level.kind == Kind.LEVEL)
BOSSES: tuple[Level, ...] = tuple(level for level in LEVELS if level.kind == Kind.BOSS)
FINAL_BOSS: Level = LEVEL_BY_NAME["Dr. N. Cortex"]
BOSS_BY_ROOM: dict[int, Level] = {level.room: level for level in LEVELS if level.is_boss}
CRYSTAL_COUNT = len(MAIN_LEVELS)
CRYSTALS_PER_BOSS = LEVELS_PER_ROOM
"""Each warp room's boss button needs that room's five crystals (VERIFY: per room, or a running total)"""


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
POWER_BY_BOSS: dict[str, Power] = {power.boss: power for power in POWERS}
ITEM_POWERS: tuple[Power, ...] = tuple(power for power in POWERS if power.boss != FINAL_BOSS.name)
"""Powers that are items. Crash Dash comes from Cortex, after the goal, so the game keeps handing it out itself."""


def powers_before_room(room: int) -> tuple[Power, ...]:
    """Powers a player has in vanilla when warp room ``room`` opens (one per boss already beaten)."""
    return tuple(POWER_BY_BOSS[BOSS_BY_ROOM[r].name] for r in range(1, room))


PATH_GEM_LEVELS: tuple[Level, ...] = tuple(level for level in MAIN_LEVELS if level.path_gem)
COLORED_GEM_LEVELS: tuple[Level, ...] = tuple(level for level in MAIN_LEVELS if level.colored_gem is not None)

assert len(MAIN_LEVELS) == WARP_ROOMS * LEVELS_PER_ROOM
assert all(sum(1 for level in MAIN_LEVELS if level.room == room) == LEVELS_PER_ROOM for room in range(1, 6))
assert [level.number for level in MAIN_LEVELS] == list(range(1, 26))
assert len(LEVEL_BY_LID) == len(LEVELS), "level IDs must be unique"
