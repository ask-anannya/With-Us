import { Baby, Car, Home, HeartPulse } from "lucide-react";
import { whenLabel, type Resp } from "../api";
import { Avatar } from "./LoadBar";

export function KindIcon({ r }: { r: Resp }) {
  const Icon = r.kind === "recovery" ? HeartPulse : r.travel || r.work_kind === "Driving" ? Car : r.kind === "baby" ? Baby : Home;
  return (
    <span className="icon-btn" style={{ cursor: "default", flex: "none" }} aria-hidden="true">
      <Icon size={18} color="var(--rose-600)" />
    </span>
  );
}

export function TaskRow({ r, owner, status, right }: {
  r: Resp; owner?: { name: string; colour: string } | null; status?: "arranging" | "outside" | "needs" | "asked"; right?: React.ReactNode;
}) {
  return (
    <div className="task-row">
      <KindIcon r={r} />
      <div style={{ flex: 1, minWidth: 0 }}>
        <div className="title">{r.title}</div>
        <div className="helper">
          {whenLabel(r)}
          {r.work_kind ? ` · ${r.work_kind}` : ""}
        </div>
      </div>
      {status === "arranging" && <span className="pill">Being arranged</span>}
      {status === "asked" && <span className="pill">Asked of you</span>}
      {status === "outside" && <span className="pill">Outside help</span>}
      {status === "needs" && <span className="pill pill-warn">Needs someone</span>}
      {owner && (
        <span className="row" style={{ gap: 8 }}>
          <Avatar name={owner.name} colour={owner.colour} size={28} />
          <span style={{ fontWeight: 600 }}>{owner.name}</span>
        </span>
      )}
      {right}
    </div>
  );
}
