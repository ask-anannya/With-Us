import { useEffect, useRef, useState } from "react";
import { Lock, Send } from "lucide-react";
import { Link } from "react-router-dom";
import { api, type ChatAction, type ChatReply, type Me } from "../api";
import { HelpCard } from "../components/QuestMap";
import { useSession } from "../session";

const SUGGESTIONS = [
  "What do I have this week?",
  "Help me say I can't do Sundays, kindly.",
  "Who is covering the nights?",
  "When are the protected rest times?",
];

type Msg = { role: "user" | "assistant"; text: string; actions?: ChatAction[] };

export default function Assistant() {
  const { refresh, toast } = useSession();
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [help, setHelp] = useState(false);
  const [aiOff, setAiOff] = useState(false);
  const end = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api.get<Msg[]>("/api/assistant/history").then(setMsgs).catch(() => undefined);
  }, []);
  useEffect(() => {
    end.current?.scrollIntoView({ block: "end" });
  }, [msgs]);

  const send = async () => {
    const m = text.trim();
    if (!m) return;
    setText("");
    setMsgs((x) => [...x, { role: "user", text: m }]);
    setBusy(true);
    try {
      const r = await api.post<ChatReply>("/api/assistant", { message: m });
      if (r.crisis) {
        setMsgs((x) => x.slice(0, -1));
        setHelp(true);
      } else {
        setAiOff(r.used_ai === false);
        setMsgs((x) => [...x, { role: "assistant", text: r.reply, actions: r.actions }]);
      }
    } catch (e) {
      setMsgs((x) => [...x, { role: "assistant", text: (e as Error).message }]);
    } finally {
      setBusy(false);
    }
  };

  const act = async (a: ChatAction, idx: number) => {
    try {
      if (a.type === "accept") await api.post(`/api/me/proposals/${a.proposal_id}/accept`);
      if (a.type === "decline") await api.post(`/api/me/proposals/${a.proposal_id}/decline`, { tell_family: false });
      if (a.type === "update_limit") {
        const me = await api.get<Me>("/api/me");
        const days = me.limits.filter((l) => l.kind === "day").map((l) => l.value);
        const kinds = me.limits.filter((l) => l.kind === "work_kind").map((l) => l.value);
        if (a.kind === "day" && a.value && !days.includes(a.value)) days.push(a.value);
        if (a.kind === "work_kind" && a.value && !kinds.includes(a.value)) kinds.push(a.value);
        await api.put("/api/me/limits", { days, work_kinds: kinds });
      }
      toast("Done.");
      setMsgs((x) => x.map((m, i) => (i === idx ? { ...m, actions: [] } : m)));
      await refresh();
    } catch (e) {
      toast((e as Error).message);
    }
  };

  return (
    <div>
      <div className="page-head">
        <h1>Your assistant</h1>
        <p className="lock-head"><Lock size={18} aria-hidden="true" /> Only you can see this conversation.</p>
      </div>
      <div className="grid-2">
        <div className="stack">
          {aiOff && <p className="card card-warn">Your assistant can't think clearly right now, so it's showing simple options instead.</p>}
          <section className="card chat" aria-live="polite">
            {msgs.length === 0 && (
              <p className="muted">Ask about your week, get help saying no kindly, or put a limit into words. It never shares anyone's reasons, including yours.</p>
            )}
            {msgs.map((m, i) => (
              <div key={i} className="stack-sm" style={{ alignItems: m.role === "user" ? "flex-end" : "flex-start" }}>
                <div className={`bubble ${m.role}`}>{m.text}</div>
                {m.actions && m.actions.length > 0 && (
                  <div className="row">
                    {m.actions.map((a, j) => (
                      <button key={j} className={`btn btn-sm${a.type === "accept" ? " btn-primary" : ""}`} onClick={() => act(a, i)}>{a.label}</button>
                    ))}
                  </div>
                )}
              </div>
            ))}
            {busy && <div className="bubble assistant muted">Thinking...</div>}
            <div ref={end} />
          </section>
          <form className="row" onSubmit={(e) => { e.preventDefault(); send(); }}>
            <label htmlFor="msg" className="visually-hidden">Message</label>
            <input id="msg" className="input" style={{ flex: 1 }} value={text} onChange={(e) => setText(e.target.value)} placeholder="What do I have this week?" autoComplete="off" />
            <button className="btn btn-primary" disabled={busy || !text.trim()} aria-label="Send"><Send size={18} /></button>
          </form>
        </div>
        <aside className="stack sticky-side">
          <section className="card card-tint stack-sm">
            <h3>Try asking</h3>
            {SUGGESTIONS.map((q) => (
              <button key={q} className="btn btn-sm" style={{ justifyContent: "flex-start", textAlign: "left" }} onClick={() => setText(q)}>
                {q}
              </button>
            ))}
          </section>
          <section className="card stack-sm">
            <h3>What it can see</h3>
            <p className="helper">Your own limits and reasons, your instructions, what's waiting on you, and the published plan.</p>
            <p className="helper">Never anyone else's reasons, requests or chats. It can't change anything until you tap a button.</p>
            <Link className="btn btn-sm" to="/control" style={{ alignSelf: "flex-start" }}>See what your assistant is told</Link>
          </section>
        </aside>
      </div>
      {help && <HelpCard onClose={() => setHelp(false)} />}
    </div>
  );
}
