import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api";
import { BabyIcon } from "../components/BabyIcon";
import { useSession } from "../session";

const ROLES = [
  { v: "partner", l: "Partner" }, { v: "parent", l: "Parent" }, { v: "relative", l: "Relative or in-law" }, { v: "helper", l: "Helper" },
];

export default function Create() {
  const { refresh } = useSession();
  const navigate = useNavigate();
  const [step, setStep] = useState(0);
  const [baby, setBaby] = useState<"girl" | "boy" | null>(null);
  const [motherName, setMotherName] = useState("");
  const [babyName, setBabyName] = useState("");
  const [arrived, setArrived] = useState("");
  const [notes, setNotes] = useState("");
  const [iAmMother, setIAmMother] = useState(true);
  const [myName, setMyName] = useState("");
  const [myRole, setMyRole] = useState("partner");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [created, setCreated] = useState<{ code: string; member_id: string } | null>(null);

  const create = async () => {
    setBusy(true);
    setError("");
    try {
      const res = await api.post<{ code: string; member_id: string }>("/api/households", {
        baby_type: baby, mother_name: motherName, baby_name: babyName, baby_arrived: arrived, notes,
        creator_is_mother: iAmMother, creator_name: myName, creator_role: myRole,
      });
      setCreated(res);
      await refresh();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="narrow">
      <div className="steps" aria-hidden="true">
        {[0, 1, 2].map((i) => <span key={i} className={i <= step ? "on" : ""} />)}
      </div>

      {step === 0 && (
        <div className="stack">
          <div className="page-head">
            <h1>Welcome, little one</h1>
            <p className="muted">Tell us about your baby.</p>
          </div>
          <div className="baby-cards" role="radiogroup" aria-label="Your baby">
            {(["girl", "boy"] as const).map((t) => (
              <button key={t} type="button" role="radio" aria-checked={baby === t} className="baby-card" onClick={() => setBaby(t)}>
                <BabyIcon type={t} size={96} />
                Baby {t}
              </button>
            ))}
          </div>
          <div className="row">
            <Link to="/" className="btn">Back</Link>
            <span className="spacer" />
            <button className="btn btn-primary" disabled={!baby} onClick={() => setStep(1)}>Continue</button>
          </div>
        </div>
      )}

      {step === 1 && (
        <div className="stack">
          <div className="page-head">
            <h1>Who is recovering?</h1>
            <p className="muted">With Us plans the week around her.</p>
          </div>
          <label className="field">Her name
            <input className="input" value={motherName} onChange={(e) => setMotherName(e.target.value)} autoFocus />
          </label>
          <label className="field">Baby's name <span className="helper">optional</span>
            <input className="input" value={babyName} onChange={(e) => setBabyName(e.target.value)} />
          </label>
          <label className="field">Date the baby arrived
            <input className="input" type="date" value={arrived} onChange={(e) => setArrived(e.target.value)} />
          </label>
          <label className="field">Anything the family should keep in mind <span className="helper">optional</span>
            <textarea className="input" value={notes} onChange={(e) => setNotes(e.target.value)} />
          </label>
          <div className="row">
            <button className="btn" onClick={() => setStep(0)}>Back</button>
            <span className="spacer" />
            <button className="btn btn-primary" disabled={!motherName.trim()} onClick={() => setStep(2)}>Continue</button>
          </div>
        </div>
      )}

      {step === 2 && !created && (
        <div className="stack">
          <div className="page-head">
            <h1>And you?</h1>
            <p className="muted">You'll set what you can take on next, privately.</p>
          </div>
          <div className="row">
            <button type="button" className="chip" aria-pressed={iAmMother} onClick={() => setIAmMother(true)}>I'm {motherName || "her"}</button>
            <button type="button" className="chip" aria-pressed={!iAmMother} onClick={() => setIAmMother(false)}>I'm someone helping her</button>
          </div>
          {!iAmMother && (
            <>
              <label className="field">Your name
                <input className="input" value={myName} onChange={(e) => setMyName(e.target.value)} />
              </label>
              <label className="field">You are her
                <select className="input" value={myRole} onChange={(e) => setMyRole(e.target.value)}>
                  {ROLES.map((r) => <option key={r.v} value={r.v}>{r.l}</option>)}
                </select>
              </label>
            </>
          )}
          {error && <p className="error" role="alert">{error}</p>}
          <div className="row">
            <button className="btn" onClick={() => setStep(1)}>Back</button>
            <span className="spacer" />
            <button className="btn btn-primary" disabled={busy || (!iAmMother && !myName.trim())} onClick={create}>Create household</button>
          </div>
        </div>
      )}

      {created && (
        <div className="stack">
          <div className="page-head">
            <h1>Your household is ready</h1>
            <p className="muted">Share the code with family. Each person keeps their own member ID.</p>
          </div>
          <CodeCard code={created.code} memberId={created.member_id} />
          <button className="btn btn-primary btn-lg" onClick={() => navigate("/intake")}>Set what I can take on</button>
        </div>
      )}
    </div>
  );
}

export function CodeCard({ code, memberId }: { code: string; memberId: string }) {
  const { toast } = useSession();
  const copy = (v: string) => navigator.clipboard?.writeText(v).then(() => toast("Copied"), () => toast(v));
  return (
    <div className="card stack-sm">
      <div className="row"><span style={{ width: 160 }} className="helper">Household code</span><strong style={{ fontSize: 22 }}>{code}</strong><span className="spacer" /><button className="btn btn-sm" onClick={() => copy(code)}>Copy</button></div>
      <div className="row"><span style={{ width: 160 }} className="helper">Your member ID</span><strong style={{ fontSize: 22 }}>{memberId}</strong><span className="spacer" /><button className="btn btn-sm" onClick={() => copy(memberId)}>Copy</button></div>
    </div>
  );
}
