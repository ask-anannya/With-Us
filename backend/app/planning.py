"""Bridges the database and the engine, and runs the consent flow.

The engine's draft is never returned by any endpoint. It only becomes private
proposals; the household sees accepted work plus "Being arranged".
"""
from sqlmodel import Session, select

from .engine import weights as W
from .engine.headline import headline
from .engine.solver import EMember, EResp, solve
from .models import (Activity, Decision, Exclusion, Household, Limit, Member, Plan,
                     Proposal, Responsibility, RestWindow, now)


def week_of(h: Household) -> str:
    return h.week_start


def members_of(s: Session, h: Household) -> list:
    return s.exec(select(Member).where(Member.household_id == h.id).order_by(Member.id)).all()


def active_resps(s: Session, h: Household) -> list:
    rows = s.exec(select(Responsibility).where(Responsibility.household_id == h.id,
                                               Responsibility.active == True,  # noqa: E712
                                               Responsibility.outside_help == False)  # noqa: E712
                  .order_by(Responsibility.id)).all()
    return [r for r in rows if h.cold or not r.cold_only]


def to_emember(s: Session, h: Household, m: Member) -> EMember:
    limits = s.exec(select(Limit).where(Limit.member_id == m.id)).all()
    rests = s.exec(select(RestWindow).where(RestWindow.member_id == m.id)).all()
    return EMember(
        id=m.id, name=m.name, capacity_hours=m.capacity_hours,
        is_mother=(m.id == h.mother_member_id),
        blocked_days={l.value for l in limits if l.kind == "day"},
        blocked_kinds={l.value for l in limits if l.kind == "work_kind"},
        rest_windows=[(r.days, r.start, r.end) for r in rests],
    )


def to_eresp(r: Responsibility) -> EResp:
    return EResp(id=r.id, title=r.title, kind=r.kind, work_kind=r.work_kind, days=list(r.days),
                 hours_per_occurrence=r.hours_per_occurrence, start=r.start, end=r.end,
                 travel=r.travel, fixed_owner_id=r.fixed_owner_id)


def sharing_ready(h: Household) -> bool:
    return h.sharing_ok_mother and h.sharing_ok_partner


def log(s: Session, h: Household, text: str = "Plan updated") -> None:
    s.add(Activity(household_id=h.id, text=text))


def replan(s: Session, h: Household, note_activity: bool = True) -> Plan | None:
    """Re-run the engine on open items, refresh private proposals and shortfall
    decisions, and publish the household plan."""
    if not sharing_ready(h):
        return None
    week = week_of(h)
    members = members_of(s, h)
    resps = active_resps(s, h)
    resp_ids = {r.id for r in resps}
    excluded = {(e.member_id, e.responsibility_id)
                for e in s.exec(select(Exclusion).where(Exclusion.week == week)).all()}
    proposals = s.exec(select(Proposal).where(Proposal.week == week)).all()
    proposals = [p for p in proposals if p.responsibility_id in resp_ids]
    locked = {p.responsibility_id: p.member_id for p in proposals if p.status == "accepted"}

    result = solve([to_emember(s, h, m) for m in members], [to_eresp(r) for r in resps],
                   excluded=excluded, locked=locked)

    # proposals: one pending per open assignment; withdraw ones that moved
    pending = {p.responsibility_id: p for p in proposals if p.status == "pending"}
    for rid, mid in result.assignments.items():
        if rid in locked:
            continue
        p = pending.get(rid)
        if p and p.member_id == mid:
            continue
        if p:
            p.status = "withdrawn"
            s.add(p)
        s.add(Proposal(responsibility_id=rid, member_id=mid, week=week))
    for rid, p in pending.items():
        if rid not in result.assignments:
            p.status = "withdrawn"
            s.add(p)

    # shortfall decisions: one per item nobody can take, no names of decliners
    by_id = {r.id: r for r in resps}
    unassigned_ids = {rid for rid, _ in result.unassigned}
    open_decisions = s.exec(select(Decision).where(Decision.household_id == h.id,
                                                   Decision.status == "open")).all()
    have = {d.payload_json.get("responsibility_id"): d for d in open_decisions}
    for rid, hours in result.unassigned:
        if rid not in have:
            r = by_id[rid]
            s.add(Decision(household_id=h.id, payload_json={
                "responsibility_id": rid, "title": r.title, "hours": round(hours, 1),
                "days": list(r.days), "work_kind": r.work_kind}))
    for rid, d in have.items():
        if rid not in unassigned_ids:
            d.status = "resolved"
            d.resolved_option = "covered"
            s.add(d)

    s.flush()
    plan = publish(s, h, result.unassigned)
    if note_activity:
        log(s, h)
    s.commit()
    return plan


