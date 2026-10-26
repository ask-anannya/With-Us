import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Sparkles, Trash2 } from "lucide-react";
import { api, timeLabel, type Me } from "../api";
import { DayPicker, WorkKindChips } from "../components/Chip";
import { PrivateReasonBox } from "../components/PrivateReasonBox";
import { Sheet } from "../components/QuestMap";
import { useSession } from "../session";

type Rest = { days: string[]; start: string; end: string };
const ALL = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

export function IntakeForm({ onSaved, submitLabel }: { onSaved: () => void; submitLabel: string }) {
  const { household, refresh, toast } = useSession();
  const [me, setMe] = useState<Me | null>(null);
  const [cap, setCap] = useState(8);
  const [days, setDays] = useState<string[]>([]);
  const [kinds, setKinds] = useState<string[]>([]);
  const [reason, setReason] = useState("");
  const [rests, setRests] = useState<Rest[]>([]);
  const [shareProgress, setShareProgress] = useState(false);
  const [shareWith, setShareWith] = useState<number[]>([]);
  const [sharingOn, setSharingOn] = useState(false);
  const [assistantOpen, setAssistantOpen] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.get<Me>("/api/me").then((m) => {
      setMe(m);
      setCap(m.capacity_hours);
      setDays(m.limits.filter((l) => l.kind === "day").map((l) => l.value));
      setKinds(m.limits.filter((l) => l.kind === "work_kind").map((l) => l.value));
      setReason(m.general_reason || m.limits.find((l) => l.reason)?.reason || "");
      setRests(m.rest_windows ?? []);
      setShareProgress(m.sharing?.share_progress ?? false);
      setShareWith(m.sharing?.share_with ?? []);
    });
  }, []);
  useEffect(() => {
    if (!household || !me) return;
    setSharingOn(me.is_mother ? household.sharing.mother : household.sharing.partner);
  }, [household, me]);

  if (!me || !household) return <p className="muted">Loading...</p>;
  const isMother = me.is_mother;
  const canShare = isMother || me.role === "partner";
  const others = household.members.filter((m) => m.id !== me.id);

  const save = async () => {
    setBusy(true);
    setError("");
    try {
      await api.put("/api/me/profile", { capacity_hours: cap });
      await api.put("/api/me/limits", { days, work_kinds: kinds, rest_windows: isMother ? rests : undefined });
      const fresh = await api.get<Me>("/api/me");
      // keep a reason only where the person wrote one; the general box covers all limits
      await api.put("/api/me/reasons/general", { text: reason });
      for (const l of fresh.limits) {
        if (l.reason && l.reason !== reason) continue;
        if (l.reason === reason && reason) await api.put(`/api/me/reasons/${l.id}`, { text: "" });
      }
      if (isMother) await api.put("/api/me/quest-sharing", { share_progress: shareProgress, share_with: shareWith });
      if (canShare) await api.patch("/api/household/sharing", { on: sharingOn });
      await refresh();
      toast("Saved. Only your limits are shared, never your reasons.");
      onSaved();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="stack" style={{ gap: 28 }}>
      <button className="btn" style={{ alignSelf: "flex-start" }} onClick={() => setAssistantOpen(true)}>
        <Sparkles size={18} aria-hidden="true" /> Tell my assistant instead
      </button>

      <section className="stack-sm">
        <label htmlFor="cap" style={{ fontWeight: 700, fontSize: 18 }}>
          How many hours a week can you give? <span style={{ color: "var(--rose-600)" }}>{cap} hours</span>
        </label>
        <input id="cap" type="range" min={0} max={40} step={1} value={cap} onChange={(e) => setCap(Number(e.target.value))} />
        <p className="helper">We measure your share against this, not an even split.</p>
        {isMother && (
          <p className="pill" style={{ alignSelf: "flex-start" }}>
            We plan for less than this, so you can rest. Planned: {cap / 2} hours.
          </p>
        )}
      </section>

      <section className="stack-sm">
        <h3>Days you can't help</h3>
        <DayPicker value={days} onChange={setDays} label="Days you can't help" />
      </section>

      <section className="stack-sm">
        <h3>Kinds of work you can't take</h3>
        <WorkKindChips value={kinds} onChange={setKinds} label="Kinds of work you can't take" />
      </section>

      <PrivateReasonBox value={reason} onChange={setReason} />

      {isMother && (
        <section className="card stack">
          <h3>Your rest windows</h3>
          <p className="helper">Nothing is ever planned for you in these times.</p>
          {rests.map((r, i) => (
            <div className="row" key={i}>
              <label className="field" style={{ flex: 1 }}>From
                <input className="input" type="time" value={r.start} onChange={(e) => setRests(rests.map((x, j) => (j === i ? { ...x, start: e.target.value } : x)))} />
              </label>
              <label className="field" style={{ flex: 1 }}>To
                <input className="input" type="time" value={r.end} onChange={(e) => setRests(rests.map((x, j) => (j === i ? { ...x, end: e.target.value } : x)))} />
              </label>
              <span className="helper" style={{ alignSelf: "flex-end", paddingBottom: 12 }}>{timeLabel(r.start)} to {timeLabel(r.end)}, every day</span>
              <button className="icon-btn" style={{ alignSelf: "flex-end" }} onClick={() => setRests(rests.filter((_, j) => j !== i))} aria-label="Remove rest window">
                <Trash2 size={16} />
              </button>
            </div>
          ))}
          <button className="btn btn-sm" style={{ alignSelf: "flex-start" }} onClick={() => setRests([...rests, { days: ALL, start: "14:00", end: "16:00" }])}>
            Add a rest window
          </button>
          <h3 style={{ marginTop: 8 }}>Share my quest progress with</h3>
          <label className="switch">
            <input type="checkbox" checked={shareProgress} onChange={(e) => setShareProgress(e.target.checked)} />
            <span>Let chosen people see today's steps and which ones are done</span>
          </label>
          {shareProgress && (
            <div className="chips">
              {others.map((m) => (
                <button key={m.id} type="button" className="chip" aria-pressed={shareWith.includes(m.id)}
                  onClick={() => setShareWith(shareWith.includes(m.id) ? shareWith.filter((x) => x !== m.id) : [...shareWith, m.id])}>
                  {m.name}
                </button>
              ))}
            </div>
          )}
        </section>
      )}

      {canShare && (
        <section className="card card-tint stack-sm">
          <label className="switch">
            <input type="checkbox" checked={sharingOn} onChange={(e) => setSharingOn(e.target.checked)} />
            <span style={{ fontWeight: 700 }}>Let With Us share out the work</span>
          </label>
          <p className="helper">The plan starts once both {isMother ? "you and your partner" : "you and the mother"} turn this on.</p>
        </section>
      )}

      {error && <p className="error" role="alert">{error}</p>}
      <button className="btn btn-primary btn-lg" disabled={busy} onClick={save}>{submitLabel}</button>

      {assistantOpen && (
        <AssistantIntake
          onClose={() => setAssistantOpen(false)}
          onFill={(f) => {
            setCap(f.capacity_hours);
            setDays(f.blocked_days);
            setKinds(f.blocked_work_kinds);
            if (f.private_reason) setReason(f.private_reason);
            setAssistantOpen(false);
            toast("Filled in. Check everything before you save.");
          }}
        />
      )}
    </div>
  );
}

