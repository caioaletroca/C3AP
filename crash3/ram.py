"""RAM map for Crash Bandicoot 3: Warped (PS1, NTSC-U SCUS-94244).

Addresses are PS1 virtual addresses (0x80xxxxxx); BizHawk's "MainRAM" domain is offset by 0x80000000.
Comments say OK (confirmed in BizHawk, see tools/VERIFY.md), GS (GameShark code lists agree), DECOMP
(SomeoneIsWorking/crash3-decomp notes) or VERIFY (a hypothesis).

The GOOL globals block starts at 0x80068EF8 (DECOMP: GOOL reads globals from *(0x1F800058)). Its first slots line up
with Crash 1's (LIFECOUNT and HEALTH sit at Crash 1's indices 24 and 25), so the other early slots are guessed from
Crash 1's layout (esplonky/c1 globals.h): respawn_count = index 5, game_state = index 17, fruit_count = index 26.
Values in the globals are fixed point (<< 8) like Crash 1's.
"""
import struct
from dataclasses import dataclass

DOMAIN = "MainRAM"
RAM_BASE = 0x80000000


def offset(address: int) -> int:
    """Convert a PS1 virtual address into a MainRAM offset."""
    return address - RAM_BASE


# GOOL globals (4 bytes each)
GLOBALS_START = 0x80068EF8
LEVEL = 0x80068EF8             # OK: current level ID << 8 (index 0); follows SCENE_ID ~345 frames later
RESPAWN_COUNT = 0x80068F0C     # OK: index 5, +0x100 per respawn, back to 0 in the warp room
GAMESTATE = 0x80068F3C         # OK: index 17, see GAMESTATE_* below
LIFE_COUNT = 0x80068F58        # OK: lives << 8 (index 24); the level writes it back on exit, warp room writes carry in
HEALTH = 0x80068F5C            # OK: Aku Aku masks << 8 (index 25); same as lives (writes inside a level are lost)
FRUIT_COUNT = 0x80068F60       # OK: index 26, synced on level exit
LEVELS_COMPLETED = 0x80068F64  # OK: index 27, bit = level ID, set back in the warp room after a normal finish
                               # (Tiny = bit 6, High Time = bit 26); a boss's bit opens the next room's fence
HUB_AREA = 0x80068FA4          # ❌ index 43 was 0x13 in room 1, 0x14 in room 2, but it changes too often (not the room)
GEMS = 0x80068FB0              # OK: gem bitfield, 8 bytes; set in the warp room ~200 frames after the level
CRYSTALS = 0x8006912C          # OK: crystal bitfield, 6 bytes; set in the warp room ~200 frames after the level
POWERS = 0x80069178            # GS: power bitmask (all powers = 0x3F)
SAPPHIRE_RELICS = 0x800691B4   # GS: sapphire relic bitfield, 6 bytes (not read yet; gold/platinum likely follow)
GLOBALS_END = POWERS + 4
GLOBALS_SIZE = GLOBALS_END - GLOBALS_START

# Engine state (DECOMP)
SCENE_BLOCK = 0x80060ABC
SCENE_ID = 0x80060ABC          # DECOMP: the scene (level) the loader last loaded
SCENE_REQUEST = 0x80060AC0     # DECOMP: -1 = idle, else the frame loop loads that scene; reset to -1 by the load
                               # OK: a button's request lasts 3 frames
SCENE_BLOCK_SIZE = 8

# Values
NO_SCENE = 0xFFFFFFFF
LID_WARP_ROOM = 0x02           # OK: the warp room hub
LID_TITLE = 0x3C               # DECOMP: boot sits here
LID_TRANSITION = 0x3A          # OK: a scene between the warp room and a level (not always used)
GAMESTATE_LOADING = 0x000      # OK: level start and respawn
GAMESTATE_PLAYING = 0x100      # OK: in a level and in the warp room
GAMESTATE_GAME_OVER = 0x200    # VERIFY (Crash 1's value)
GAMESTATE_LEVEL_DONE = 0x300   # OK: normal level exit
GAMESTATE_QUIT = 0x400         # OK: exit through the pause menu

HUB_AREA_ROOM_1: int | None = None
"""Area value of warp room 1: unknown (HUB_AREA was a wrong guess), so the client always assumes the worst"""

UNIT = 0x100
MAX_HEALTH = 2 * UNIT          # VERIFY: two masks; a third gives temporary invincibility
MAX_LIVES = 99 * UNIT

