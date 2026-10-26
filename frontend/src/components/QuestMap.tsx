import { useEffect, useRef } from "react";
import { Bed, Footprints, Pill, Stethoscope, Bandage, X, Check } from "lucide-react";
import type { Quest } from "../api";

const ICONS: Record<string, typeof Footprints> = {
  walk: Footprints, medicine: Pill, rest: Bed, wound: Bandage, visit: Stethoscope,
};

export function QuestIcon({ icon, size = 26 }: { icon: string; size?: number }) {
  const Icon = ICONS[icon] ?? Footprints;
  return <Icon size={size} aria-hidden="true" />;
}

const STEP = 130;
const WIDTH = 640;

/** A winding path of round stepping stones, one per quest today. */
export function QuestMap({ quests, onOpen }: { quests: Quest[]; onOpen: (q: Quest) => void }) {
  const current = quests.findIndex((q) => !q.done);
  const pts = quests.map((_, i) => ({ x: i % 2 === 0 ? 170 : WIDTH - 170, y: 70 + i * STEP }));
  let d = "";
  pts.forEach((p, i) => {
    if (i === 0) d = `M ${p.x} ${p.y}`;
    else {
      const prev = pts[i - 1];
      const my = (prev.y + p.y) / 2;
      d += ` C ${prev.x} ${my}, ${p.x} ${my}, ${p.x} ${p.y}`;
    }
  });
  const height = Math.max(160, 70 + (quests.length - 1) * STEP + 80);
  return (
    <div className="quest-map">
      <svg viewBox={`0 0 ${WIDTH} ${height}`} role="list" aria-label="Today's steps">
        {quests.length > 1 && (
          <path d={d} fill="none" stroke="var(--pink-200)" strokeWidth="14" strokeLinecap="round" strokeDasharray="2 22" />
        )}
        {quests.map((q, i) => {
          const p = pts[i];
          const left = p.x < WIDTH / 2;
          return (
            <g
              key={q.key}
              role="listitem"
              tabIndex={0}
              className={`stone${q.done ? " done" : ""}${i === current ? " current" : ""}`}
              onClick={() => onOpen(q)}
              onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && (e.preventDefault(), onOpen(q))}
              aria-label={`${q.title}${q.time ? `, ${q.time}` : ""}${q.done ? ", done" : ""}`}
            >
              {i === current && <circle className="pulse" cx={p.x} cy={p.y} r="38" />}
              <circle className="ring" cx={p.x} cy={p.y} r="38" />
              <g className="stone-icon" transform={`translate(${p.x - 14} ${p.y - 14})`}>
                {q.done ? <Check size={28} strokeWidth={3} /> : <QuestIcon icon={q.icon} size={28} />}
              </g>
              <text className="stone-label" x={left ? p.x + 58 : p.x - 58} y={p.y - 2} textAnchor={left ? "start" : "end"}>
                {q.title.length > 34 ? q.title.slice(0, 33) + "…" : q.title}
              </text>
              {q.time && q.kind !== "rest" && (
                <text className="stone-time" x={left ? p.x + 58 : p.x - 58} y={p.y + 20} textAnchor={left ? "start" : "end"}>
                  {q.time}
                </text>
              )}
            </g>
          );
        })}
      </svg>
    </div>
  );
}

export function Sheet({ onClose, label, children }: { onClose: () => void; label: string; children: React.ReactNode }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const prev = document.activeElement as HTMLElement | null;
    ref.current?.focus();
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("keydown", onKey);
      prev?.focus?.();
    };
  }, [onClose]);
  return (
    <div className="sheet-backdrop" onClick={onClose}>
      <div className="sheet" role="dialog" aria-modal="true" aria-label={label} tabIndex={-1} ref={ref} onClick={(e) => e.stopPropagation()}>
        <div className="row" style={{ justifyContent: "flex-end", marginBottom: -12 }}>
          <button className="icon-btn" onClick={onClose} aria-label="Close">
            <X size={18} />
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}

