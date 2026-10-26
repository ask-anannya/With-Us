"""Routes under /api/me return the viewer's own private data and nothing else."""
import secrets

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from ..ai import assistant as assistant_ai
from ..ai import intake as intake_ai
from ..auth import current_member, household_of
from ..db import get_session
from ..engine.weights import MOTHER_CEILING, WEEKDAYS, WORK_KINDS
from ..models import AssistantInstructions, Limit, Member, MotherSharing, PrivateReason, RestWindow
from ..planning import members_of, replan
from ..privacy import guard
from ..privacy.projection import member_public
from .plan import my_proposals

router = APIRouter(prefix="/api")


def me_view(s: Session, h, me: Member) -> dict:
    limits = s.exec(select(Limit).where(Limit.member_id == me.id).order_by(Limit.id)).all()
    reasons = s.exec(select(PrivateReason).where(PrivateReason.member_id == me.id)).all()
    by_limit = {r.limit_id: r.text for r in reasons}
    instr = s.get(AssistantInstructions, me.id)
    is_mother = me.id == h.mother_member_id
    out = {
        "id": me.id, "member_id": me.slug, "name": me.name, "role": me.role, "colour": me.colour,
        "capacity_hours": me.capacity_hours, "is_mother": is_mother, "household_code": h.code,
        "limits": [{"id": l.id, "opaque_id": l.opaque_id, "kind": l.kind, "value": l.value,
                    "reason": by_limit.get(l.id, "")} for l in limits],
        "general_reason": by_limit.get(None, ""),
        "instructions": instr.text if instr else "",
    }
    if is_mother:
        rests = s.exec(select(RestWindow).where(RestWindow.member_id == me.id).order_by(RestWindow.id)).all()
        ms = s.get(MotherSharing, h.id)
        out["rest_windows"] = [{"days": r.days, "start": r.start, "end": r.end} for r in rests]
        out["planned_hours"] = me.capacity_hours * MOTHER_CEILING
        out["sharing"] = {"share_progress": bool(ms and ms.share_progress),
                          "share_with": list(ms.share_with) if ms else []}
    return out


@router.get("/me")
def get_me(me: Member = Depends(current_member), s: Session = Depends(get_session)):
    return me_view(s, household_of(s, me), me)


class ProfileBody(BaseModel):
    name: str | None = None
    capacity_hours: float | None = None


@router.put("/me/profile")
def put_profile(body: ProfileBody, me: Member = Depends(current_member), s: Session = Depends(get_session)):
    h = household_of(s, me)
    if body.name is not None and body.name.strip():
        me.name = body.name.strip()
    if body.capacity_hours is not None:
        me.capacity_hours = max(0.0, min(60.0, body.capacity_hours))
    s.add(me)
    s.commit()
    replan(s, h)
    return me_view(s, h, me)


class RestBody(BaseModel):
    days: list[str]
    start: str
    end: str


class LimitsBody(BaseModel):
    days: list[str] = []
    work_kinds: list[str] = []
    rest_windows: list[RestBody] | None = None


@router.put("/me/limits")
def put_limits(body: LimitsBody, me: Member = Depends(current_member), s: Session = Depends(get_session)):
    h = household_of(s, me)
    wanted = {("day", d) for d in body.days if d in WEEKDAYS}
    wanted |= {("work_kind", k) for k in body.work_kinds if k in WORK_KINDS}
    existing = s.exec(select(Limit).where(Limit.member_id == me.id)).all()
    for l in existing:
        if (l.kind, l.value) not in wanted:
            for r in s.exec(select(PrivateReason).where(PrivateReason.limit_id == l.id)).all():
                s.delete(r)
            s.delete(l)
    have = {(l.kind, l.value) for l in existing}
    for kind, value in sorted(wanted - have):
        s.add(Limit(member_id=me.id, kind=kind, value=value, opaque_id="lim_" + secrets.token_hex(4)))
    if body.rest_windows is not None:
        if me.id != h.mother_member_id:
            raise HTTPException(403, "Rest windows are for the recovering mother.")
        for r in s.exec(select(RestWindow).where(RestWindow.member_id == me.id)).all():
            s.delete(r)
        for r in body.rest_windows:
            days = [d for d in r.days if d in WEEKDAYS] or list(WEEKDAYS)
            s.add(RestWindow(member_id=me.id, days=days, start=r.start, end=r.end))
    s.commit()
    replan(s, h)
    return me_view(s, h, me)


class TextBody(BaseModel):
    text: str


@router.put("/me/reasons/{limit_id}")
def put_reason(limit_id: str, body: TextBody, me: Member = Depends(current_member), s: Session = Depends(get_session)):
    lid = None
    if limit_id != "general":
        lid = int(limit_id)
        l = s.get(Limit, lid)
        if not l or l.member_id != me.id:
            raise HTTPException(404, "That limit isn't yours.")
    row = s.exec(select(PrivateReason).where(PrivateReason.member_id == me.id,
                                             PrivateReason.limit_id == lid)).first()
    if body.text.strip():
        row = row or PrivateReason(member_id=me.id, limit_id=lid)
        row.text = body.text.strip()
        s.add(row)
    elif row:
        s.delete(row)
    s.commit()
    return {"ok": True}


@router.put("/me/instructions")
def put_instructions(body: TextBody, me: Member = Depends(current_member), s: Session = Depends(get_session)):
    row = s.get(AssistantInstructions, me.id) or AssistantInstructions(member_id=me.id)
    row.text = body.text.strip()
    s.add(row)
    s.commit()
    return {"ok": True}


class QuestSharingBody(BaseModel):
    share_progress: bool
    share_with: list[int] = []


@router.put("/me/quest-sharing")
def put_quest_sharing(body: QuestSharingBody, me: Member = Depends(current_member), s: Session = Depends(get_session)):
    h = household_of(s, me)
    if me.id != h.mother_member_id:
        raise HTTPException(403, "Only the mother shares her quest progress.")
    ids = {m.id for m in members_of(s, h)}
    row = s.get(MotherSharing, h.id) or MotherSharing(household_id=h.id)
    row.share_progress = body.share_progress
    row.share_with = [i for i in body.share_with if i in ids and i != me.id]
    s.add(row)
    s.commit()
    return {"ok": True}


@router.get("/me/what-household-sees")
def what_household_sees(me: Member = Depends(current_member), s: Session = Depends(get_session)):
    h = household_of(s, me)
    return member_public(s, h, me)


@router.get("/me/what-assistant-is-told")
def what_assistant_is_told(me: Member = Depends(current_member), s: Session = Depends(get_session)):
    h = household_of(s, me)
    ctx = assistant_ai.build_context(s, h, me, my_proposals(s, h, me))
    return {"rules": assistant_ai.RULES, "context": ctx}


class IntakeBody(BaseModel):
    text: str


@router.post("/intake/read")
def intake_read(body: IntakeBody, me: Member = Depends(current_member), s: Session = Depends(get_session)):
    if not body.text.strip():
        raise HTTPException(400, "Tell your assistant a little about your week first.")
    fields = intake_ai.read(body.text)
    if fields is None:
        return {"ok": False, "message": "Your assistant can't read that right now. The form below works just the same."}
    # The reader saw only the speaker's own text, so there is no one else's text to protect.
    fields["private_reason"] = guard.check(fields["private_reason"], [], fallback="")
    return {"ok": True, "fields": fields}
