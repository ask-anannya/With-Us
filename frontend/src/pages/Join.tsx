import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api";
import { useSession } from "../session";

export default function Join() {
  const { refresh } = useSession();
  const navigate = useNavigate();
  const [code, setCode] = useState("");
  const [memberId, setMemberId] = useState("");
  const [isNew, setIsNew] = useState(false);
  const [name, setName] = useState("");
  const [role, setRole] = useState("relative");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const go = async () => {
    setBusy(true);
    setError("");
    try {
      const res = await api.post<{ created: boolean }>("/api/session", {
        code, member_id: isNew ? "" : memberId, name: isNew ? name : "", role,
      });
      await refresh();
      navigate(res.created ? "/intake" : "/home");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="narrow">
      <div className="stack">
        <div className="page-head">
          <h1>Join your household</h1>
          <p className="muted">Use the household code someone shared with you.</p>
        </div>
        <label className="field">Household code
          <input className="input" value={code} onChange={(e) => setCode(e.target.value)} placeholder="meera-1234" autoFocus />
        </label>
        <div className="row">
          <button type="button" className="chip" aria-pressed={!isNew} onClick={() => setIsNew(false)}>I have a member ID</button>
          <button type="button" className="chip" aria-pressed={isNew} onClick={() => setIsNew(true)}>I'm new here</button>
        </div>
        {!isNew ? (
          <label className="field">Member ID
            <input className="input" value={memberId} onChange={(e) => setMemberId(e.target.value)} placeholder="ramesh" />
          </label>
        ) : (
          <>
            <label className="field">Your name
              <input className="input" value={name} onChange={(e) => setName(e.target.value)} />
            </label>
            <label className="field">You are her
              <select className="input" value={role} onChange={(e) => setRole(e.target.value)}>
                <option value="partner">Partner</option>
                <option value="parent">Parent</option>
                <option value="relative">Relative or in-law</option>
                <option value="helper">Helper</option>
              </select>
            </label>
          </>
        )}
        {error && <p className="error" role="alert">{error}</p>}
        <div className="row">
          <Link to="/" className="btn">Back</Link>
          <span className="spacer" />
          <button className="btn btn-primary" disabled={busy || !code.trim() || (isNew ? !name.trim() : !memberId.trim())} onClick={go}>
            {isNew ? "Join" : "Sign in"}
          </button>
        </div>
      </div>
    </div>
  );
}
