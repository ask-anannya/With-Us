import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Eye, Lock } from "lucide-react";
import { api, DAY_NAMES, type Me, type MemberPublic } from "../api";
import { Avatar } from "../components/LoadBar";
import { Sheet } from "../components/QuestMap";
import { useSession } from "../session";
import { CodeCard } from "./Create";
import { IntakeForm } from "./Intake";

function HouseholdSees({ m }: { m: MemberPublic }) {
  const days = m.limits.filter((l) => l.kind === "day").map((l) => DAY_NAMES[l.value] ?? l.value);
  const kinds = m.limits.filter((l) => l.kind === "work_kind").map((l) => l.value);
  return (
    <div className="card card-tint stack-sm">
      <div className="row"><Avatar name={m.name} colour={m.colour} /><strong>{m.name}</strong><span className="helper">{m.is_mother ? "recovering" : m.role}</span></div>
      <p>{m.capacity_hours} hours a week{m.is_mother ? " (planned at half, so she can rest)" : ""}</p>
      <p>Not available: {days.length ? days.join(", ") : "no days blocked"}</p>
      <p>Doesn't take: {kinds.length ? kinds.join(", ") : "nothing blocked"}</p>
      {m.resting && m.resting.length > 0 && <p>Resting blocks: {m.resting.length}</p>}
      <p className="helper">No reasons. No instructions. No requests or answers.</p>
    </div>
  );
}

function YouTab() {
  const { household, toast } = useSession();
  const [me, setMe] = useState<Me | null>(null);
  const [instructions, setInstructions] = useState("");
  const [reasons, setReasons] = useState<Record<number, string>>({});
  const [sees, setSees] = useState<MemberPublic | null>(null);
  const [told, setTold] = useState<{ rules: string; context: string } | null>(null);
  const [version, setVersion] = useState(0);

  useEffect(() => {
    api.get<Me>("/api/me").then((m) => {
      setMe(m);
      setInstructions(m.instructions);
      setReasons(Object.fromEntries(m.limits.map((l) => [l.id, l.reason])));
    });
    api.get<MemberPublic>("/api/me/what-household-sees").then(setSees);
  }, [version]);

  if (!me || !household) return <p className="muted">Loading...</p>;

  const saveReason = async (id: number) => {
    await api.put(`/api/me/reasons/${id}`, { text: reasons[id] ?? "" });
    toast("Saved privately.");
  };
  const saveInstructions = async () => {
    await api.put("/api/me/instructions", { text: instructions });
    toast("Your assistant will follow this.");
  };
  const showTold = async () => setTold(await api.get("/api/me/what-assistant-is-told"));

  return (
    <div className="grid-2">
      <div className="stack" style={{ gap: 28 }}>
        <CodeCard code={household.code} memberId={me.member_id} />
        <section className="card stack">
          <h2>What you can take on</h2>
          <IntakeForm key={version} onSaved={() => setVersion((v) => v + 1)} submitLabel="Save changes" />
        </section>
      </div>
      <aside className="stack">
        <h3>What your household sees</h3>
        {sees && <HouseholdSees m={sees} />}
        {me.limits.length > 0 && (
          <section className="card stack">
            <h2>Private reasons, per limit</h2>
            <p className="note" style={{ color: "var(--rose-700)" }}><Lock size={14} aria-hidden="true" /> Only you and your assistant see these.</p>
            {me.limits.map((l) => (
              <div className="reason-box" key={l.id}>
                <label htmlFor={`r${l.id}`} style={{ fontWeight: 700 }}>{l.kind === "day" ? DAY_NAMES[l.value] : l.value}</label>
                <textarea id={`r${l.id}`} className="input" value={reasons[l.id] ?? ""} onChange={(e) => setReasons({ ...reasons, [l.id]: e.target.value })} placeholder="Optional" />
                <button className="btn btn-sm" style={{ marginTop: 8 }} onClick={() => saveReason(l.id)}>Save</button>
              </div>
            ))}
          </section>
        )}
        <section className="card stack">
          <h2>Instructions for your assistant</h2>
          <p className="helper">For example: "I never say no. When it's too much, say it for me, kindly."</p>
          <textarea className="input" value={instructions} onChange={(e) => setInstructions(e.target.value)} />
          <div className="row">
            <button className="btn btn-primary" onClick={saveInstructions}>Save</button>
            <button className="btn" onClick={showTold}><Eye size={16} aria-hidden="true" /> See what your assistant is told</button>
          </div>
        </section>
      </aside>
      {told && (
        <Sheet onClose={() => setTold(null)} label="What your assistant is told">
          <div className="stack">
            <h2>What your assistant is told</h2>
            <p className="helper">This is everything it knows. Nobody else's reasons are in it.</p>
            <pre style={{ whiteSpace: "pre-wrap", background: "var(--pink-50)", padding: 16, borderRadius: 12, fontSize: 14 }}>{told.context}</pre>
            <details>
              <summary>Its rules</summary>
              <pre style={{ whiteSpace: "pre-wrap", fontSize: 13 }}>{told.rules}</pre>
            </details>
          </div>
        </Sheet>
      )}
    </div>
  );
}

