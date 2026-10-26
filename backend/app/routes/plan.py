from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from ..ai import say_for_me
from ..auth import current_member, household_of, require_mother_or_partner
from ..db import get_session
from ..models import (Announcement, Decision, Exclusion, Member, PrivateReason, Proposal,
                      Responsibility)
from ..planning import latest_plan, members_of, publish, replan, sharing_ready, week_of
from ..privacy import guard
from ..privacy.projection import member_public, resp_public

router = APIRouter(prefix="/api")


def plan_view(s: Session, h, viewer: Member) -> dict:
    members = members_of(s, h)
    names = {m.id: m.name for m in members}
    if not sharing_ready(h):
        return {"ready": False, "sharing": {"mother": h.sharing_ok_mother, "partner": h.sharing_ok_partner}}
    plan = latest_plan(s, h)
    if not plan:
        plan = publish(s, h, [])
        s.commit()
    resps = {r.id: r for r in s.exec(select(Responsibility).where(Responsibility.household_id == h.id)).all()}
    burden = {b["member_id"]: b for b in plan.burden_json}
    outside = [resp_public(r) for r in resps.values()
               if r.outside_help and r.active and (h.cold or not r.cold_only)]
    return {
        "ready": True,
        "week": plan.week, "version": plan.version, "published_at": plan.published_at.isoformat(),
        "headline": plan.headline, "spread": plan.spread,
        "members": [{**member_public(s, h, m), **{k: burden.get(m.id, {}).get(k, 0)
                                                  for k in ("burden_pct", "hours", "tasks")}}
                    for m in members],
        "assignments": [{"responsibility": resp_public(resps[a["responsibility_id"]]),
                         "member_id": a["member_id"], "member_name": names.get(a["member_id"], "")}
                        for a in plan.assignments_json if a["responsibility_id"] in resps],
        "arranging": [resp_public(resps[rid]) for rid in plan.arranging_json if rid in resps],
        "unassigned": [{"responsibility": resp_public(resps[u["responsibility_id"]]), "hours": u["hours"]}
                       for u in plan.unassigned_json if u["responsibility_id"] in resps],
        "outside_help": outside,
    }


@router.get("/plan")
def get_plan(me: Member = Depends(current_member), s: Session = Depends(get_session)):
    h = household_of(s, me)
    return plan_view(s, h, me)


@router.post("/plan/replan")
def do_replan(me: Member = Depends(current_member), s: Session = Depends(get_session)):
    h = household_of(s, me)
    if not sharing_ready(h):
        raise HTTPException(409, "Both the mother and the partner need to turn on sharing first.")
    replan(s, h)
    return plan_view(s, h, me)


def my_proposals(s: Session, h, me: Member) -> list:
    rows = s.exec(select(Proposal).where(Proposal.member_id == me.id, Proposal.week == week_of(h),
                                         Proposal.status == "pending").order_by(Proposal.id)).all()
    out = []
    for p in rows:
        r = s.get(Responsibility, p.responsibility_id)
        if r and r.active and not r.outside_help and (h.cold or not r.cold_only):
            out.append({"id": p.id, "responsibility": resp_public(r), "status": p.status})
    return out


@router.get("/me/proposals")
def get_my_proposals(me: Member = Depends(current_member), s: Session = Depends(get_session)):
    h = household_of(s, me)
    return my_proposals(s, h, me)


def _mine(s: Session, me: Member, pid: int) -> Proposal:
    p = s.get(Proposal, pid)
    if not p or p.member_id != me.id or p.status != "pending":
        raise HTTPException(404, "That request isn't waiting on you.")
    return p


@router.post("/me/proposals/{pid}/accept")
def accept(pid: int, me: Member = Depends(current_member), s: Session = Depends(get_session)):
    h = household_of(s, me)
    p = _mine(s, me, pid)
    p.status = "accepted"
    s.add(p)
    s.commit()
    replan(s, h)
    return {"ok": True}


class DeclineBody(BaseModel):
    tell_family: bool = False


@router.post("/me/proposals/{pid}/decline")
def decline(pid: int, body: DeclineBody, me: Member = Depends(current_member), s: Session = Depends(get_session)):
    h = household_of(s, me)
    p = _mine(s, me, pid)
    p.status = "declined"
    s.add(p)
    s.add(Exclusion(member_id=me.id, responsibility_id=p.responsibility_id, week=p.week))
    s.commit()
    announcement = None
    if body.tell_family:
        r = s.get(Responsibility, p.responsibility_id)
        line = say_for_me.write(me.name.split(" ")[0], r.title)
        own = [x.text for x in s.exec(select(PrivateReason).where(PrivateReason.member_id == me.id)).all()]
        line = guard.check(line, own, fallback=say_for_me.template(me.name.split(" ")[0], r.title))
        s.add(Announcement(household_id=h.id, from_member_id=me.id, text=line))
        s.commit()
        announcement = line
    replan(s, h)
    return {"ok": True, "announcement": announcement}


@router.get("/decisions")
def decisions(me: Member = Depends(current_member), s: Session = Depends(get_session)):
    h = household_of(s, me)
    rows = s.exec(select(Decision).where(Decision.household_id == h.id, Decision.status == "open")
                  .order_by(Decision.id)).all()
    can_drop = me.id == h.mother_member_id or me.role == "partner"
    out = []
    for d in rows:
        pl = d.payload_json
        hours = pl.get("hours", 0)
        hrs = f"{hours:g} hour{'s' if hours != 1 else ''}"
        days = ", ".join(DAY_NAMES.get(x, x) for x in pl.get("days", []))
        out.append({
            "id": d.id, "title": pl.get("title"), "hours": hours, "days": pl.get("days", []),
            "text": f"{hrs} a week still need{'s' if hours == 1 else ''} someone: {pl.get('title')} ({days}).",
            "options": (["drop"] if can_drop else []) + ["outside_help", "raise_capacity"],
            "my_capacity": me.capacity_hours,
        })
    return out


DAY_NAMES = {"Mon": "Monday", "Tue": "Tuesday", "Wed": "Wednesday", "Thu": "Thursday",
             "Fri": "Friday", "Sat": "Saturday", "Sun": "Sunday"}


class ResolveBody(BaseModel):
    option: str
    capacity_hours: float | None = None


@router.post("/decisions/{did}/resolve")
def resolve(did: int, body: ResolveBody, me: Member = Depends(current_member), s: Session = Depends(get_session)):
    h = household_of(s, me)
    d = s.get(Decision, did)
    if not d or d.household_id != h.id or d.status != "open":
        raise HTTPException(404, "That decision is already settled.")
    r = s.get(Responsibility, d.payload_json.get("responsibility_id"))
    if body.option == "drop":
        require_mother_or_partner(h, me)
        r.active = False
        s.add(r)
    elif body.option == "outside_help":
        r.outside_help = True
        s.add(r)
    elif body.option == "raise_capacity":
        if body.capacity_hours is None or body.capacity_hours <= me.capacity_hours:
            raise HTTPException(400, "Choose a capacity higher than your current one.")
        me.capacity_hours = min(60, body.capacity_hours)
        s.add(me)
    else:
        raise HTTPException(400, "Unknown option.")
    if body.option != "raise_capacity":
        d.status = "resolved"
        d.resolved_option = body.option
        s.add(d)
    s.commit()
    replan(s, h)
    return {"ok": True}
