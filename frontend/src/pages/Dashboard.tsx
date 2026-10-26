import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { RefreshCw } from "lucide-react";
import { api, DAY_NAMES, timeLabel, WEEKDAYS, type Plan, type PlanMember, type Proposal, type QuestProgress, type Resp } from "../api";
import { SharedQuests } from "../components/SharedQuests";
import { SideCard } from "../components/Cards";
import { LoadBar } from "../components/LoadBar";
import { TaskRow } from "../components/TaskRow";
import { useSession } from "../session";

export type Row = { r: Resp; ownerId?: number; status?: "arranging" | "outside" | "needs" | "asked" };

export function usePlan() {
  const [plan, setPlan] = useState<Plan | null>(null);
  const [error, setError] = useState("");
  const load = useCallback(() => {
    api.get<Plan>("/api/plan").then(setPlan).catch((e) => setError((e as Error).message));
  }, []);
  useEffect(load, [load]);
  return { plan, setPlan, error, load };
}

export function SetupCard() {
  const { household } = useSession();
  if (!household) return null;
  const s = household.sharing;
  const motherName = household.mother?.name ?? "The mother";
  return (
    <section className="card setup-card stack-sm">
      <h2>Almost ready to share out the work</h2>
      <p>The plan starts once {motherName} and her partner each turn on "Let With Us share out the work" in their own view.</p>
      <ul className="helper" style={{ margin: 0 }}>
        <li>{motherName}: {s.mother ? "on" : "not yet"}</li>
        <li>Partner: {household.has_partner ? (s.partner ? "on" : "not yet") : "hasn't joined yet"}</li>
      </ul>
      <p className="helper">Meanwhile, everyone can set what they can take on, privately.</p>
      <Link className="btn" to="/control" style={{ alignSelf: "flex-start" }}>Open my settings</Link>
    </section>
  );
}

function nextTask(rows: Row[]): { r: Resp; day: string } | null {
  const today = (new Date().getDay() + 6) % 7;
  let best: { r: Resp; day: string; score: number } | null = null;
  for (const { r } of rows) {
    for (const d of r.days) {
      let delta = (WEEKDAYS.indexOf(d) - today + 7) % 7;
      const mins = r.start ? Number(r.start.slice(0, 2)) * 60 + Number(r.start.slice(3)) : 600;
      const nowMins = new Date().getHours() * 60 + new Date().getMinutes();
      if (delta === 0 && mins < nowMins) delta = 7;
      const score = delta * 1440 + mins;
      if (!best || score < best.score) best = { r, day: d, score };
    }
  }
  return best && { r: best.r, day: best.day };
}


export function WeekCalendar({ rows, members }: { rows: Row[]; members: Map<number, PlanMember> }) {
  return (
    <div className="calendar">
      {WEEKDAYS.map((d) => (
        <div className="cal-day" key={d}>
          <h4>{DAY_NAMES[d]}</h4>
          {rows.filter((x) => x.r.days.includes(d)).sort((a, b) => (a.r.start ?? "99").localeCompare(b.r.start ?? "99")).map((x) => {
            const o = x.ownerId ? members.get(x.ownerId) : null;
            return (
              <div className="cal-item" key={`${x.r.id}-${x.status ?? "a"}`} style={{ borderLeftColor: o ? `var(${o.colour})` : x.status === "asked" ? "var(--rose-600)" : "var(--pink-200)", ...(x.status === "asked" ? { background: "var(--pink-100)" } : {}) }}>
                <strong>{x.r.title}</strong>
                <div className="helper" style={{ fontSize: 12 }}>
                  {x.r.start ? timeLabel(x.r.start) + " · " : ""}{o ? o.name : x.status === "asked" ? "Asked of you" : x.status === "arranging" ? "Being arranged" : x.status === "outside" ? "Outside help" : "Needs someone"}
                </div>
              </div>
            );
          })}
        </div>
      ))}
    </div>
  );
}

