"""The fair-plan engine.

Assigns whole responsibilities so everyone is about equally full against their
own capacity, never above it. Deterministic: same input, same output.
"""
from dataclasses import dataclass, field
from typing import Optional

from . import weights as W

EPS = 1e-9
MAX_ITERATIONS = 500


@dataclass
class EMember:
    id: int
    name: str
    capacity_hours: float
    is_mother: bool = False
    blocked_days: set = field(default_factory=set)
    blocked_kinds: set = field(default_factory=set)
    rest_windows: list = field(default_factory=list)  # [(days, "HH:MM", "HH:MM")]

    @property
    def eff_capacity(self) -> float:
        return W.effective_capacity(self.capacity_hours, self.is_mother)


@dataclass
class EResp:
    id: int
    title: str
    kind: str
    work_kind: str
    days: list
    hours_per_occurrence: float
    start: Optional[str] = None
    end: Optional[str] = None
    travel: bool = False
    fixed_owner_id: Optional[int] = None

    @property
    def weight(self) -> float:
        return W.weight(self.hours_per_occurrence, self.days, self.work_kind, self.travel)

    @property
    def hours(self) -> float:
        return W.hours_per_week(self.hours_per_occurrence, self.days)


@dataclass
class PlanResult:
    assignments: dict  # resp_id -> member_id
    burden: dict  # member_id -> fraction of own capacity
    load: dict  # member_id -> assigned weight
    spread: float  # percentage points
    unassigned: list  # [(resp_id, hours)]

    @property
    def unassigned_hours(self) -> float:
        return sum(h for _, h in self.unassigned)


