import { Lock } from "lucide-react";

export function PrivateReasonBox({ value, onChange, id = "reason" }: { value: string; onChange: (v: string) => void; id?: string }) {
  return (
    <div className="reason-box">
      <label htmlFor={id} style={{ fontWeight: 700 }}>
        Why, only if you want to say it
      </label>
      <p className="note">
        <Lock size={16} aria-hidden="true" style={{ marginTop: 3, flex: "none" }} />
        Only you and your assistant see this. Your family sees the limit, never the reason.
      </p>
      <textarea id={id} className="input" value={value} onChange={(e) => onChange(e.target.value)} placeholder="Optional" />
    </div>
  );
}
