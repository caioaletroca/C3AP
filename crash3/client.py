"""BizHawk client for Crash Bandicoot 3: Warped (PS1, NTSC-U).

All game logic lives in ``watcher.py``; this module only talks to BizHawk and the server.
"""
import logging
from collections import Counter
from typing import TYPE_CHECKING, Any

from NetUtils import ClientStatus
import worlds._bizhawk as bizhawk
from worlds._bizhawk.client import BizHawkClient

from . import ram, trap
from .items import APPLIED_IN_HUB, GAME_NAME, NO_LIVES_TRAP, item_name_to_id
from .trap import TrapState
from .watcher import SlotInfo, Watcher

if TYPE_CHECKING:
    from worlds._bizhawk.context import BizHawkClientContext

logger = logging.getLogger("Client")

ITEM_ID_TO_NAME = {item_id: name for name, item_id in item_name_to_id.items()}

SERIAL_MARKERS = (b"SCUS_942.44", b"SCUS-94244")
"""Boot executable name; the BIOS leaves SYSTEM.CNF's BOOT line in kernel RAM"""
SERIAL_KNOWN_OFFSETS: tuple[int, ...] = (0x0092A4, 0x009E19, 0x00B8B7)  # OK: found in BizHawk
SERIAL_SCAN_SIZE = 0x20000
SERIAL_SCAN_CHUNK = 0x4000
"""The connector returns one line per reply and asyncio caps a line at 64 KiB (base64 included), so read in chunks"""
KNOWN_HASHES: frozenset[str] = frozenset()
"""BizHawk disc hashes of verified NTSC-U dumps. Filled in as people report them."""


def contains_serial(data: bytes) -> bool:
    return any(marker in data for marker in SERIAL_MARKERS)


async def find_serial(ctx: "BizHawkClientContext") -> bool:
    """Look for the disc ID: first at the known offsets, then a chunked scan of the first 128 KiB."""
    width = max(len(marker) for marker in SERIAL_MARKERS)
    known = await bizhawk.read(ctx.bizhawk_ctx, [(address, width, ram.DOMAIN) for address in SERIAL_KNOWN_OFFSETS])
    if any(contains_serial(block) for block in known):
        return True
    for start in range(0, SERIAL_SCAN_SIZE, SERIAL_SCAN_CHUNK):
        # overlap each chunk by the marker width so an ID split across two chunks is still found
        block = (await bizhawk.read(ctx.bizhawk_ctx, [(start, SERIAL_SCAN_CHUNK + width, ram.DOMAIN)]))[0]
        if contains_serial(block):
            return True
    return False


def _filler_key(ctx: "BizHawkClientContext") -> str:
    return f"C3AP_filler_applied_{ctx.team}_{ctx.slot}"


def _trap_key(ctx: "BizHawkClientContext") -> str:
    return f"C3AP_trap_{ctx.team}_{ctx.slot}"


async def _store(ctx: "BizHawkClientContext", key: str, value: Any) -> None:
    ctx.stored_data[key] = value  # local copy until the server echoes the update
    await ctx.send_msgs([{
        "cmd": "Set", "key": key, "default": None, "want_reply": False,
        "operations": [{"operation": "replace", "value": value}],
    }])


async def _write_word(ctx: "BizHawkClientContext", address: int, value: int, guard: int) -> bool:
    return await bizhawk.guarded_write(
        ctx.bizhawk_ctx,
        [(ram.offset(address), ram.word_bytes(value), ram.DOMAIN)],
        [(ram.offset(address), ram.word_bytes(guard), ram.DOMAIN)],
    )