# Bits. Crystal and box-gem bits are indexed by level ID: OK for Toad Village (bit 11 in both), the rest VERIFY.
# Bits that are not known yet are None; the client then neither writes nor watches them.
CRYSTAL_BIT_BY_LID: dict[int, int] = {}      # filled below: bit = level ID (VERIFY)
CLEAR_GEM_BIT_BY_LID: dict[int, int] = {}    # filled below: bit = level ID (VERIFY)
PATH_GEM_BIT_BY_LID: dict[int, int | None] = {}
"""Second (gem path) clear gem of Bone Yard, Tomb Time, Dino Might!, Sphynxinator, Gone Tomorrow, Bug Lite: unknown"""
COLORED_GEM_BITS: dict[str, int | None] = {"Red": None, "Green": None, "Purple": 60, "Blue": None, "Yellow": None}
"""Bit in GEMS of each colored gem: Purple OK (High Time), the rest unknown (watch GEMS in tools/c3ap_ram_watch.lua)"""


def _fill_level_bits() -> None:
    from .data import MAIN_LEVELS, PATH_GEM_LEVELS
    for level in MAIN_LEVELS:
        CRYSTAL_BIT_BY_LID[level.lid] = level.lid
        CLEAR_GEM_BIT_BY_LID[level.lid] = level.lid
    for level in PATH_GEM_LEVELS:
        PATH_GEM_BIT_BY_LID[level.lid] = None


_fill_level_bits()


@dataclass(frozen=True)
class Snapshot:
    level: int
    """Current level ID (LEVEL >> 8)"""
    gamestate: int
    respawn_count: int
    lives: int
    health: int
    gems: int
    """64-bit gem field"""
    crystals: int
    """48-bit crystal field"""
    powers: int
    scene_id: int
    scene_request: int
    hub_area: int = 0
    levels_completed: int = 0

    @property
    def in_hub(self) -> bool:
        return self.level == LID_WARP_ROOM

    @property
    def warp_room(self) -> int | None:
        """Warp room (1-5) Crash stands in, or None when unknown"""
        if HUB_AREA_ROOM_1 is None:
            return None
        room = self.hub_area - HUB_AREA_ROOM_1 + 1
        return room if self.in_hub and 1 <= room <= 5 else None

    @property
    def hub_loading_or_in(self) -> bool:
        """The warp room is loaded or loading (SCENE_ID switches ~345 frames before LEVEL)"""
        return self.level == LID_WARP_ROOM or self.scene_id == LID_WARP_ROOM

    @property
    def hub_ready(self) -> bool:
        """Fully in the warp room, nothing loading: safe to ask for a reload"""
        return (self.level == LID_WARP_ROOM and self.scene_id == LID_WARP_ROOM and self.gamestate == GAMESTATE_PLAYING
                and self.scene_request == NO_SCENE)

    @property
    def on_title(self) -> bool:
        return self.level == LID_TITLE


def read_requests() -> list[tuple[int, int, str]]:
    return [
        (offset(GLOBALS_START), GLOBALS_SIZE, DOMAIN),
        (offset(SCENE_BLOCK), SCENE_BLOCK_SIZE, DOMAIN),
    ]


def _word(block: bytes, block_start: int, address: int) -> int:
    return struct.unpack_from("<I", block, address - block_start)[0]


def _bytes_le(block: bytes, block_start: int, address: int, size: int) -> int:
    start = address - block_start
    return int.from_bytes(block[start:start + size], "little")


CRYSTALS_SIZE = 6
GEMS_SIZE = 8


def parse(globals_block: bytes, scene_block: bytes) -> Snapshot:
    def g(address: int) -> int:
        return _word(globals_block, GLOBALS_START, address)

    return Snapshot(
        level=g(LEVEL) >> 8,
        gamestate=g(GAMESTATE),
        respawn_count=g(RESPAWN_COUNT),
        lives=g(LIFE_COUNT),
        health=g(HEALTH),
        gems=_bytes_le(globals_block, GLOBALS_START, GEMS, GEMS_SIZE),
        crystals=_bytes_le(globals_block, GLOBALS_START, CRYSTALS, CRYSTALS_SIZE),
        powers=g(POWERS),
        scene_id=_word(scene_block, SCENE_BLOCK, SCENE_ID),
        scene_request=_word(scene_block, SCENE_BLOCK, SCENE_REQUEST),
        hub_area=g(HUB_AREA),
        levels_completed=g(LEVELS_COMPLETED),
    )


def word_bytes(value: int) -> bytes:
    return struct.pack("<I", value & 0xFFFFFFFF)


def field_bytes(value: int, size: int) -> bytes:
    return (value & ((1 << (8 * size)) - 1)).to_bytes(size, "little")
