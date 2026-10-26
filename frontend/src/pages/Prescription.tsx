import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { AlertTriangle, FileImage, Trash2 } from "lucide-react";
import { api, type SheetItem } from "../api";
import { DayPicker } from "../components/Chip";
import { useSession } from "../session";

type Upload = { id: number; items: SheetItem[]; used_ai: boolean; message: string };
const ICONS = [
  { v: "walk", l: "Walk" }, { v: "medicine", l: "Medicine" }, { v: "wound", l: "Wound care" }, { v: "visit", l: "Visit" }, { v: "rest", l: "Rest" },
];

function blank(): SheetItem {
  return { title: "", original_line: "", schedule: "", days: [], time: "", icon: "walk" };
}

export default function Prescription() {
  const { toast, refresh, household } = useSession();
  const navigate = useNavigate();
  const [file, setFile] = useState<File | null>(null);
  const [text, setText] = useState("");
  const [reading, setReading] = useState(false);
  const [upload, setUpload] = useState<Upload | null>(null);
  const [rows, setRows] = useState<SheetItem[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const motherName = household?.mother?.name ?? "her";

  const read = async (useSample = false) => {
    setReading(true);
    setError("");
    const fd = new FormData();
    if (useSample) fd.append("use_sample", "true");
    else if (file) fd.append("file", file);
    fd.append("text", useSample ? "" : text);
    try {
      const res = await api.post<Upload>("/api/prescription", fd);
      setUpload(res);
      setRows(res.items.length ? res.items : [blank()]);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setReading(false);
    }
  };

  const update = (i: number, patch: Partial<SheetItem>) => setRows(rows.map((r, j) => (j === i ? { ...r, ...patch } : r)));

  const confirm = async () => {
    if (!upload) return;
    setBusy(true);
    try {
      const res = await api.post<{ created: number }>(`/api/prescription/${upload.id}/confirm`, {
        items: rows.filter((r) => r.title.trim()).map(({ unclear: _u, ...r }) => r),
      });
      await refresh();
      toast(`${res.created} step${res.created === 1 ? "" : "s"} added to ${motherName}'s quest map.`);
      navigate(household?.me.is_mother ? "/home" : "/plan");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  if (!upload) {
    return (
      <div>
        <div className="page-head">
          <h1>The doctor's discharge sheet</h1>
          <p className="muted">With Us reads it, and a person confirms every line. It never adds medical advice.</p>
        </div>
        <div className="stack">
          <div className="grid-halves">
          <label className="card stack-sm" style={{ cursor: "pointer", borderStyle: "dashed", minHeight: 200 }}>
            <span className="row"><FileImage color="var(--rose-600)" aria-hidden="true" /><strong>Upload a photo of the sheet</strong></span>
            <span className="helper">PNG or JPEG. {file ? `Chosen: ${file.name}` : ""}</span>
            <input type="file" accept="image/png,image/jpeg,image/webp" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
          </label>
          <label className="card field">Or paste the text
            <textarea className="input" style={{ minHeight: 140 }} value={text} onChange={(e) => setText(e.target.value)} placeholder="Walk 10 minutes daily" />
          </label>
          </div>
          {error && <p className="error" role="alert">{error}</p>}
          <div className="row">
            <button className="btn btn-primary btn-lg" disabled={reading || (!file && !text.trim())} onClick={() => read(false)}>
              {reading ? "Reading the sheet..." : "Read the sheet"}
            </button>
            <button className="btn" disabled={reading} onClick={() => read(true)}>Use the sample sheet</button>
            <a className="btn btn-ghost" href="/api/prescription/sample" target="_blank" rel="noreferrer">See the sample</a>
          </div>
          {reading && <p className="muted" role="status">Reading each line. This takes a few seconds.</p>}
          <div className="grid-2" style={{ marginTop: 8 }}>
            <section className="card stack">
              <h2>How it works</h2>
              <div className="grid-thirds">
                {[
                  ["1", "We read it", "Gemini lists each instruction exactly as the doctor wrote it. Nothing is added or explained."],
                  ["2", "You check each line", "Every row sits beside the doctor's original words. Unclear lines are marked \"Ask your doctor\"."],
                  ["3", "Quests on her map", `Only after you tap Confirm do they appear as gentle steps on ${motherName}'s quest map.`],
                ].map(([n, t, d]) => (
                  <div className="stack-sm" key={n}>
                    <span className="avatar" style={{ background: "var(--rose-600)" }} aria-hidden="true">{n}</span>
                    <h3>{t}</h3>
                    <p className="helper">{d}</p>
                  </div>
                ))}
              </div>
              <p className="helper">With Us is not a medical device. It never gives medical advice, doses or diagnosis.</p>
            </section>
            <section className="card stack-sm">
              <h3>The sample sheet</h3>
              <p className="helper">A demo document, not a real prescription.</p>
              <img src="/api/prescription/sample" alt="Sample discharge sheet with four instructions" style={{ width: "100%", borderRadius: 12, border: "1px solid var(--line)" }} />
            </section>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="page-head">
        <h1>Check each line</h1>
        <p className="muted">Nothing becomes a quest until you tap Confirm. Edit or remove anything that's not right.</p>
      </div>
      {upload.message && <p className="card card-warn" style={{ marginBottom: 16 }}>{upload.message}</p>}
      <section className="card">
        <div className="confirm-row helper" style={{ fontWeight: 700, paddingTop: 0 }}>
          <span>Quest</span><span>The doctor's original line</span><span />
        </div>
        {rows.map((r, i) => (
          <div className={`confirm-row${r.unclear ? " unclear" : ""}`} key={i}>
            <div className="stack-sm">
              {r.unclear && <span className="pill pill-warn" style={{ alignSelf: "flex-start" }}><AlertTriangle size={14} aria-hidden="true" /> Ask your doctor</span>}
              <input className="input" aria-label="Quest" value={r.title} onChange={(e) => update(i, { title: e.target.value })} />
              <div className="row">
                <input className="input" style={{ flex: 2 }} aria-label="Schedule" placeholder="Schedule, as written" value={r.schedule} onChange={(e) => update(i, { schedule: e.target.value })} />
                <input className="input" style={{ flex: 1 }} type="time" aria-label="Time" value={r.time} onChange={(e) => update(i, { time: e.target.value })} />
                <select className="input" style={{ flex: 1 }} aria-label="Icon" value={r.icon} onChange={(e) => update(i, { icon: e.target.value })}>
                  {ICONS.map((x) => <option key={x.v} value={x.v}>{x.l}</option>)}
                </select>
              </div>
              <DayPicker value={r.days} onChange={(d) => update(i, { days: d })} label="Which days" />
              {r.days.length === 0 && <span className="helper">No days chosen: it shows on her map until she marks it done.</span>}
            </div>
            <div>
              {upload.used_ai || r.original_line ? (
                <p className="doctor-line">"{r.original_line || "Added by hand"}"</p>
              ) : null}
              {!r.original_line && (
                <input className="input" aria-label="Doctor's original line" placeholder="Type the line exactly as written" value={r.original_line} onChange={(e) => update(i, { original_line: e.target.value })} />
              )}
            </div>
            <button className="icon-btn" onClick={() => setRows(rows.filter((_, j) => j !== i))} aria-label={`Remove ${r.title || "row"}`}>
              <Trash2 size={16} />
            </button>
          </div>
        ))}
        <button className="btn btn-sm" style={{ marginTop: 16 }} onClick={() => setRows([...rows, blank()])}>Add an instruction</button>
      </section>
      {error && <p className="error" role="alert" style={{ marginTop: 12 }}>{error}</p>}
      <div className="row" style={{ marginTop: 20 }}>
        <button className="btn" onClick={() => setUpload(null)}>Start again</button>
        <span className="spacer" />
        <button className="btn btn-primary btn-lg" disabled={busy || !rows.some((r) => r.title.trim())} onClick={confirm}>Confirm</button>
      </div>
    </div>
  );
}
