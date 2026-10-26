"""The mother's quest map. Quest progress is private to her unless she shares it."""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..auth import current_member, household_of
from ..db import get_session
from ..engine.solver import _intervals
from ..engine.weights import WEEKDAYS
from ..models import Member, Proposal, QuestLog, Responsibility, RestWindow
from ..planning import active_resps, members_of, week_of
from ..privacy.projection import can_see_progress

router = APIRouter(prefix="/api")


def _label(hhmm: str | None) -> str:
    if not hhmm:
        return ""
    h, m = map(int, hhmm.split(":"))
    suffix = "am" if h < 12 else "pm"
    h12 = h % 12 or 12
    return f"{h12} {suffix}" if m == 0 else f"{h12}:{m:02d} {suffix}"


def _minutes(hhmm: str | None, default: int = 600) -> int:
    if not hhmm:
        return default
    h, m = map(int, hhmm.split(":"))
    return h * 60 + m


def todays_quests(s: Session, h, today: date | None = None) -> list:
    today = today or date.today()
    day = WEEKDAYS[today.weekday()]
    week = week_of(h)
    names = {m.id: m.name for m in members_of(s, h)}
    resps = active_resps(s, h)
    accepted = {p.responsibility_id: p.member_id for p in s.exec(
        select(Proposal).where(Proposal.week == week, Proposal.status == "accepted")).all()}
    done = {q.quest_key for q in s.exec(select(QuestLog).where(QuestLog.member_id == h.mother_member_id)).all()}

    def hour_after(start: str) -> str:
        return f"{(_minutes(start) // 60 + 1) % 24:02d}:{_minutes(start) % 60:02d}"

    def covering(days: list, start: str | None, end: str | None) -> str:
        if not start:
            return ""
        mine = _intervals([day], start, end or hour_after(start))
        for r in resps:
            if r.kind != "baby" or r.id not in accepted or day not in r.days or not r.start:
                continue
            for a0, a1 in mine:
                for b0, b1 in _intervals([day], r.start, r.end or hour_after(r.start)):
                    if a0 < b1 and b0 < a1:
                        return f"{names[accepted[r.id]]} has the baby."
        return ""

    quests = []
    for r in resps:
        if r.kind != "recovery":
            continue
        daily = len(r.days) == 7
        if daily:
            key = f"r{r.id}-{today.isoformat()}"
        elif r.days:
            key = f"r{r.id}-{week}"
            passed = any(WEEKDAYS.index(d) < today.weekday() for d in r.days)
            if day not in r.days and not (passed and key not in done):
                continue  # not today, and not a missed one rolling forward
        else:
            key = f"r{r.id}"
        quests.append({
            "key": key, "kind": "recovery", "title": r.title, "icon": r.icon or "walk",
            "time": _label(r.start), "sort": _minutes(r.start), "original_line": r.source_line,
            "schedule": r.schedule, "covering": covering(r.days, r.start, r.end), "done": key in done,
        })
    for rw in s.exec(select(RestWindow).where(RestWindow.member_id == h.mother_member_id)).all():
        if day not in rw.days:
            continue
        key = f"rest{rw.id}-{today.isoformat()}"
        night = _minutes(rw.start) >= 20 * 60
        title = (f"Sleep, {_label(rw.start)} to {_label(rw.end)}" if night
                 else f"Lie down, {_label(rw.start)} to {_label(rw.end)}")
        quests.append({
            "key": key, "kind": "rest", "title": title, "icon": "rest", "time": _label(rw.start),
            "sort": _minutes(rw.start), "original_line": "", "schedule": "Every day",
            "covering": covering(rw.days, rw.start, rw.end), "done": key in done,
        })
    quests.sort(key=lambda q: (q["sort"], q["kind"] != "recovery", q["title"]))
    for q in quests:
        q.pop("sort")
    return quests


@router.get("/quests/today")
def quests_today(me: Member = Depends(current_member), s: Session = Depends(get_session)):
    h = household_of(s, me)
    if me.id != h.mother_member_id:
        raise HTTPException(403, "The quest map is the mother's own.")
    quests = todays_quests(s, h)
    names = {m.id: m.name for m in members_of(s, h)}
    week = week_of(h)
    resps = {r.id: r for r in active_resps(s, h)}
    props = s.exec(select(Proposal).where(Proposal.week == week)).all()
    covered = [{"title": resps[p.responsibility_id].title, "owner": names.get(p.member_id, "")}
               for p in props if p.status == "accepted" and p.responsibility_id in resps
               and resps[p.responsibility_id].kind != "recovery"]
    arranging = sorted({resps[p.responsibility_id].title for p in props
                        if p.status == "pending" and p.responsibility_id in resps})
    outside = [r.title for r in s.exec(select(Responsibility).where(Responsibility.household_id == h.id,
                                                                     Responsibility.outside_help == True)).all()]  # noqa: E712
    bunnies = len(s.exec(select(QuestLog).where(QuestLog.member_id == me.id)).all())
    has_sheet = any(r.kind == "recovery" for r in resps.values())
    return {"name": me.name, "baby_type": h.baby_type, "quests": quests, "bunnies": bunnies,
            "covered": sorted(covered, key=lambda c: c["title"]), "arranging": arranging,
            "outside_help": outside, "has_sheet": has_sheet}


@router.post("/quests/{key}/done")
def quest_done(key: str, me: Member = Depends(current_member), s: Session = Depends(get_session)):
    h = household_of(s, me)
    if me.id != h.mother_member_id:
        raise HTTPException(403, "Only the mother logs her quests.")
    valid = {q["key"] for q in todays_quests(s, h)}
    if key not in valid:
        raise HTTPException(404, "That step isn't on today's map.")
    exists = s.exec(select(QuestLog).where(QuestLog.member_id == me.id, QuestLog.quest_key == key)).first()
    if not exists:
        s.add(QuestLog(member_id=me.id, quest_key=key, date=date.today().isoformat()))
        s.commit()
    bunnies = len(s.exec(select(QuestLog).where(QuestLog.member_id == me.id)).all())
    return {"bunnies": bunnies}


@router.get("/quests/progress")
def quest_progress(me: Member = Depends(current_member), s: Session = Depends(get_session)):
    """The mother's quests in detail, only for the people she chose to share with."""
    h = household_of(s, me)
    if me.id == h.mother_member_id or not can_see_progress(s, h, me):
        return {"shared": False, "quests": [], "dots": []}
    quests = todays_quests(s, h)
    mother = s.get(Member, h.mother_member_id)
    bunnies = len(s.exec(select(QuestLog).where(QuestLog.member_id == h.mother_member_id)).all())
    return {"shared": True, "name": mother.name if mother else "", "quests": quests,
            "done": sum(q["done"] for q in quests), "total": len(quests), "bunnies": bunnies,
            "dots": [q["done"] for q in quests]}
