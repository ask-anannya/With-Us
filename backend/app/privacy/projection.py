"""Per-viewer projection.

Every response about the household is built here. Other members' data is
reduced to a whitelist. Private tables (reasons, instructions, proposals,
exclusions, chats, quest logs) are never read in this module. The mother's
quest progress is shown in detail only to the people she chose to share with.
"""
from sqlmodel import Session, select

from ..models import Household, Limit, Member, MotherSharing, Responsibility, RestWindow

RESP_FIELDS = ("id", "title", "kind", "work_kind", "days", "start", "end", "hours_per_occurrence",
               "travel", "source", "source_line", "schedule", "icon", "active", "outside_help")


def resp_public(r: Responsibility) -> dict:
    return {k: getattr(r, k) for k in RESP_FIELDS}


def member_public(s: Session, h: Household, m: Member) -> dict:
    """What anyone in the household may see about member m."""
    limits = s.exec(select(Limit).where(Limit.member_id == m.id).order_by(Limit.id)).all()
    out = {
        "id": m.id, "name": m.name, "role": m.role, "colour": m.colour,
        "capacity_hours": m.capacity_hours, "is_mother": m.id == h.mother_member_id,
        "limits": [{"opaque_id": l.opaque_id, "kind": l.kind, "value": l.value} for l in limits],
    }
    if m.id == h.mother_member_id:
        rests = s.exec(select(RestWindow).where(RestWindow.member_id == m.id)).all()
        out["resting"] = [{"days": r.days, "start": r.start, "end": r.end, "label": "Resting"} for r in rests]
    return out


def project(viewer: Member, s: Session, h: Household, kind: str, data):
    """Single entry point used by routes for household-facing payloads."""
    if kind == "member":
        return member_public(s, h, data)
    if kind == "members":
        return [member_public(s, h, m) for m in data]
    if kind == "responsibility":
        return resp_public(data)
    if kind == "responsibilities":
        return [resp_public(r) for r in data]
    raise ValueError(kind)


def can_see_progress(s: Session, h: Household, viewer: Member) -> bool:
    if viewer.id == h.mother_member_id:
        return True
    ms = s.get(MotherSharing, h.id)
    return bool(ms and ms.share_progress and viewer.id in (ms.share_with or []))