def publish(s: Session, h: Household, unassigned: list) -> Plan:
    """The published plan holds accepted work only. Burden is measured on it."""
    week = week_of(h)
    members = members_of(s, h)
    resps = {r.id: r for r in active_resps(s, h)}
    proposals = s.exec(select(Proposal).where(Proposal.week == week)).all()
    accepted = [p for p in proposals if p.status == "accepted" and p.responsibility_id in resps]
    arranging = sorted({p.responsibility_id for p in proposals
                        if p.status == "pending" and p.responsibility_id in resps})
    mother = next((m for m in members if m.id == h.mother_member_id), None)

    load = {m.id: 0.0 for m in members}
    hours = {m.id: 0.0 for m in members}
    tasks = {m.id: 0 for m in members}
    assignments = []
    for p in sorted(accepted, key=lambda p: p.responsibility_id):
        r = resps[p.responsibility_id]
        if r.kind == "recovery":
            continue
        load[p.member_id] += W.weight(r.hours_per_occurrence, r.days, r.work_kind, r.travel)
        hours[p.member_id] += W.hours_per_week(r.hours_per_occurrence, r.days)
        tasks[p.member_id] += 1
        assignments.append({"responsibility_id": r.id, "member_id": p.member_id})

    burden = {}
    for m in members:
        cap = W.effective_capacity(m.capacity_hours, m.id == h.mother_member_id)
        burden[m.id] = W.burden(load[m.id], cap)
    counted = [burden[m.id] for m in members if m.capacity_hours > 0 and m.id != h.mother_member_id]
    spread = (max(counted) - min(counted)) * 100 if counted else 0.0
    names = {m.id: m.name for m in members}
    unassigned_hours = sum(hh for _, hh in unassigned)

    prev = s.exec(select(Plan).where(Plan.household_id == h.id).order_by(Plan.version.desc())).first()
    plan = Plan(
        household_id=h.id, week=week, version=(prev.version + 1 if prev else 1), published_at=now(),
        assignments_json=assignments,
        burden_json=[{"member_id": m.id, "burden_pct": round(burden[m.id] * 100),
                      "hours": round(hours[m.id], 1), "tasks": tasks[m.id]} for m in members],
        unassigned_json=[{"responsibility_id": rid, "hours": round(hh, 1)} for rid, hh in unassigned],
        arranging_json=arranging,
        spread=round(spread, 1),
        headline=headline(mother.name if mother else "Her", {k: v for k, v in burden.items()
                                                             if k != h.mother_member_id},
                          names, spread, unassigned_hours, h.tolerance_points),
    )
    s.add(plan)
    return plan


def latest_plan(s: Session, h: Household) -> Plan | None:
    return s.exec(select(Plan).where(Plan.household_id == h.id).order_by(Plan.version.desc())).first()


def owner_of(s: Session, h: Household, resp_id: int) -> int | None:
    p = s.exec(select(Proposal).where(Proposal.week == week_of(h), Proposal.responsibility_id == resp_id,
                                      Proposal.status == "accepted")).first()
    return p.member_id if p else None
