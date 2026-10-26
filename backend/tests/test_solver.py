import random

import pytest

from app.engine import weights as W
from app.engine.solver import EMember, EResp, feasible, overlaps_rest, solve

KINDS = W.WORK_KINDS


def household(seed: int):
    rng = random.Random(seed)
    n = rng.randint(2, 6)
    members = []
    for i in range(1, n + 1):
        members.append(EMember(
            id=i, name=f"P{i}", capacity_hours=rng.choice([0, 4, 8, 10, 12, 16, 20, 30]),
            is_mother=(i == 1),
            blocked_days=set(rng.sample(W.WEEKDAYS, rng.randint(0, 3))),
            blocked_kinds=set(rng.sample(KINDS, rng.randint(0, 2))),
            rest_windows=[(W.WEEKDAYS, "22:00", "06:00"), (W.WEEKDAYS, "14:00", "16:00")] if i == 1 else [],
        ))
    resps = []
    for j in range(1, rng.randint(3, 12) + 1):
        kind = rng.choice(KINDS)
        start = rng.choice([None, "08:00", "15:00", "22:00", "10:00"])
        resps.append(EResp(
            id=100 + j, title=f"T{j}", kind=rng.choice(["baby", "home", "recovery"]), work_kind=kind,
            days=sorted(rng.sample(W.WEEKDAYS, rng.randint(1, 7)), key=W.WEEKDAYS.index),
            hours_per_occurrence=rng.choice([0.5, 1.0, 1.5, 2.0]),
            start=start, end=None if start is None else rng.choice(["09:00", "17:00", "06:00", "12:00"]),
            travel=rng.random() < 0.2,
        ))
    excluded = set()
    for r in resps:
        if rng.random() < 0.15:
            excluded.add((rng.choice(members).id, r.id))
    return members, resps, excluded


def check_constraints(members, resps, excluded, result, locked=None):
    by_m = {m.id: m for m in members}
    by_r = {r.id: r for r in resps}
    load = {m.id: 0.0 for m in members}
    for rid, mid in result.assignments.items():
        r, m = by_r[rid], by_m[mid]
        assert r.kind != "recovery", "recovery items are quests, never assigned"
        load[mid] += r.weight
        if locked and rid in locked:
            continue
        assert feasible(r, m, excluded), f"{r.title} broke a hard constraint for {m.name}"
    for mid, l in load.items():
        if locked and any(locked[r] == mid for r in locked):
            continue
        assert l <= by_m[mid].eff_capacity + 1e-6, f"{by_m[mid].name} over capacity"


@pytest.mark.parametrize("seed", range(200))
def test_never_over_capacity_and_constraints_hold(seed):
    members, resps, excluded = household(seed)
    result = solve(members, resps, excluded)
    check_constraints(members, resps, excluded, result)


def test_blocked_day_kind_rest_and_exclusion():
    mom = EMember(1, "Mom", 10, is_mother=True, rest_windows=[(W.WEEKDAYS, "14:00", "16:00")])
    a = EMember(2, "A", 10, blocked_days={"Thu"})
    b = EMember(3, "B", 10, blocked_kinds={"Nights"})
    nap = EResp(10, "Afternoon", "baby", "Baby care", ["Mon"], 1, "15:00", "15:30")
    thu = EResp(11, "Thursday", "home", "Cooking", ["Thu"], 1)
    night = EResp(12, "Night", "baby", "Nights", ["Mon"], 1)
    assert overlaps_rest(nap, mom) and not feasible(nap, mom, set())
    assert not feasible(thu, a, set())
    assert not feasible(night, b, set())
    assert not feasible(thu, b, {(3, 11)})
    result = solve([mom, a, b], [nap, thu, night], excluded={(3, 11)})
    assert result.assignments.get(10) != 1
    assert result.assignments.get(11) not in (2, 3)
    assert result.assignments.get(12) != 3


def test_deterministic():
    members, resps, excluded = household(7)
    first = solve(members, resps, excluded)
    for _ in range(5):
        again = solve(members, resps, excluded)
        assert again.assignments == first.assignments
        assert again.unassigned == first.unassigned


@pytest.mark.parametrize("seed", range(30))
def test_scale_invariant(seed):
    members, resps, excluded = household(seed)
    base = solve(members, resps, excluded)
    for m in members:
        m.capacity_hours *= 2
    for r in resps:
        r.hours_per_occurrence *= 2
    doubled = solve(members, resps, excluded)
    assert doubled.assignments == base.assignments


def test_locked_never_move():
    members, resps, excluded = household(11)
    open_resps = [r for r in resps if r.kind != "recovery"]
    first = solve(members, resps, excluded)
    locked = dict(list(first.assignments.items())[:2])
    for extra_seed in range(5):
        for m in members:
            m.capacity_hours += extra_seed
        again = solve(members, resps, excluded, locked=locked)
        for rid, mid in locked.items():
            assert again.assignments[rid] == mid
    assert open_resps


def test_recovery_items_do_not_count():
    mom = EMember(1, "Mom", 10, is_mother=True)
    walk = EResp(1, "Walk", "recovery", "", W.WEEKDAYS, 0.5)
    result = solve([mom], [walk])
    assert result.assignments == {} and result.unassigned == []


def test_seed_household_baseline_and_cold():
    from sqlmodel import Session

    from app import planning
    from app.db import engine
    from app.models import Household
    from app.seed import seed

    h = seed(cold=False)
    with Session(engine) as s:
        hh = s.get(Household, h.id)
        assert planning.latest_plan(s, hh).unassigned_json == []
        hh.cold = True
        s.add(hh)
        s.commit()
        plan = planning.replan(s, hh)
        hours = sum(u["hours"] for u in plan.unassigned_json)
        assert 2.0 <= hours <= 4.0
