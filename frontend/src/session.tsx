import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { api, ApiError, type Household } from "./api";

type SessionValue = {
  household: Household | null;
  loading: boolean;
  needsYou: number;
  refresh: () => Promise<void>;
  signOut: () => Promise<void>;
  toast: (msg: string) => void;
};

const SessionContext = createContext<SessionValue | null>(null);

export function SessionProvider({ children }: { children: ReactNode }) {
  const [household, setHousehold] = useState<Household | null>(null);
  const [loading, setLoading] = useState(true);
  const [needsYou, setNeedsYou] = useState(0);
  const [message, setMessage] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const h = await api.get<Household>("/api/household");
      setHousehold(h);
      const [props, decisions] = await Promise.all([
        api.get<unknown[]>("/api/me/proposals"),
        api.get<unknown[]>("/api/decisions"),
      ]);
      setNeedsYou(props.length + decisions.length);
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) setHousehold(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const signOut = useCallback(async () => {
    await api.del("/api/session").catch(() => undefined);
    setHousehold(null);
  }, []);

  const toast = useCallback((msg: string) => {
    setMessage(msg);
    window.setTimeout(() => setMessage(null), 3200);
  }, []);

  return (
    <SessionContext.Provider value={{ household, loading, needsYou, refresh, signOut, toast }}>
      {children}
      {message && (
        <div className="toast" role="status">
          {message}
        </div>
      )}
    </SessionContext.Provider>
  );
}

export function useSession(): SessionValue {
  const v = useContext(SessionContext);
  if (!v) throw new Error("useSession outside provider");
  return v;
}

export function useTheme(): [string, () => void] {
  const [theme, setTheme] = useState(() => document.documentElement.dataset.theme || "light");
  const toggle = () => {
    const next = theme === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    try {
      localStorage.setItem("withus-theme", next);
    } catch {
      /* storage unavailable */
    }
    setTheme(next);
  };
  return [theme, toggle];
}
