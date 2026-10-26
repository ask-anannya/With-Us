import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, type Quest, type QuestDay } from "../api";
import { BabyIcon } from "../components/BabyIcon";
import { BunnyJar, HelpCard, QuestMap, QuestSheet } from "../components/QuestMap";
import { useSession } from "../session";

function greeting() {
  const h = new Date().getHours();
  return h < 12 ? "Good morning" : h < 17 ? "Good afternoon" : "Good evening";
}

export default function MotherHome() {
  const { toast } = useSession();
  const [day, setDay] = useState<QuestDay | null>(null);
  const [open, setOpen] = useState<Quest | null>(null);
  const [busy, setBusy] = useState(false);
  const [hopping, setHopping] = useState(false);
  const [help, setHelp] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(() => {
    api.get<QuestDay>("/api/quests/today").then(setDay).catch((e) => setError((e as Error).message));
  }, []);
  useEffect(load, [load]);

  const done = async () => {
    if (!open) return;
    setBusy(true);
    try {
      const res = await api.post<{ bunnies: number }>(`/api/quests/${encodeURIComponent(open.key)}/done`);
      setOpen(null);
      setHopping(true);
      window.setTimeout(() => setHopping(false), 1200);
      setDay((d) => d && { ...d, bunnies: res.bunnies, quests: d.quests.map((q) => (q.key === open.key ? { ...q, done: true } : q)) });
    } catch (e) {
      toast((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  if (error) return <p className="error">{error}</p>;
  if (!day) return <p className="muted">Loading your day...</p>;
  const left = day.quests.filter((q) => !q.done).length;

  return (
    <div className="stack" style={{ gap: 28 }}>
      <header className="quest-head">
        <span className="baby"><BabyIcon type={day.baby_type} size={64} /></span>
        <h1 style={{ paddingRight: 80 }}>{greeting()}, {day.name}</h1>
        <p style={{ fontSize: 19, marginTop: 8 }}>
          {left === 0
            ? "Every step today is done. Rest well. Everything else is covered."
            : `Today has ${left} small step${left === 1 ? "" : "s"}. Everything else is covered.`}
        </p>
      </header>

      <div className="mother-grid">
      <div className="stack">
      {!day.has_sheet && (
        <div className="card card-tint row">
          <p style={{ flex: 1 }}>Your doctor's steps will appear here once someone adds the discharge sheet.</p>
          <Link className="btn" to="/prescription">Add the sheet</Link>
        </div>
      )}

      <div className="quest-map-wrap">
        <BunnyJar count={day.bunnies} hopping={hopping} />
        <QuestMap quests={day.quests} onOpen={setOpen} />
      </div>
      </div>

      <aside className="stack sticky-side">
      <section className="card stack-sm">
        <h2>Your week is covered</h2>
        {day.covered.length === 0 && day.arranging.length === 0 && (
          <p className="muted">The family is still setting up the week.</p>
        )}
        <div className="task-list">
          {day.covered.map((c) => (
            <div className="task-row" key={c.title}>
              <span style={{ flex: 1, fontWeight: 600 }}>{c.title}</span>
              <span>{c.owner}</span>
            </div>
          ))}
          {day.arranging.map((t) => (
            <div className="task-row" key={t}>
              <span style={{ flex: 1, fontWeight: 600 }}>{t}</span>
              <span className="pill">Being arranged</span>
            </div>
          ))}
          {day.outside_help.map((t) => (
            <div className="task-row" key={t}>
              <span style={{ flex: 1, fontWeight: 600 }}>{t}</span>
              <span className="pill">Outside help</span>
            </div>
          ))}
        </div>
      </section>

      <button className="btn btn-ghost" style={{ alignSelf: "center" }} onClick={() => setHelp(true)}>
        Need to talk to someone?
      </button>
      </aside>
      </div>

      {open && <QuestSheet quest={open} onClose={() => setOpen(null)} onDone={done} busy={busy} />}
      {help && <HelpCard onClose={() => setHelp(false)} />}
    </div>
  );
}
