import { Check } from "lucide-react";
import type { QuestProgress } from "../api";
import { Bunny, QuestIcon } from "./QuestMap";

/** The mother's quests, compact, shown only to people she chose to share with. */
export function SharedQuests({ p }: { p: QuestProgress }) {
  const done = p.done ?? 0;
  const total = p.total ?? p.quests.length;
  const pct = total ? Math.round((done / total) * 100) : 0;
  return (
    <section className="card stack-sm">
      <div className="row" style={{ justifyContent: "space-between" }}>
        <h3>{p.name}'s quests today</h3>
        <span className="pill" style={{ paddingLeft: 4 }}>
          <Bunny size={22} />
          {p.bunnies ?? 0} {p.bunnies === 1 ? "bunny" : "bunnies"}
        </span>
      </div>
      <div className="row" style={{ justifyContent: "space-between" }}>
        <span className="helper">{done} of {total} done</span>
        {total > 0 && done === total && <span className="helper">All done today</span>}
      </div>
      <div className="progress" role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100} aria-label={`${done} of ${total} steps done`}>
        <span style={{ width: `${pct}%` }} />
      </div>
      {total === 0 ? (
        <p className="helper">No steps on her map today.</p>
      ) : (
        <ul className="quest-list">
          {p.quests.map((q) => (
            <li key={q.key} className={q.done ? "done" : ""}>
              <span className="quest-list-icon" aria-hidden="true">
                {q.done ? <Check size={14} strokeWidth={3} /> : <QuestIcon icon={q.icon} size={14} />}
              </span>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div className="quest-list-title">{q.title}</div>
                <div className="helper" style={{ fontSize: 13 }}>
                  {q.kind === "rest" ? (q.covering || "Rest") : [q.schedule, q.time].filter(Boolean).join(" · ") || "Today"}
                </div>
              </div>
              <span className="visually-hidden">{q.done ? "done" : "not yet"}</span>
            </li>
          ))}
        </ul>
      )}
      <p className="helper" style={{ fontSize: 13 }}>Shared by {p.name}. Keep it gentle: no nudging.</p>
    </section>
  );
}