export default function Dashboard({ initialTab = "mine" }: { initialTab?: "mine" | "everyone" }) {
  const { household, toast, refresh } = useSession();
  const { plan, setPlan, error } = usePlan();
  const [tab, setTab] = useState(initialTab);
  const [view, setView] = useState<"list" | "calendar">("list");
  const [proposals, setProposals] = useState<Proposal[]>([]);
  const [progress, setProgress] = useState<QuestProgress>({ shared: false, quests: [], dots: [] });
  const [news, setNews] = useState<{ from: string; text: string }[]>([]);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.get<Proposal[]>("/api/me/proposals").then(setProposals).catch(() => undefined);
    api.get<QuestProgress>("/api/quests/progress").then(setProgress).catch(() => undefined);
    api.get<typeof news>("/api/announcements").then(setNews).catch(() => undefined);
  }, [plan]);

  if (!household) return null;
  const motherName = household.mother?.name ?? "her";
  const me = household.me;

  const replan = async () => {
    setBusy(true);
    try {
      setPlan(await api.post<Plan>("/api/plan/replan"));
      await refresh();
      toast("Re-planned. Anything that moved will ask the right person.");
    } catch (e) {
      toast((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div>
      <div className="page-head">
        <h1>How the work around {motherName}'s recovery is shared</h1>
        {plan?.ready && <p style={{ fontSize: 20 }} className="muted">{plan.headline}</p>}
      </div>
      {error && <p className="error">{error}</p>}
      {plan && !plan.ready && <SetupCard />}
      {plan?.ready && (() => {
        const members = new Map(plan.members.map((m) => [m.id, m]));
        const all: Row[] = [
          ...plan.assignments.filter((a) => a.responsibility.kind !== "recovery").map((a) => ({ r: a.responsibility, ownerId: a.member_id })),
          ...plan.arranging.filter((r) => r.kind !== "recovery").map((r) => ({ r, status: "arranging" as const })),
          ...plan.unassigned.map((u) => ({ r: u.responsibility, status: "needs" as const })),
          ...plan.outside_help.map((r) => ({ r, status: "outside" as const })),
        ];
        const mine = all.filter((x) => x.ownerId === me.id);
        const rows = tab === "mine" ? mine : all;
        const next = nextTask(mine);
        const counts = { covered: plan.assignments.filter((a) => a.responsibility.kind !== "recovery").length, arranging: plan.arranging.length, needs: plan.unassigned.length };
        return (
          <div className="grid-2">
            <div className="stack" style={{ gap: 24 }}>
              <section className="card">
                <LoadBar members={plan.members} />
              </section>
              <section className="card stack">
                <div className="row" style={{ justifyContent: "space-between" }}>
                  <div className="tabs" role="tablist" aria-label="Whose tasks">
                    <button role="tab" aria-selected={tab === "mine"} onClick={() => setTab("mine")}>Mine</button>
                    <button role="tab" aria-selected={tab === "everyone"} onClick={() => setTab("everyone")}>Everyone</button>
                  </div>
                  <div className="tabs" role="tablist" aria-label="View">
                    <button role="tab" aria-selected={view === "list"} onClick={() => setView("list")}>List</button>
                    <button role="tab" aria-selected={view === "calendar"} onClick={() => setView("calendar")}>Calendar</button>
                  </div>
                </div>
                {rows.length === 0 && (
                  <p className="muted">
                    {tab === "mine" ? (proposals.length ? "Nothing is yours yet. Check Needs you for requests." : "Nothing is yours this week.") : "No tasks in the plan yet. Add one from the sidebar."}
                  </p>
                )}
                {view === "list" ? (
                  <div className="task-list">
                    {rows.map((x) => {
                      const o = x.ownerId ? members.get(x.ownerId) : null;
                      return <TaskRow key={`${x.r.id}-${x.status ?? "a"}`} r={x.r} status={x.status} owner={tab === "everyone" && o ? { name: o.name, colour: o.colour } : null} />;
                    })}
                  </div>
                ) : (
                  <WeekCalendar rows={rows} members={members} />
                )}
              </section>
              {!(tab === "everyone" && view === "calendar") && (
                <section className="card stack">
                  <h2>The whole week</h2>
                  <WeekCalendar rows={all} members={members} />
                </section>
              )}
              {news.length > 0 && (
                <section className="card stack-sm">
                  <h3>From the family</h3>
                  {news.slice(0, 5).map((n, i) => <p key={i}>{n.text}</p>)}
                </section>
              )}
            </div>
            <aside className="stack">
              <SideCard title="Your assistant" tone="tint">
                <p className="helper">Ask about your week, or let it help you say no kindly.</p>
                <div className="row">
                  <Link className="btn btn-sm" to="/assistant">Open</Link>
                  <button className="btn btn-sm" onClick={replan} disabled={busy}><RefreshCw size={14} aria-hidden="true" /> Re-plan now</button>
                </div>
              </SideCard>
              <SideCard title="Next task">
                {next ? (
                  <p><strong>{next.r.title}</strong><br /><span className="helper">{DAY_NAMES[next.day]}{next.r.start ? `, ${timeLabel(next.r.start)}` : ""}</span></p>
                ) : <p className="helper">Nothing coming up for you.</p>}
              </SideCard>
              {proposals.length > 0 && (
                <SideCard title="Waiting on you" tone="warn">
                  <p className="warn-ink">{proposals.length} request{proposals.length === 1 ? "" : "s"} only you can see.</p>
                  <Link className="btn btn-sm" to="/needs-you" style={{ alignSelf: "flex-start" }}>Answer</Link>
                </SideCard>
              )}
              <SideCard title="This week">
                <p>{counts.covered} covered · {counts.arranging} being arranged{counts.needs ? ` · ${counts.needs} need someone` : ""}</p>
              </SideCard>
              {progress.shared && <SharedQuests p={progress} />}
            </aside>
          </div>
        );
      })()}
    </div>
  );
}

/** The mother's view of the plan: who covers what, no percentages. */
export function MotherPlan() {
  const { plan, error } = usePlan();
  const { household } = useSession();
  if (error) return <p className="error">{error}</p>;
  if (!plan) return <p className="muted">Loading...</p>;
  return (
    <div>
      <div className="page-head">
        <h1>Your week</h1>
        <p className="muted">Who is covering what around you.</p>
      </div>
      {!plan.ready ? <SetupCard /> : (
        <section className="card task-list">
          {plan.assignments.filter((a) => a.responsibility.kind !== "recovery").map((a) => {
            const m = household?.members.find((x) => x.id === a.member_id);
            return <TaskRow key={a.responsibility.id} r={a.responsibility} owner={m ? { name: m.name, colour: m.colour } : null} />;
          })}
          {plan.arranging.filter((r) => r.kind !== "recovery").map((r) => <TaskRow key={r.id} r={r} status="arranging" />)}
          {plan.outside_help.map((r) => <TaskRow key={r.id} r={r} status="outside" />)}
        </section>
      )}
    </div>
  );
}