function HouseholdTab() {
  const { household, refresh, toast } = useSession();
  if (!household) return null;
  const me = household.me;
  const mine = me.is_mother ? "mother" : me.role === "partner" ? "partner" : null;
  const setSharing = async (on: boolean) => {
    try {
      await api.patch("/api/household/sharing", { on });
      await refresh();
    } catch (e) {
      toast((e as Error).message);
    }
  };
  const setCold = async (on: boolean) => {
    await api.post("/api/household/cold", { on });
    await refresh();
    toast(on ? "Baby has a cold this week. The plan re-balanced." : "Back to a normal week.");
  };
  return (
    <div className="grid-halves">
      <section className="card stack-sm">
        <h2>Members</h2>
        <div className="task-list">
          {household.members.map((m) => (
            <div className="task-row" key={m.id}>
              <Avatar name={m.name} colour={m.colour} />
              <div style={{ flex: 1 }}><strong>{m.name}</strong><div className="helper">{m.is_mother ? "recovering" : m.role}</div></div>
              <span className="helper">{m.capacity_hours} h a week</span>
            </div>
          ))}
        </div>
      </section>
      <div className="stack">
      <section className="card stack">
        <h2>Sharing out the work</h2>
        <p className="helper">The plan runs only when both switches are on. Each person sets their own.</p>
        <label className="switch">
          <input type="checkbox" checked={household.sharing.mother} disabled={mine !== "mother"} onChange={(e) => setSharing(e.target.checked)} />
          <span>{household.mother?.name ?? "Mother"}: let With Us share out the work</span>
        </label>
        <label className="switch">
          <input type="checkbox" checked={household.sharing.partner} disabled={mine !== "partner"} onChange={(e) => setSharing(e.target.checked)} />
          <span>Partner: let With Us share out the work</span>
        </label>
      </section>
      <section className="card stack-sm">
        <h2>Doctor's instructions</h2>
        <p className="helper">Add the discharge sheet to turn it into {household.mother?.name ?? "her"}'s quests.</p>
        <Link className="btn" to="/prescription" style={{ alignSelf: "flex-start" }}>Add the discharge sheet</Link>
      </section>
      {household.demo && (
        <section className="card card-tint stack-sm">
          <h2>Demo</h2>
          <label className="switch">
            <input type="checkbox" checked={household.cold} onChange={(e) => setCold(e.target.checked)} />
            <span>Baby has a cold (extra night feeds and a pediatric visit)</span>
          </label>
        </section>
      )}
      </div>
    </div>
  );
}

function ActivityTab() {
  const [rows, setRows] = useState<{ at: string; text: string }[] | null>(null);
  const [news, setNews] = useState<{ from: string; text: string; at: string }[]>([]);
  useEffect(() => {
    api.get<typeof rows>("/api/activity").then(setRows);
    api.get<typeof news>("/api/announcements").then(setNews);
  }, []);
  return (
    <div className="grid-halves">
    <section className="card stack-sm">
      <h2>Activity</h2>
      <p className="helper">Only general updates. Never who was asked, who said no, or why.</p>
      {rows && rows.length === 0 && <p className="muted">Nothing yet.</p>}
      <div className="task-list">
        {rows?.map((r, i) => (
          <div className="task-row" key={i}>
            <span style={{ flex: 1 }}>{r.text}</span>
            <span className="helper">{new Date(r.at).toLocaleString([], { weekday: "short", hour: "numeric", minute: "2-digit" })}</span>
          </div>
        ))}
      </div>
    </section>
    <section className="card stack-sm">
      <h2>From the family</h2>
      <p className="helper">Lines people chose to share with "Tell the family kindly for me".</p>
      {news.length === 0 && <p className="muted">Nothing shared yet.</p>}
      <div className="task-list">
        {news.map((n, i) => (
          <div className="task-row" key={i}>
            <span style={{ flex: 1 }}>{n.text}</span>
          </div>
        ))}
      </div>
    </section>
    </div>
  );
}

export default function ControlPanel() {
  const [tab, setTab] = useState<"you" | "household" | "activity">("you");
  return (
    <div>
      <div className="page-head">
        <h1>Control panel</h1>
      </div>
      <div className="tabs" role="tablist" aria-label="Control panel" style={{ marginBottom: 24 }}>
        <button role="tab" aria-selected={tab === "you"} onClick={() => setTab("you")}>You</button>
        <button role="tab" aria-selected={tab === "household"} onClick={() => setTab("household")}>Household</button>
        <button role="tab" aria-selected={tab === "activity"} onClick={() => setTab("activity")}>Activity</button>
      </div>
      {tab === "you" && <YouTab />}
      {tab === "household" && <HouseholdTab />}
      {tab === "activity" && <ActivityTab />}
    </div>
  );
}
