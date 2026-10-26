import { useState } from "react";
import { NavLink, Navigate, Outlet, useNavigate } from "react-router-dom";
import { Bell, CalendarDays, Home, Info, LogOut, MessageCircle, Moon, Plus, Settings, Sun } from "lucide-react";
import { api, WORK_KINDS } from "../api";
import { useSession, useTheme } from "../session";
import { BabyIcon, Logo } from "./BabyIcon";
import { DayPicker } from "./Chip";
import { Avatar } from "./LoadBar";
import { Sheet } from "./QuestMap";

const NAV = [
  { to: "/home", label: "Home", icon: Home },
  { to: "/needs-you", label: "Needs you", icon: Bell, badge: true },
  { to: "/plan", label: "Plan", icon: CalendarDays },
  { to: "/assistant", label: "Assistant", icon: MessageCircle },
  { to: "/control", label: "Control panel", icon: Settings },
];

export function Shell() {
  const { household, loading, needsYou, signOut } = useSession();
  const [theme, toggleTheme] = useTheme();
  const [adding, setAdding] = useState(false);
  const navigate = useNavigate();
  if (loading) return <div className="narrow muted">Loading your household...</div>;
  if (!household) return <Navigate to="/" replace />;
  const me = household.me;
  const mother = household.mother;

  const out = async () => {
    await signOut();
    navigate("/");
  };

  return (
    <div className="shell">
      <aside className="sidebar" aria-label="Main">
        <NavLink to="/home" className="logo">
          <Logo /> With Us
        </NavLink>
        {mother && (
          <div className="mother-card">
            <BabyIcon type={household.baby_type} size={44} />
            <div>
              <div className="name">{mother.name}</div>
              <div className="helper">recovering, week {mother.week}</div>
            </div>
          </div>
        )}
        <nav className="nav">
          {NAV.map(({ to, label, icon: Icon, badge }) => (
            <NavLink key={to} to={to}>
              <Icon size={20} aria-hidden="true" /> {label}
              {badge && needsYou > 0 && <span className="badge" aria-label={`${needsYou} waiting`}>{needsYou}</span>}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <button className="btn btn-primary" onClick={() => setAdding(true)}>
            <Plus size={18} aria-hidden="true" /> Add a task
          </button>
          <NavLink to="/about" className="btn btn-ghost" style={{ justifyContent: "flex-start" }}>
            <Info size={18} aria-hidden="true" /> About
          </NavLink>
          <div className="me-row">
            <Avatar name={me.name} colour={me.colour} />
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontWeight: 700 }}>{me.name}</div>
              <div className="helper">{me.is_mother ? "recovering" : me.role}</div>
            </div>
            <button className="icon-btn" onClick={toggleTheme} aria-label={theme === "dark" ? "Use light mode" : "Use dark mode"}>
              {theme === "dark" ? <Sun size={18} /> : <Moon size={18} />}
            </button>
            <button className="icon-btn" onClick={out} aria-label="Sign out">
              <LogOut size={18} />
            </button>
          </div>
        </div>
      </aside>

      <main className="main" id="main">
        <Outlet />
      </main>

      {adding && <AddTask onClose={() => setAdding(false)} />}
    </div>
  );
}

function AddTask({ onClose }: { onClose: () => void }) {
  const { refresh, toast } = useSession();
  const [title, setTitle] = useState("");
  const [kind, setKind] = useState<"home" | "baby">("home");
  const [workKind, setWorkKind] = useState("Cooking");
  const [days, setDays] = useState<string[]>([]);
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [hours, setHours] = useState(1);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const save = async () => {
    setBusy(true);
    setError("");
    try {
      await api.post("/api/responsibilities", {
        title, kind, work_kind: workKind, days, start: start || null, end: end || null,
        hours_per_occurrence: hours, travel: workKind === "Driving" || workKind === "Appointments",
      });
      await refresh();
      toast("Task added. The plan will ask someone.");
      onClose();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Sheet onClose={onClose} label="Add a task">
      <div className="stack">
        <h2>Add a task</h2>
        <p className="helper">Recovery steps come from the doctor's sheet. This is for baby and home work.</p>
        <label className="field">What needs doing
          <input className="input" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Evening dishes" />
        </label>
        <div className="row">
          <label className="field" style={{ flex: 1 }}>Kind
            <select className="input" value={kind} onChange={(e) => setKind(e.target.value as "home" | "baby")}>
              <option value="home">Home</option>
              <option value="baby">Baby</option>
            </select>
          </label>
          <label className="field" style={{ flex: 1 }}>Type of work
            <select className="input" value={workKind} onChange={(e) => setWorkKind(e.target.value)}>
              {WORK_KINDS.map((k) => <option key={k}>{k}</option>)}
            </select>
          </label>
        </div>
        <div className="stack-sm">
          <span style={{ fontWeight: 600 }}>Which days</span>
          <DayPicker value={days} onChange={setDays} label="Which days" />
        </div>
        <div className="row">
          <label className="field" style={{ flex: 1 }}>From (optional)
            <input className="input" type="time" value={start} onChange={(e) => setStart(e.target.value)} />
          </label>
          <label className="field" style={{ flex: 1 }}>To (optional)
            <input className="input" type="time" value={end} onChange={(e) => setEnd(e.target.value)} />
          </label>
          <label className="field" style={{ flex: 1 }}>Hours each time
            <input className="input" type="number" min={0.25} max={12} step={0.25} value={hours} onChange={(e) => setHours(Number(e.target.value))} />
          </label>
        </div>
        {error && <p className="error" role="alert">{error}</p>}
        <button className="btn btn-primary btn-lg" disabled={busy || !title.trim() || days.length === 0} onClick={save}>
          Add to the plan
        </button>
      </div>
    </Sheet>
  );
}
