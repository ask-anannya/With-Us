import { DAY_NAMES, WEEKDAYS, WORK_KINDS } from "../api";

export function Chip({ on, onClick, children }: { on: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button type="button" className="chip" aria-pressed={on} onClick={onClick}>
      {children}
    </button>
  );
}

function toggle(list: string[], v: string) {
  return list.includes(v) ? list.filter((x) => x !== v) : [...list, v];
}

export function DayPicker({ value, onChange, label }: { value: string[]; onChange: (v: string[]) => void; label: string }) {
  return (
    <div className="chips" role="group" aria-label={label}>
      {WEEKDAYS.map((d) => (
        <Chip key={d} on={value.includes(d)} onClick={() => onChange(toggle(value, d))}>
          <span aria-hidden="true">{d}</span>
          <span className="visually-hidden">{DAY_NAMES[d]}</span>
        </Chip>
      ))}
    </div>
  );
}

export function WorkKindChips({ value, onChange, label }: { value: string[]; onChange: (v: string[]) => void; label: string }) {
  return (
    <div className="chips" role="group" aria-label={label}>
      {WORK_KINDS.map((k) => (
        <Chip key={k} on={value.includes(k)} onClick={() => onChange(toggle(value, k))}>
          {k}
        </Chip>
      ))}
    </div>
  );
}