class Crash1Client(BizHawkClient):
    game = GAME_NAME
    system = "PSX"
    patch_suffix = None

    def __init__(self) -> None:
        super().__init__()
        self.watcher: Watcher | None = None
        self.sent: set[int] = set()
        self.goal_sent = False
        self.notify_set = False

    async def validate_rom(self, ctx: "BizHawkClientContext") -> bool:
        try:
            rom_hash = await bizhawk.get_hash(ctx.bizhawk_ctx)
            # No caching of misses: during the BIOS intro the ID isn't in RAM yet.
            if rom_hash not in KNOWN_HASHES and not await find_serial(ctx):
                return False
                logger.info(f"Crash Bandicoot 3 NTSC-U detected (disc hash {rom_hash}, not in the verified list).")
        except bizhawk.RequestFailedError:
            return False

        ctx.game = self.game
        ctx.items_handling = 0b111  # every item comes from the server, including our own
        ctx.want_slot_data = True
        ctx.watcher_timeout = 0.1   # fast enough to redirect a level load
        self.watcher = None
        self.sent.clear()
        self.goal_sent = False
        self.notify_set = False
        return True

    def on_package(self, ctx: "BizHawkClientContext", cmd: str, args: dict) -> None:
        if cmd == "Connected":
            self.watcher = None  # rebuilt from the new slot data
            self.sent.clear()
            self.goal_sent = False
            self.notify_set = False

    async def game_watcher(self, ctx: "BizHawkClientContext") -> None:
        if ctx.server is None or ctx.server.socket.closed or ctx.slot_data is None:
            return

        if self.watcher is None:
            self.watcher = Watcher(SlotInfo.from_slot_data(ctx.slot_data))
            await ctx.update_death_link(bool(ctx.slot_data.get("death_link", False)))
        if not self.notify_set:
            ctx.set_notify(_filler_key(ctx), _trap_key(ctx))
            self.notify_set = True

        try:
            globals_block, scene_block = await bizhawk.read(ctx.bizhawk_ctx, ram.read_requests())
            snap = ram.parse(globals_block, scene_block)

            received = Counter(ITEM_ID_TO_NAME.get(item.item, "") for item in ctx.items_received)
            checked = ctx.checked_locations | self.sent
            actions = self.watcher.step(snap, received, checked)

            if actions.writes:
                await bizhawk.guarded_write(
                    ctx.bizhawk_ctx,
                    [(ram.offset(address), ram.field_bytes(value, size), ram.DOMAIN)
                     for address, (value, size) in actions.writes.items()],
                    [(ram.offset(address), ram.field_bytes(value, size), ram.DOMAIN)
                     for address, (value, size) in actions.guards.items()],
                )

            if actions.reload_hub:
                logger.info("Crystals changed in the warp room: reloading it so its buttons match.")

            new_locations = actions.locations - checked
            if new_locations:
                self.sent |= new_locations
                await ctx.check_locations(new_locations)

            if actions.died and "DeathLink" in ctx.tags:
                await ctx.send_death(f"{ctx.player_names[ctx.slot]} lost a life.")

            if actions.goal and not self.goal_sent and not ctx.finished_game:
                await ctx.send_msgs([{"cmd": "StatusUpdate", "status": ClientStatus.CLIENT_GOAL}])
                self.goal_sent = True
                ctx.finished_game = True

            if await self._advance_trap(ctx, snap):
                return  # lives were just restored; filler waits for the next poll
            if actions.can_apply_filler:
                await self._apply_filler(ctx, snap)
        except bizhawk.RequestFailedError:
            pass  # emulator busy or disconnected; try again next poll

    async def _advance_trap(self, ctx: "BizHawkClientContext", snap: ram.Snapshot) -> bool:
        """Track an active No Lives Trap; returns True if this poll restored the lives."""
        key = _trap_key(ctx)
        if key not in ctx.stored_data:
            return False  # not loaded yet
        state = TrapState.from_json(ctx.stored_data[key])
        new_state, restore = trap.advance(state, snap)
        if restore is not None:
            if not await _write_word(ctx, ram.LIFE_COUNT, restore, snap.lives):
                return False
            logger.info(f"No Lives Trap over: {restore // ram.UNIT} lives.")
        if new_state != state:
            await _store(ctx, key, None if new_state is None else new_state.to_json())
        return restore is not None

    async def _apply_filler(self, ctx: "BizHawkClientContext", snap: ram.Snapshot) -> None:
        """Apply the next filler item or trap not yet applied. The count lives in data storage so it survives restarts."""
        key = _filler_key(ctx)
        if key not in ctx.stored_data or _trap_key(ctx) not in ctx.stored_data:
            return  # not loaded yet
        applied = int(ctx.stored_data[key] or 0)
        fillers = [name for item in ctx.items_received
                   if (name := ITEM_ID_TO_NAME.get(item.item)) in APPLIED_IN_HUB]
        if applied >= len(fillers):
            return

        name = fillers[applied]
        if name == NO_LIVES_TRAP:
            state, lives = trap.spring(TrapState.from_json(ctx.stored_data[_trap_key(ctx)]), snap)
            if lives is not None:
                if not await _write_word(ctx, ram.LIFE_COUNT, lives, snap.lives):
                    return
                await _store(ctx, _trap_key(ctx), state.to_json())
                logger.info("No Lives Trap! 0 lives for the next level.")
        else:
            if name == "Extra Life":
                address, value, guard = ram.LIFE_COUNT, min(snap.lives + ram.UNIT, ram.MAX_LIVES), snap.lives
            else:  # Aku Aku Mask
                address, value, guard = ram.HEALTH, min(snap.health + ram.UNIT, ram.MAX_HEALTH), snap.health
            if not await _write_word(ctx, address, value, guard):
                return
        await _store(ctx, key, applied + 1)