export function QuestSheet({ quest, onClose, onDone, busy }: { quest: Quest; onClose: () => void; onDone: () => void; busy: boolean }) {
  return (
    <Sheet onClose={onClose} label={quest.title}>
      <div className="stack">
        <span className="icon-btn" style={{ width: 56, height: 56, background: "var(--pink-100)", color: "var(--rose-700)" }}>
          <QuestIcon icon={quest.icon} />
        </span>
        <h2>{quest.title}</h2>
        {quest.time && <p className="muted">{quest.time}</p>}
        {quest.original_line && (
          <div className="stack-sm">
            <span className="helper" style={{ fontWeight: 600 }}>From your doctor</span>
            <p className="doctor-line">"{quest.original_line}"</p>
          </div>
        )}
        {quest.kind === "rest" && <p>This time is yours. Nothing is planned for you now.</p>}
        <p style={{ fontWeight: 600 }}>{quest.covering || "Everything else is covered."}</p>
        {quest.done ? (
          <p className="pill" style={{ alignSelf: "flex-start" }}>Done today. Lovely.</p>
        ) : (
          <button className="btn btn-primary btn-lg btn-block" onClick={onDone} disabled={busy}>
            I did it
          </button>
        )}
      </div>
    </Sheet>
  );
}

export function Bunny({ size = 40 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 40 40" aria-hidden="true">
      <ellipse cx="15" cy="9" rx="3.5" ry="8" fill="var(--surface)" stroke="var(--ink)" strokeWidth="1.8" />
      <ellipse cx="25" cy="9" rx="3.5" ry="8" fill="var(--surface)" stroke="var(--ink)" strokeWidth="1.8" />
      <ellipse cx="15" cy="10" rx="1.4" ry="5" fill="var(--pink-200)" />
      <ellipse cx="25" cy="10" rx="1.4" ry="5" fill="var(--pink-200)" />
      <circle cx="20" cy="25" r="11" fill="var(--surface)" stroke="var(--ink)" strokeWidth="1.8" />
      <circle cx="16" cy="23" r="1.4" fill="var(--ink)" />
      <circle cx="24" cy="23" r="1.4" fill="var(--ink)" />
      <circle cx="14" cy="27.5" r="2" fill="var(--pink-200)" />
      <circle cx="26" cy="27.5" r="2" fill="var(--pink-200)" />
      <path d="M18.5 27 q1.5 1.5 3 0" fill="none" stroke="var(--ink)" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}

export function BunnyJar({ count, hopping }: { count: number; hopping: boolean }) {
  return (
    <div className="bunny-jar" aria-live="polite">
      {hopping && (
        <span className="bunny-hop">
          <Bunny size={36} />
        </span>
      )}
      <svg width="72" height="84" viewBox="0 0 72 84" aria-hidden="true">
        <rect x="16" y="4" width="40" height="10" rx="4" fill="var(--pink-200)" stroke="var(--ink)" strokeWidth="2" />
        <path d="M12 18 h48 q4 0 4 6 v46 q0 10 -10 10 h-36 q-10 0 -10 -10 v-46 q0 -6 4 -6 z" fill="var(--pink-50)" stroke="var(--ink)" strokeWidth="2" />
        {Array.from({ length: Math.min(count, 6) }).map((_, i) => (
          <circle key={i} cx={24 + (i % 3) * 12} cy={68 - Math.floor(i / 3) * 12} r="5" fill="var(--pink-400)" />
        ))}
      </svg>
      <span className="count">{count} {count === 1 ? "bunny" : "bunnies"}</span>
    </div>
  );
}

export function HelpCard({ onClose }: { onClose: () => void }) {
  return (
    <Sheet onClose={onClose} label="Talk to someone">
      <div className="stack">
        <h2>You don't have to carry this alone.</h2>
        <p>Talk to someone now: <strong>Tele-MANAS 14416</strong> (India), or 1800-891-4416. Free, any time of day, in many languages.</p>
        <a className="btn btn-primary btn-lg" href="tel:14416">Call 14416</a>
        <p className="helper">If you are in danger right now, call 112.</p>
      </div>
    </Sheet>
  );
}
