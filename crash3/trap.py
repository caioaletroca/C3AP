"""No Lives Trap: lives drop to 0 for one level, then come back.

Same design as C1AP's (verified there in BizHawk): the client only touches lives between levels, in the warp room.

1. In the warp room, the trap saves the current lives and sets them to 0 (another trap before the next level is used up
   without effect).
2. The next level is played with 0 lives: one death is a game over.
3. Back in the warp room, the saved lives are added to whatever the player has now (lives picked up in the level count).
   A game over ends the trap without restoring (VERIFY: Crash 3's game-over state).

The state is kept in the server's data storage so it survives a client restart. Pure logic, no I/O.
"""
from dataclasses import dataclass
from typing import Any

from . import ram
from .data import LEVEL_BY_LID


@dataclass(frozen=True)
class TrapState:
    saved: int
    """LIFE_COUNT (<< 8) before the trap"""
    played: bool = False
    """A level has been entered since the trap was applied"""

    def to_json(self) -> dict[str, Any]:
        return {"saved": self.saved, "played": self.played}

    @classmethod
    def from_json(cls, data: Any) -> "TrapState | None":
        if not isinstance(data, dict):
            return None
        return cls(int(data["saved"]), bool(data.get("played", False)))


def advance(state: TrapState | None, snap: ram.Snapshot) -> tuple[TrapState | None, int | None]:
    """Move the trap along. Returns the new state and, when the trap ends in the warp room, the lives to write."""
    if state is None:
        return None, None
    if snap.gamestate == ram.GAMESTATE_GAME_OVER:
        return None, None
    if not state.played and snap.level in LEVEL_BY_LID:
        return TrapState(state.saved, played=True), None
    if state.played and snap.in_hub:
        return None, min(snap.lives + state.saved, ram.MAX_LIVES)
    return state, None


def spring(state: TrapState | None, snap: ram.Snapshot) -> tuple[TrapState, int | None]:
    """A No Lives Trap received in the warp room. Returns the new state and the lives to write (None: already active)."""
    if state is not None:
        return state, None
    return TrapState(snap.lives), 0
