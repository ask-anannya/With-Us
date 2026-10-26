import type { PlanMember } from "../api";

export function initials(name: string) {
  return name.split(/\s+/).map((p) => p[0]).join("").slice(0, 2).toUpperCase();
}

export function Avatar({ name, colour, size = 36 }: { name: string; colour: string; size?: number }) {
  return (
    <span className="avatar" style={{ background: `var(${colour})`, width: size, height: size }} aria-hidden="true">
      {initials(name)}
    </span>
  );
}

/** One rounded bar split by member colour. Widths show each person's share of the work done. */
export function LoadBar({ members }: { members: PlanMember[] }) {
  const counted = members.filter((m) => !m.is_mother);
  const total = counted.reduce((s, m) => s + m.hours, 0) || 1;
  return (
    <div>
      <div className="loadbar" role="img" aria-label="How the work is shared">
        {counted.map((m) => (
          <span key={m.id} style={{ width: `${(m.hours / total) * 100}%`, background: `var(${m.colour})` }} title={m.name} />
        ))}
      </div>
      <div className="legend">
        {counted.map((m) => (
          <div className="legend-item" key={m.id}>
            <Avatar name={m.name} colour={m.colour} size={32} />
            <div>
              <div style={{ fontWeight: 700 }}>{m.name}</div>
              <div className="helper">
                {m.burden_pct}% of their own capacity, {m.tasks} task{m.tasks === 1 ? "" : "s"}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
