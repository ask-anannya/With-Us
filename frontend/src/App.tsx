import { Navigate, Route, Routes } from "react-router-dom";
import { Shell } from "./components/Shell";
import About from "./pages/About";
import Assistant from "./pages/Assistant";
import ControlPanel from "./pages/ControlPanel";
import Create from "./pages/Create";
import Dashboard, { MotherPlan } from "./pages/Dashboard";
import Intake from "./pages/Intake";
import Join from "./pages/Join";
import Landing from "./pages/Landing";
import MotherHome from "./pages/MotherHome";
import NeedsYou from "./pages/NeedsYou";
import Prescription from "./pages/Prescription";
import { useSession } from "./session";

function Home() {
  const { household } = useSession();
  return household?.me.is_mother ? <MotherHome /> : <Dashboard />;
}

function PlanPage() {
  const { household } = useSession();
  return household?.me.is_mother ? <MotherPlan /> : <Dashboard initialTab="everyone" />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/create" element={<Create />} />
      <Route path="/join" element={<Join />} />
      <Route path="/intake" element={<Intake />} />
      <Route element={<Shell />}>
        <Route path="/home" element={<Home />} />
        <Route path="/needs-you" element={<NeedsYou />} />
        <Route path="/plan" element={<PlanPage />} />
        <Route path="/prescription" element={<Prescription />} />
        <Route path="/assistant" element={<Assistant />} />
        <Route path="/control" element={<ControlPanel />} />
        <Route path="/about" element={<About />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