def _minutes(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def _intervals(days: list, start: str, end: str) -> list:
    """Week-minute intervals, splitting windows that cross midnight."""
    out = []
    s, e = _minutes(start), _minutes(end)
    for d in days:
        base = W.WEEKDAYS.index(d) * 1440
        if e > s:
            out.append((base + s, base + e))
        else:
            out.append((base + s, base + 1440))
            nxt = ((W.WEEKDAYS.index(d) + 1) % 7) * 1440
            out.append((nxt, nxt + e))
    return out


def overlaps_rest(resp: EResp, member: EMember) -> bool:
    if not member.rest_windows:
        return False
    start, end = resp.start, resp.end
    if not start or not end:
        if resp.work_kind != "Nights":
            return False
        start, end = "22:00", "06:00"
    mine = _intervals(resp.days, start, end)
    for days, rs, re_ in member.rest_windows:
        for a0, a1 in mine:
            for b0, b1 in _intervals(days, rs, re_):
                if a0 < b1 and b0 < a1:
                    return True
    return False


def feasible(resp: EResp, member: EMember, excluded: set) -> bool:
    if member.eff_capacity <= 0:
        return False
    if (member.id, resp.id) in excluded:
        return False
    if any(d in member.blocked_days for d in resp.days):
        return False
    if resp.work_kind and resp.work_kind in member.blocked_kinds:
        return False
    if member.is_mother and overlaps_rest(resp, member):
        return False
    return True


def _objective(load: dict, caps: dict, unassigned_hours: float, counted: set) -> tuple:
    """Spread is measured over members with capacity, except the mother: her
    ceiling already protects her, and her near-zero load would swamp the spread."""
    burdens = [load[m] / caps[m] for m in counted if caps[m] > 0]
    if not burdens:
        return (0.0, 0.0, round(unassigned_hours, 9))
    spread = (max(burdens) - min(burdens)) * 100
    return (round(spread, 9), round(max(burdens), 9), round(unassigned_hours, 9))


def solve(members: list, resps: list, excluded: set = frozenset(), locked: dict = None) -> PlanResult:
    """members: [EMember]; resps: [EResp] (recovery items are skipped, they are the
    mother's own quests and never count toward her burden); excluded: {(member_id,
    resp_id)}; locked: {resp_id: member_id} accepted assignments that never move."""
    locked = dict(locked or {})
    members = sorted(members, key=lambda m: m.id)
    resps = sorted([r for r in resps if r.kind != "recovery"], key=lambda r: r.id)
    by_id = {m.id: m for m in members}
    caps = {m.id: m.eff_capacity for m in members}
    counted = {m.id for m in members if not m.is_mother}
    rw = {r.id: r.weight for r in resps}
    load = {m.id: 0.0 for m in members}
    assign: dict = {}
    unassigned: list = []

    # 1. feasibility matrix
    feas = {r.id: [m.id for m in members if feasible(r, m, excluded)] for r in resps}

    def has_room(mid: int, w: float) -> bool:
        return load[mid] + w <= caps[mid] + EPS

    # 2. fixed and locked first
    pinned = set()
    for r in resps:
        owner = locked.get(r.id)
        if owner in by_id:
            assign[r.id] = owner
            load[owner] += rw[r.id]
            pinned.add(r.id)
        elif r.fixed_owner_id in by_id:
            if r.fixed_owner_id in feas[r.id] and has_room(r.fixed_owner_id, rw[r.id]):
                assign[r.id] = r.fixed_owner_id
                load[r.fixed_owner_id] += rw[r.id]
            else:
                unassigned.append(r)
            pinned.add(r.id)

    # 3. sort open items: weight desc, fewest feasible, id
    open_items = [r for r in resps if r.id not in pinned]
    open_items.sort(key=lambda r: (-rw[r.id], len(feas[r.id]), r.id))

    # 4. greedy: lowest resulting burden among feasible members with room
    for r in open_items:
        best = None
        for mid in feas[r.id]:
            if not has_room(mid, rw[r.id]):
                continue
            b = (load[mid] + rw[r.id]) / caps[mid]
            key = (round(b, 9), mid)
            if best is None or key < best[0]:
                best = (key, mid)
        if best is None:
            unassigned.append(r)
        else:
            assign[r.id] = best[1]
            load[best[1]] += rw[r.id]

    movable = sorted(r.id for r in open_items if r.id in assign)

    def unassigned_hours() -> float:
        return sum(r.hours for r in unassigned)

    # 5. local search: move one, then swap two; accept lexicographic improvement
    def local_search():
        for _ in range(MAX_ITERATIONS):
            current = _objective(load, caps, unassigned_hours(), counted)
            improved = False
            for rid in movable:
                src = assign[rid]
                for dst in feas[rid]:
                    if dst == src or not has_room(dst, rw[rid]):
                        continue
                    load[src] -= rw[rid]
                    load[dst] += rw[rid]
                    if _objective(load, caps, unassigned_hours(), counted) < current:
                        assign[rid] = dst
                        improved = True
                        break
                    load[dst] -= rw[rid]
                    load[src] += rw[rid]
                if improved:
                    break
            if not improved:
                for i, a in enumerate(movable):
                    for b in movable[i + 1:]:
                        ma, mb = assign[a], assign[b]
                        if ma == mb or mb not in feas[a] or ma not in feas[b]:
                            continue
                        delta = rw[b] - rw[a]
                        if load[ma] + delta > caps[ma] + EPS or load[mb] - delta > caps[mb] + EPS:
                            continue
                        load[ma] += delta
                        load[mb] -= delta
                        if _objective(load, caps, unassigned_hours(), counted) < current:
                            assign[a], assign[b] = mb, ma
                            improved = True
                            break
                        load[ma] -= delta
                        load[mb] += delta
                    if improved:
                        break
            if not improved:
                return

    local_search()

    # 6. repair: place each unassigned item, moving one open item away if needed
    for r in sorted(unassigned, key=lambda r: (-rw[r.id], r.id)):
        if r.fixed_owner_id in by_id:
            continue
        placed = False
        for mid in feas[r.id]:
            if has_room(mid, rw[r.id]):
                assign[r.id] = mid
                load[mid] += rw[r.id]
                placed = True
                break
        if not placed:
            for mid in feas[r.id]:
                for other in movable:
                    if assign.get(other) != mid:
                        continue
                    if load[mid] - rw[other] + rw[r.id] > caps[mid] + EPS:
                        continue
                    for dst in feas[other]:
                        if dst == mid or not has_room(dst, rw[other]):
                            continue
                        load[mid] += rw[r.id] - rw[other]
                        load[dst] += rw[other]
                        assign[other] = dst
                        assign[r.id] = mid
                        placed = True
                        break
                    if placed:
                        break
                if placed:
                    break
        if placed:
            unassigned.remove(r)
            movable.append(r.id)
            movable.sort()

    local_search()

    burden = {mid: (load[mid] / caps[mid] if caps[mid] > 0 else 0.0) for mid in load}
    spread = _objective(load, caps, 0, counted)[0]
    return PlanResult(
        assignments=dict(sorted(assign.items())),
        burden=burden,
        load=load,
        spread=spread,
        unassigned=[(r.id, r.hours) for r in sorted(unassigned, key=lambda r: r.id)],
    )
