export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const init: RequestInit = { method, credentials: "include", headers: {} };
  if (body instanceof FormData) {
    init.body = body;
  } else if (body !== undefined) {
    (init.headers as Record<string, string>)["Content-Type"] = "application/json";
    init.body = JSON.stringify(body);
  }
  let res: Response;
  try {
    res = await fetch(path, init);
  } catch {
    throw new ApiError(0, "We can't reach With Us right now. Check that the server is running.");
  }
  if (!res.ok) {
    let msg = "Something went wrong. Please try again.";
    try {
      const data = await res.json();
      if (typeof data.detail === "string") msg = data.detail;
    } catch {
      /* keep default */
    }
    throw new ApiError(res.status, msg);
  }
  return res.json() as Promise<T>;
}

export const api = {
  get: <T>(path: string) => request<T>("GET", path),
  post: <T>(path: string, body?: unknown) => request<T>("POST", path, body ?? {}),
  put: <T>(path: string, body?: unknown) => request<T>("PUT", path, body ?? {}),
  patch: <T>(path: string, body?: unknown) => request<T>("PATCH", path, body ?? {}),
  del: <T>(path: string) => request<T>("DELETE", path),
};

export type LimitPublic = { opaque_id: string; kind: "day" | "work_kind"; value: string };
export type MemberPublic = {
  id: number; name: string; role: string; colour: string; capacity_hours: number; is_mother: boolean;
  limits: LimitPublic[]; resting?: { days: string[]; start: string; end: string; label: string }[];
};
export type Household = {
  code: string; baby_type: "girl" | "boy"; baby_name: string; week_start: string; cold: boolean; demo: boolean;
  mother: { id: number; name: string; week: number } | null; notes: string; members: MemberPublic[];
  sharing: { mother: boolean; partner: boolean; ready: boolean }; has_partner: boolean;
  me: { id: number; member_id: string; name: string; role: string; colour: string; is_mother: boolean };
};
export type Resp = {
  id: number; title: string; kind: "recovery" | "baby" | "home"; work_kind: string; days: string[];
  start: string | null; end: string | null; hours_per_occurrence: number; travel: boolean; source: string;
  source_line: string; schedule: string; icon: string; active: boolean; outside_help: boolean;
};
export type PlanMember = MemberPublic & { burden_pct: number; hours: number; tasks: number };
export type Plan =
  | { ready: false; sharing: { mother: boolean; partner: boolean } }
  | {
      ready: true; week: string; version: number; published_at: string; headline: string; spread: number;
      members: PlanMember[]; assignments: { responsibility: Resp; member_id: number; member_name: string }[];
      arranging: Resp[]; unassigned: { responsibility: Resp; hours: number }[]; outside_help: Resp[];
    };
export type Proposal = { id: number; responsibility: Resp; status: string };
export type Decision = {
  id: number; title: string; hours: number; days: string[]; text: string;
  options: ("drop" | "outside_help" | "raise_capacity")[]; my_capacity: number;
};
export type Me = {
  id: number; member_id: string; name: string; role: string; colour: string; capacity_hours: number;
  is_mother: boolean; household_code: string; general_reason: string; instructions: string;
  limits: { id: number; opaque_id: string; kind: "day" | "work_kind"; value: string; reason: string }[];
  rest_windows?: { days: string[]; start: string; end: string }[]; planned_hours?: number;
  sharing?: { share_progress: boolean; share_with: number[] };
};
export type Quest = {
  key: string; kind: "recovery" | "rest"; title: string; icon: string; time: string; original_line: string;
  schedule: string; covering: string; done: boolean;
};
export type QuestProgress = {
  shared: boolean; name?: string; quests: Quest[]; done?: number; total?: number; bunnies?: number; dots: boolean[];
};
export type QuestDay = {
  name: string; baby_type: "girl" | "boy"; quests: Quest[]; bunnies: number;
  covered: { title: string; owner: string }[]; arranging: string[]; outside_help: string[]; has_sheet: boolean;
};
export type SheetItem = {
  title: string; original_line: string; schedule: string; days: string[]; time: string; icon: string; unclear?: boolean;
};
export type ChatAction = {
  type: "accept" | "decline" | "update_limit"; proposal_id?: number; kind?: "day" | "work_kind"; value?: string; label: string;
};
export type ChatReply = { reply: string; actions: ChatAction[]; crisis?: boolean; used_ai?: boolean };

export const WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
export const DAY_NAMES: Record<string, string> = {
  Mon: "Monday", Tue: "Tuesday", Wed: "Wednesday", Thu: "Thursday", Fri: "Friday", Sat: "Saturday", Sun: "Sunday",
};
export const WORK_KINDS = ["Nights", "Driving", "Cooking", "Appointments", "Baby care", "Cleaning", "Errands"];

export function timeLabel(hhmm: string | null | undefined): string {
  if (!hhmm) return "";
  const [h, m] = hhmm.split(":").map(Number);
  const suffix = h < 12 ? "am" : "pm";
  const h12 = h % 12 || 12;
  return m === 0 ? `${h12} ${suffix}` : `${h12}:${String(m).padStart(2, "0")} ${suffix}`;
}

export function daysLabel(days: string[]): string {
  if (days.length === 7) return "Every day";
  if (days.join() === "Mon,Tue,Wed,Thu,Fri") return "Monday to Friday";
  if (days.join() === "Sat,Sun") return "Weekends";
  if (days.length === 1) return DAY_NAMES[days[0]] ?? days[0];
  return days.join(", ");
}

export function whenLabel(r: Pick<Resp, "days" | "start" | "end">): string {
  const d = daysLabel(r.days);
  if (r.start && r.end) return `${d}, ${timeLabel(r.start)} to ${timeLabel(r.end)}`;
  if (r.start) return `${d}, ${timeLabel(r.start)}`;
  return d;
}
