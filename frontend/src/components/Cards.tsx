import { useState } from "react";
import { api, whenLabel, type Decision, type Proposal } from "../api";
import { useSession } from "../session";
import { KindIcon } from "./TaskRow";

export function SideCard({ title, tone, children }: { title: string; tone?: "warn" | "tint"; children: React.ReactNode }) {
  return (
    <section className={`card stack-sm${tone === "warn" ? " card-warn" : tone === "tint" ? " card-tint" : ""}`}>
      <h3>{title}</h3>
      {children}
    </section>
  );
}

export function ProposalCard({ p, onDone }: { p: Proposal; onDone: () => void }) {
  const { toast, refresh } = useSession();
  const [tell, setTell] = useState(false);
  const [busy, setBusy] = useState(false);
  const r = p.responsibility;

  const act = async (kind: "accept" | "decline") => {
    setBusy(true);
    try {
      if (kind === "accept") {
        await api.post(`/api/me/proposals/${p.id}/accept`);
        toast(`${r.title} is yours. Thank you.`);
      } else {
        const res = await api.post<{ announcement: string | null }>(`/api/me/proposals/${p.id}/decline`, { tell_family: tell });
        toast(res.announcement ? "Done. We told the family kindly for you." : "Done. The plan will quietly find someone else.");
      }
      await refresh();
      onDone();
    } catch (e) {
      toast((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <article className="card proposal-card">
      <div className="row" style={{ alignItems: "flex-start", flexWrap: "nowrap" }}>
        <KindIcon r={r} />
        <div className="stack-sm" style={{ flex: 1, minWidth: 0 }}>
          <h3>{r.title}</h3>
          <p className="helper">{whenLabel(r)}{r.work_kind ? ` · ${r.work_kind}` : ""} · about {Math.round(r.hours_per_occurrence * r.days.length * 10) / 10} hours a week</p>
          <p className="helper">Only you can see this request. If you say no, nobody is told it was you.</p>
        </div>
      </div>
      <div className="proposal-actions">
        <label className="switch">
          <input type="checkbox" checked={tell} onChange={(e) => setTell(e.target.checked)} />
          <span>Tell the family kindly for me</span>
        </label>
        <div className="row" style={{ flexWrap: "nowrap" }}>
          <button className="btn btn-primary" disabled={busy} onClick={() => act("accept")}>Accept</button>
          <button className="btn" disabled={busy} onClick={() => act("decline")}>Not this week</button>
        </div>
      </div>
    </article>
  );
}

export function ShortfallCard({ d, onDone }: { d: Decision; onDone: () => void }) {
  const { toast, refresh } = useSession();
  const [cap, setCap] = useState(Math.ceil(d.my_capacity + d.hours));
  const [raising, setRaising] = useState(false);
  const [busy, setBusy] = useState(false);

  const resolve = async (option: string) => {
    setBusy(true);
    try {
      await api.post(`/api/decisions/${d.id}/resolve`, { option, capacity_hours: option === "raise_capacity" ? cap : undefined });
      toast(option === "drop" ? "Paused for this week." : option === "outside_help" ? "Marked as outside help." : "Thanks. Your capacity is updated.");
      await refresh();
      onDone();
    } catch (e) {
      toast((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <article className="card card-warn stack">
      <h3>{d.text}</h3>
      <p className="warn-ink">Nobody is quietly overloaded. The household decides.</p>
      <div className="row">
        {d.options.includes("drop") && (
          <button className="btn" disabled={busy} onClick={() => resolve("drop")}>Drop or pause it</button>
        )}
        <button className="btn" disabled={busy} onClick={() => resolve("outside_help")}>Mark as outside help</button>
        <button className="btn" disabled={busy} onClick={() => setRaising((v) => !v)}>Raise my own capacity</button>
      </div>
      {raising && (
        <div className="row">
          <label className="field" style={{ flex: 1 }}>
            My hours a week (now {d.my_capacity})
            <input className="input" type="number" min={d.my_capacity + 1} max={60} value={cap} onChange={(e) => setCap(Number(e.target.value))} />
          </label>
          <button className="btn btn-primary" disabled={busy || cap <= d.my_capacity} onClick={() => resolve("raise_capacity")} style={{ alignSelf: "flex-end" }}>
            Save
          </button>
        </div>
      )}
    </article>
  );
}
