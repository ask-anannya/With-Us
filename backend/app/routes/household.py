import re
import secrets
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel
from sqlmodel import Session, select

from .. import settings
from ..auth import (current_member, end_session, find_member, household_of,
                    require_mother_or_partner, start_session)
from ..db import get_session
from ..models import Activity, Announcement, Household, Member, MotherSharing, Responsibility
from ..planning import log, members_of, replan, sharing_ready
from ..privacy.projection import project

router = APIRouter(prefix="/api")

COLOURS = ["--m1", "--m2", "--m3", "--m4"]
ROLES = {"mother", "partner", "parent", "relative", "helper"}


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "member"


def unique_slug(s: Session, h: Household, name: str) -> str:
    base = slugify(name)
    slug, n = base, 2
    while find_member(s, h, slug):
        slug, n = f"{base}{n}", n + 1
    return slug


def add_member(s: Session, h: Household, name: str, role: str, capacity: float = 0) -> Member:
    count = len(members_of(s, h))
    m = Member(household_id=h.id, slug=unique_slug(s, h, name), name=name.strip(), role=role,
               capacity_hours=capacity, colour=COLOURS[count % len(COLOURS)])
    s.add(m)
    s.commit()
    s.refresh(m)
    return m


def weeks_since(arrived: str) -> int | None:
    try:
        d = date.fromisoformat(arrived)
    except ValueError:
        return None
    return max(1, (date.today() - d).days // 7 + 1)


def household_summary(s: Session, h: Household, viewer: Member) -> dict:
    members = members_of(s, h)
    mother = next((m for m in members if m.id == h.mother_member_id), None)
    return {
        "code": h.code, "baby_type": h.baby_type, "baby_name": h.baby_name,
        "week_start": h.week_start, "cold": h.cold, "demo": settings.DEMO_MODE,
        "mother": {"id": mother.id, "name": mother.name,
                   "week": weeks_since(h.baby_arrived) or 2} if mother else None,
        "notes": h.notes,
        "members": project(viewer, s, h, "members", members),
        "sharing": {"mother": h.sharing_ok_mother, "partner": h.sharing_ok_partner,
                    "ready": sharing_ready(h)},
        "has_partner": any(m.role == "partner" for m in members),
    }


class CreateBody(BaseModel):
    baby_type: str
    mother_name: str
    baby_name: str = ""
    baby_arrived: str = ""
    notes: str = ""
    creator_is_mother: bool = True
    creator_name: str = ""
    creator_role: str = "partner"


@router.post("/households")
def create_household(body: CreateBody, response: Response, s: Session = Depends(get_session)):
    if body.baby_type not in ("girl", "boy"):
        raise HTTPException(400, "Choose baby girl or baby boy.")
    if not body.mother_name.strip():
        raise HTTPException(400, "Tell us who is recovering.")
    code = f"{slugify(body.mother_name)}-{secrets.randbelow(9000) + 1000}"
    today = date.today()
    h = Household(code=code, baby_type=body.baby_type, baby_name=body.baby_name.strip(),
                  baby_arrived=body.baby_arrived, notes=body.notes.strip(),
                  week_start=(today - timedelta(days=today.weekday())).isoformat())
    s.add(h)
    s.commit()
    s.refresh(h)
    mother = add_member(s, h, body.mother_name, "mother")
    h.mother_member_id = mother.id
    s.add(MotherSharing(household_id=h.id))
    s.add(h)
    s.commit()
    me = mother
    if not body.creator_is_mother:
        if not body.creator_name.strip():
            raise HTTPException(400, "Tell us your name.")
        role = body.creator_role if body.creator_role in ROLES - {"mother"} else "relative"
        me = add_member(s, h, body.creator_name, role)
    start_session(s, response, me)
    return {"code": h.code, "member_id": me.slug}


class SessionBody(BaseModel):
    code: str
    member_id: str = ""
    name: str = ""
    role: str = "relative"


@router.post("/session")
def sign_in(body: SessionBody, response: Response, s: Session = Depends(get_session)):
    h = s.exec(select(Household).where(Household.code == body.code.strip().lower())).first()
    if not h:
        raise HTTPException(404, "We couldn't find that household code.")
    m = find_member(s, h, body.member_id.strip().lower()) if body.member_id else None
    created = False
    if not m:
        if not body.name.strip():
            raise HTTPException(404, "That member ID isn't in this household. Add your name to join.")
        role = body.role if body.role in ROLES - {"mother"} else "relative"
        m = add_member(s, h, body.name, role)
        created = True
    start_session(s, response, m)
    return {"code": h.code, "member_id": m.slug, "created": created}


@router.delete("/session")
def sign_out(request: Request, response: Response, s: Session = Depends(get_session)):
    end_session(s, request, response)
    return {"ok": True}


@router.get("/demo/members")
def demo_members(code: str = "meera", s: Session = Depends(get_session)):
    if not settings.DEMO_MODE:
        raise HTTPException(404, "Demo mode is off.")
    h = s.exec(select(Household).where(Household.code == code)).first()
    if not h:
        return []
    return [{"member_id": m.slug, "name": m.name, "role": m.role} for m in members_of(s, h)]


@router.get("/demo/login")
def demo_login(member: str, next: str = "/home", code: str = "meera", s: Session = Depends(get_session)):
    """Demo mode only: sign in as a seed member by link, for recording the video."""
    from fastapi.responses import RedirectResponse

    if not settings.DEMO_MODE:
        raise HTTPException(404, "Demo mode is off.")
    h = s.exec(select(Household).where(Household.code == code)).first()
    m = find_member(s, h, member) if h else None
    if not m:
        raise HTTPException(404, "No such demo member.")
    resp = RedirectResponse(next if next.startswith("/") and not next.startswith("//") else "/home", status_code=303)
    start_session(s, resp, m)
    return resp


@router.get("/household")
def get_household(me: Member = Depends(current_member), s: Session = Depends(get_session)):
    h = household_of(s, me)
    out = household_summary(s, h, me)
    out["me"] = {"id": me.id, "member_id": me.slug, "name": me.name, "role": me.role,
                 "colour": me.colour, "is_mother": me.id == h.mother_member_id}
    return out


class SharingBody(BaseModel):
    on: bool


@router.patch("/household/sharing")
def set_sharing(body: SharingBody, me: Member = Depends(current_member), s: Session = Depends(get_session)):
    h = household_of(s, me)
    if me.id == h.mother_member_id:
        h.sharing_ok_mother = body.on
    elif me.role == "partner":
        h.sharing_ok_partner = body.on
    else:
        raise HTTPException(403, "Only the mother and partner set this switch, each their own.")
    s.add(h)
    s.commit()
    if sharing_ready(h):
        replan(s, h)
    return household_summary(s, h, me)["sharing"]


class ColdBody(BaseModel):
    on: bool


@router.post("/household/cold")
def set_cold(body: ColdBody, me: Member = Depends(current_member), s: Session = Depends(get_session)):
    """Demo variant: the baby has a cold (extra night feeds and a pediatric visit)."""
    h = household_of(s, me)
    h.cold = body.on
    s.add(h)
    s.commit()
    replan(s, h)
    return {"cold": h.cold}


@router.get("/responsibilities")
def list_resps(me: Member = Depends(current_member), s: Session = Depends(get_session)):
    h = household_of(s, me)
    rows = s.exec(select(Responsibility).where(Responsibility.household_id == h.id)
                  .order_by(Responsibility.id)).all()
    rows = [r for r in rows if h.cold or not r.cold_only]
    return project(me, s, h, "responsibilities", rows)


class RespBody(BaseModel):
    title: str
    kind: str = "home"
    work_kind: str = ""
    days: list[str] = []
    start: str | None = None
    end: str | None = None
    hours_per_occurrence: float = 1.0
    travel: bool = False


@router.post("/responsibilities")
def add_resp(body: RespBody, me: Member = Depends(current_member), s: Session = Depends(get_session)):
    h = household_of(s, me)
    if not body.title.strip() or not body.days:
        raise HTTPException(400, "Give the task a name and at least one day.")
    if body.kind not in ("baby", "home"):
        raise HTTPException(400, "Recovery items come from the doctor's discharge sheet.")
    r = Responsibility(household_id=h.id, title=body.title.strip(), kind=body.kind,
                       work_kind=body.work_kind, days=body.days, start=body.start or None,
                       end=body.end or None, hours_per_occurrence=max(0.25, body.hours_per_occurrence),
                       travel=body.travel, source="family")
    s.add(r)
    s.commit()
    s.refresh(r)
    replan(s, h) or log(s, h, "A task was added")
    s.commit()
    return project(me, s, h, "responsibility", r)


class RespPatch(BaseModel):
    active: bool | None = None
    title: str | None = None


@router.patch("/responsibilities/{rid}")
def edit_resp(rid: int, body: RespPatch, me: Member = Depends(current_member), s: Session = Depends(get_session)):
    h = household_of(s, me)
    require_mother_or_partner(h, me)
    r = s.get(Responsibility, rid)
    if not r or r.household_id != h.id:
        raise HTTPException(404, "Task not found.")
    if body.active is not None:
        r.active = body.active
    if body.title:
        r.title = body.title.strip()
    s.add(r)
    s.commit()
    replan(s, h)
    return project(me, s, h, "responsibility", r)


@router.get("/activity")
def activity(me: Member = Depends(current_member), s: Session = Depends(get_session)):
    h = household_of(s, me)
    rows = s.exec(select(Activity).where(Activity.household_id == h.id)
                  .order_by(Activity.id.desc()).limit(30)).all()
    return [{"at": a.at.isoformat(), "text": a.text} for a in rows]


@router.get("/announcements")
def announcements(me: Member = Depends(current_member), s: Session = Depends(get_session)):
    h = household_of(s, me)
    rows = s.exec(select(Announcement).where(Announcement.household_id == h.id)
                  .order_by(Announcement.id.desc()).limit(20)).all()
    names = {m.id: m.name for m in members_of(s, h)}
    return [{"at": a.at.isoformat(), "from": names.get(a.from_member_id, ""), "text": a.text} for a in rows]
