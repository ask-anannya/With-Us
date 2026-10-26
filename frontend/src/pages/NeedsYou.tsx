import { useCallback, useEffect, useState } from "react";
import { EyeOff, Heart, Scale } from "lucide-react";
import { api, type Decision, type Plan, type PlanMember, type Proposal, type Resp } from "../api";
import { WeekCalendar, type Row } from "./Dashboard";
import { ProposalCard, ShortfallCard, SideCard } from "../components/Cards";
import { TaskRow } from "../components/TaskRow";
import { useSession } from "../session";

export default function NeedsYou() {
  const { household } = useSession();
  const [proposals, setProposals] = useState<Proposal[] | null>(null);
  const [decisions, setDecisions] = useState<Decision[]>([]);
  const [mine, setMine] = useState<Resp[]>([]);
  const [members, setMembers] = useState<Map<number, PlanMember>>(new Map());
  const [error, setError] = useState("");
  const load = useCallback(() => {
    Promise.all([api.get<Proposal[]>("/api/me/proposals"), api.get<Decision[]>("/api/decisions"), api.get<Plan>("/api/plan")])
      .then(([p, d, plan]) => {
        setProposals(p);
        setDecisions(d);
        setMine(plan.ready ? plan.assignments.filter((a) => a.member_id === household?.me.id).map((a) => a.responsibility) : []);
        setMembers(new Map(plan.ready ? plan.members.map((m) => [m.id, m]) : []));
      })
      .catch((e) => setError((e as Error).message));
  }, [household?.me.id]);
  useEffect(load, [load]);

  const nothing = proposals && proposals.length === 0 && decisions.length === 0;

  return (
    <div>
      <div className="page-head">
        <h1>Needs you</h1>
        <p className="muted">Nobody gets a task without saying yes. Your answers here are private.</p>
      </div>
      {error && <p className="error">{error}</p>}
      <div className="grid-2">
        <div className="stack">
          {proposals === null && !error && <p className="muted">Loading...</p>}
          {nothing && (
            <div className="card card-tint"><p>Nothing needs you right now. Thank you for being here.</p></div>
          )}
          {decisions.length > 0 && <h2>For the household to decide</h2>}
          {decisions.map((d) => <ShortfallCard key={d.id} d={d} onDone={load} />)}
          {proposals && proposals.length > 0 && <h2 style={{ marginTop: decisions.length ? 12 : 0 }}>Asked of you</h2>}
          {proposals?.map((p) => <ProposalCard key={p.id} p={p} onDone={load} />)}
          {proposals && household && (mine.length > 0 || proposals.length > 0) && (
            <section className="card stack" style={{ marginTop: 8 }}>
              <h2>Your week</h2>
              <p className="helper">What you already carry, with anything asked of you highlighted, so you can decide.</p>
              <WeekCalendar
                members={members}
                rows={[
                  ...mine.map((r): Row => ({ r, ownerId: household.me.id })),
                  ...proposals.map((p): Row => ({ r: p.responsibility, status: "asked" })),
                ]}
              />
            </section>
          )}
        </div>
        <aside className="stack sticky-side">
          <SideCard title="How saying no works" tone="tint">
            <div className="stack-sm">
              <p className="row" style={{ flexWrap: "nowrap", alignItems: "flex-start" }}><EyeOff size={18} color="var(--rose-600)" aria-hidden="true" style={{ flex: "none", marginTop: 3 }} /><span className="helper">Requests are visible only to you. Nobody sees who was asked.</span></p>
              <p className="row" style={{ flexWrap: "nowrap", alignItems: "flex-start" }}><Scale size={18} color="var(--rose-600)" aria-hidden="true" style={{ flex: "none", marginTop: 3 }} /><span className="helper">"Not this week" quietly re-balances the plan. Others only see "Plan updated".</span></p>
              <p className="row" style={{ flexWrap: "nowrap", alignItems: "flex-start" }}><Heart size={18} color="var(--rose-600)" aria-hidden="true" style={{ flex: "none", marginTop: 3 }} /><span className="helper">Want the family to hear it from you? Turn on "Tell the family kindly for me" for one gentle line, with no reason given.</span></p>
            </div>
          </SideCard>
          <SideCard title="Already yours this week">
            {mine.length === 0 ? <p className="helper">Nothing yet.</p> : (
              <div className="task-list">{mine.map((r) => <TaskRow key={r.id} r={r} />)}</div>
            )}
          </SideCard>
        </aside>
      </div>
    </div>
  );
}
