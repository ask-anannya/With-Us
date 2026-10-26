"""Intake reader: turns the speaker's own free text into suggested form fields.
Sees only that text. Anything that sounds like a reason goes to private_reason."""
from pydantic import BaseModel, Field

from ..engine.weights import WEEKDAYS, WORK_KINDS
from .client import generate_json

SYSTEM = f"""You help one family member fill in a private form about what they can take on while a new
mother in their household recovers. Read only their own words and fill the fields.
- capacity_hours: hours per week they can give (0 to 40). If they don't say, estimate conservatively.
- blocked_days: days they can't help. Use only these codes: {", ".join(WEEKDAYS)}.
- blocked_work_kinds: kinds of work they can't do. Use only: {", ".join(WORK_KINDS)}.
- will_take: kinds of work they offered to do, same list.
- private_reason: WHY they have limits, in their own words, trimmed. Never put reasons in other fields.
Return JSON only."""


class IntakeFields(BaseModel):
    capacity_hours: float = Field(ge=0, le=40)
    blocked_days: list[str] = []
    blocked_work_kinds: list[str] = []
    will_take: list[str] = []
    private_reason: str = ""


def read(text: str) -> dict | None:
    out = generate_json(SYSTEM, [text], IntakeFields)
    if not out:
        return None
    return {
        "capacity_hours": max(0, min(40, round(out.capacity_hours))),
        "blocked_days": [d for d in out.blocked_days if d in WEEKDAYS],
        "blocked_work_kinds": [k for k in out.blocked_work_kinds if k in WORK_KINDS],
        "will_take": [k for k in out.will_take if k in WORK_KINDS],
        "private_reason": out.private_reason.strip(),
    }
