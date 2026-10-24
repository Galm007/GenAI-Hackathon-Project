from typing import Literal

from pydantic import BaseModel

Speaker = Literal["advocate", "chair"]
Recommendation = Literal["ADMIT", "LIKELY ADMIT", "WAITLIST", "LIKELY DENY", "DENY"]


class Citation(BaseModel):
    kind: Literal["dossier", "cds", "twin", "web", "model", "sql"]
    ref: str
    valid: bool
    span: tuple[int, int]                          # char offsets in content, for UI chip placement


class DebateTurn(BaseModel):
    turn: int
    speaker: Speaker
    content: str
    citations: list[Citation]
    recommendation: Recommendation | None = None   # chair's closing turn only
    degraded: bool = False                         # True if the template fallback was used