type Fields = { capacity_hours: number; blocked_days: string[]; blocked_work_kinds: string[]; will_take: string[]; private_reason: string };

function AssistantIntake({ onClose, onFill }: { onClose: () => void; onFill: (f: Fields) => void }) {
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");
  const read = async () => {
    setBusy(true);
    setMsg("");
    try {
      const res = await api.post<{ ok: boolean; fields?: Fields; message?: string }>("/api/intake/read", { text });
      if (res.ok && res.fields) onFill(res.fields);
      else setMsg(res.message || "Your assistant can't read that right now. The form works just the same.");
    } catch (e) {
      setMsg((e as Error).message);
    } finally {
      setBusy(false);
    }
  };
  return (
    <Sheet onClose={onClose} label="Tell my assistant">
      <div className="stack">
        <h2>Tell your assistant</h2>
        <p className="helper">Say it however it comes out. Your assistant fills the form, and you check it before saving. Anything that sounds like a reason stays private.</p>
        <textarea className="input" style={{ minHeight: 140 }} value={text} onChange={(e) => setText(e.target.value)}
          placeholder="I have client meetings every Thursday and Friday and I'm wiped out after. I can do weekends and cooking." autoFocus />
        {msg && <p className="error" role="alert">{msg}</p>}
        <button className="btn btn-primary btn-lg" disabled={busy || !text.trim()} onClick={read}>
          {busy ? "Reading..." : "Fill the form for me"}
        </button>
      </div>
    </Sheet>
  );
}

export default function Intake() {
  const navigate = useNavigate();
  const { household } = useSession();
  return (
    <div className="narrow">
      <div className="page-head">
        <h1>What can you take on?</h1>
        <p className="muted">Privately. {household?.mother ? `It helps With Us build a fair week around ${household.mother.name}.` : ""}</p>
      </div>
      <IntakeForm onSaved={() => navigate("/home")} submitLabel="Save and continue" />
    </div>
  );
}
