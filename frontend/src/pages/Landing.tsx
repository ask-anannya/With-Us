import { useEffect, useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { HeartHandshake, Lock, Moon, Scale, Sun, UserPlus, Users } from "lucide-react";
import { api } from "../api";
import { Logo } from "../components/BabyIcon";
import { useSession, useTheme } from "../session";

const TASKS = ["Night feeds", "Cooking", "Laundry", "Doctor visits", "Groceries", "Baby bath"];
const SHARED = [
  { who: "R", colour: "--m3" }, { who: "S", colour: "--m4" }, { who: "S", colour: "--m4" },
  { who: "R", colour: "--m3" }, { who: "K", colour: "--m2" }, { who: "S", colour: "--m4" },
];

function Illustration() {
  const [shared, setShared] = useState(false);
  useEffect(() => {
    const t = window.setInterval(() => setShared((s) => !s), 2800);
    return () => window.clearInterval(t);
  }, []);
  return (
    <div className="card" aria-label="Illustration: a week moving from one person doing it all to a shared week" role="img">
      <div className="row" style={{ justifyContent: "space-between", marginBottom: 12 }}>
        <h3>{shared ? "A shared week" : "Meera doing it all"}</h3>
        <span className="pill">{shared ? "Her rest comes first" : "Week 2 after birth"}</span>
      </div>
      <div className="task-list">
        {TASKS.map((t, i) => (
          <div className="task-row" key={t}>
            <span style={{ flex: 1, fontWeight: 600 }}>{t}</span>
            <span
              className="avatar"
              style={{ background: `var(${shared ? SHARED[i].colour : "--m1"})`, width: 30, height: 30, transition: "background .6s", fontSize: 13 }}
              aria-hidden="true"
            >
              {shared ? SHARED[i].who : "M"}
            </span>
          </div>
        ))}
      </div>
      <div className="row" style={{ marginTop: 12 }}>
        <span className="helper">{shared ? "Meera: rest, 2 pm to 4 pm, every day." : "Meera: no time to rest."}</span>
      </div>
    </div>
  );
}

function DemoSwitcher() {
  const [members, setMembers] = useState<{ member_id: string; name: string; role: string }[]>([]);
  const { refresh } = useSession();
  const navigate = useNavigate();
  useEffect(() => {
    api.get<typeof members>("/api/demo/members?code=meera").then(setMembers).catch(() => setMembers([]));
  }, []);
  if (!members.length) return null;
  const go = async (member_id: string) => {
    await api.post("/api/session", { code: "meera", member_id });
    await refresh();
    navigate("/home");
  };
  return (
    <div className="card card-tint stack-sm" style={{ marginTop: 32 }}>
      <h3>Demo household</h3>
      <p className="helper">Sign in as someone in the sample household (code "meera").</p>
      <div className="row">
        {members.map((m) => (
          <button key={m.member_id} className="btn btn-sm" onClick={() => go(m.member_id)}>
            {m.name} <span className="helper">({m.role === "mother" ? "recovering" : m.role})</span>
          </button>
        ))}
      </div>
    </div>
  );
}

export default function Landing() {
  const { household, loading } = useSession();
  const [theme, toggleTheme] = useTheme();
  if (!loading && household) return <Navigate to="/home" replace />;
  return (
    <div className="landing">
      <header className="row" style={{ justifyContent: "space-between" }}>
        <span className="logo"><Logo /> With Us</span>
        <button className="icon-btn" onClick={toggleTheme} aria-label="Toggle dark mode">
          {theme === "dark" ? <Sun size={18} /> : <Moon size={18} />}
        </button>
      </header>
      <section className="landing-hero">
        <div>
          <h1>Let her rest. We've got the rest.</h1>
          <p style={{ fontSize: 20, marginTop: 16 }} className="muted">
            Everyone at home tells With Us, privately, what they can take on. It builds a fair week around her
            recovery, and your reasons stay with you.
          </p>
          <div className="action-cards">
            <Link to="/create" className="card action-card">
              <UserPlus color="var(--rose-600)" aria-hidden="true" />
              <h3>Create a household</h3>
              <p className="helper">Start a plan for a new mother and invite the family.</p>
            </Link>
            <Link to="/join" className="card action-card">
              <Users color="var(--rose-600)" aria-hidden="true" />
              <h3>Join your household</h3>
              <p className="helper">Use the household code someone shared with you.</p>
            </Link>
          </div>
        </div>
        <Illustration />
      </section>
      <section className="points">
        {[
          { icon: HeartHandshake, t: "Her rest comes first", d: "Her rest windows are never touched, and we plan her for less than she says." },
          { icon: Scale, t: "Shared by what each person can carry", d: "Fair against each person's own capacity, not an even split." },
          { icon: Lock, t: "Your reasons stay with you", d: "Your family sees your limit. Only you and your assistant see why." },
        ].map(({ icon: Icon, t, d }) => (
          <div className="card stack-sm" key={t}>
            <Icon color="var(--rose-600)" aria-hidden="true" />
            <h3>{t}</h3>
            <p className="helper">{d}</p>
          </div>
        ))}
      </section>
      <DemoSwitcher />
    </div>
  );
}
