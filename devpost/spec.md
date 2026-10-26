---
doc: spec
status: approved
---

# With Us: Technical Spec

Full detail lives in `docs/build-plan.md`; this spec is the blueprint `5-build` cites. Where the two disagree, this spec wins and the difference is recorded under **Decisions and Open Issues**.

## How This Works, In Plain Language
With Us is two programs running on one laptop.

- **The backend** (Python) holds everything: a small SQLite database file, the fair-plan engine, the privacy layer, and the calls to Gemini. It answers requests at `/api/...`.
- **The frontend** (React in the browser) draws the screens and asks the backend for data.

Three ideas carry the product rules into code:

1. **The engine is plain Python.** Given everyone's capacity, limits and the tasks, it always produces the same fair plan. No AI touches assignments or fairness numbers.
2. **Private data lives in separate tables,** and every response passes through one function, `project(viewer, data)`, that strips out anything the viewer isn't allowed to see. A test logs in as every member and checks no one else's secrets appear.
3. **Gemini only reads and writes words** (reading the discharge sheet, filling the intake form, the assistant, "say it for me"). Each call sees only what it's allowed to, returns JSON in a fixed shape, passes through a guard that blocks leaked private text, and has a non-AI fallback so the demo never breaks.

Why this shape: the solver and its tests are fastest to write in Python, SQLite needs no setup, and everything runs locally for recording.

## The Core Journey Through the System
PRD ref: `prd.md > The Core Journey`.

1. Create household → `POST /api/households` writes Household + Member, sets an httpOnly session cookie, returns code and member ID.
2. Join → `POST /api/session` with code + member ID; cookie set.
3. Intake → form saves via `PUT /api/me/profile`, `/api/me/limits`, `/api/me/reasons/{limit_id}`. "Tell my assistant instead" → `POST /api/intake/read` → Gemini fills fields → person reviews and saves. Reasons land only in `PrivateReason`.
4. Discharge sheet → `POST /api/prescription` (image or text) → Gemini extracts rows → confirm screen → `POST /api/prescription/{id}/confirm` creates recovery Responsibilities (the mother's quests).
5. Sharing → `PATCH /api/household/sharing` by mother and partner. When both on, the engine runs.
6. Engine draft (never returned) → a Proposal per unaccepted assignment → member sees `GET /api/me/proposals` → accept locks it; decline creates an Exclusion, re-solves open items, new proposals for moved items; Activity "Plan updated". Optional Announcement via "say it for me" + guard.
7. Published plan → `GET /api/plan` (accepted assignments, burden, headline, "being arranged"). Shortfalls → Decision → `POST /api/decisions/{id}/resolve`.
8. Mother → `GET /api/quests/today` → quest map → `POST /api/quests/{id}/done` → bunny count.
9. Assistant → `POST /api/assistant` → context built from only the viewer's own data + public plan → Gemini → guard → reply + suggested actions.

## Stack
- **Python 3.12** (plan said 3.11; 3.12.6 is installed and compatible), **FastAPI**, **SQLModel** on SQLite, **pytest**, **uvicorn**. Docs: https://fastapi.tiangolo.com, https://sqlmodel.tiangolo.com
- **Google Gen AI Python SDK** `google-genai`. Docs: https://ai.google.dev/gemini-api/docs. Model from env `GEMINI_MODEL`, default `gemini-3.5-flash`; key from `GEMINI_API_KEY`.
- **Pillow** to generate the sample discharge sheet. https://pillow.readthedocs.io
- **React 18, Vite, TypeScript, React Router, lucide-react**, plain CSS with tokens. https://vite.dev, https://reactrouter.com, https://lucide.dev
- Learner-selected: Python backend + React frontend + SQLite + Gemini (all from `docs/build-plan.md` section 3, Gemini by explicit change).
- **Unverified, check early:** the exact default Gemini model ID (sources disagreed on the newest; `gemini-flash-latest` is the fallback alias).

## Where It Runs and How Someone Tries It
- Local only. Needs Python 3.12, Node 20+, and `GEMINI_API_KEY` in `backend/.env` (template in `backend/.env.example`).
- Backend: `cd backend && python -m venv .venv && .venv/Scripts/pip install -r requirements.txt && .venv/Scripts/python -m app.seed && .venv/Scripts/uvicorn app.main:app --reload --port 8787`
- Frontend: `cd frontend && npm install && npm run dev`, open http://localhost:5173 (Vite proxies `/api` to port 8787; override with API_PORT).
- Demo recording: set `DEMO_MODE=1` for the member switcher; household code `meera`.
- Submission needs a short demo video and a public GitHub repository. Deployed on Vercel (learner choice) at https://with-us-omega.vercel.app: static React build plus the FastAPI app as a Python function (`api/index.py`, `vercel.json`), with a free Neon Postgres database via `DATABASE_URL`. Demo mode on; the demo household seeds itself on an empty database.
- Git operations are done by the learner, not the agent.

## Look and Feel
Carries `prd.md > Look and Feel`. Implement exactly the tokens in `docs/build-plan.md` section 9 in `frontend/src/styles/tokens.css` (cream `--bg`, white `--surface`, `--pink-50..400`, `--rose-600/700`, member colours `--m1..m4`, radii, shadow, dark overrides on `:root[data-theme="dark"]`). Source Sans 3 from Google Fonts: titles 40/700, sections 22/700, body 17/400, helper 15. Primary buttons `--rose-600` with white text; chips pill-shaped with `--pink-100` selected; private reason box `--pink-50` fill with `--pink-400` border and lock icon; load bar 48 px; quest path `--pink-200`, done stones `--rose-600`. Focus rings `--pink-400`; reduced motion honoured. Copy: calm, no em dashes, no reference names.

## Components

### Session and auth
`auth.py`: household code + member ID → session row with hashed token in an httpOnly cookie; `current_member` dependency on every route. `DEMO_MODE` exposes a member list on the login page.
PRD ref: `prd.md > Household setup and sign-in`.

### Data store
`db.py`, `models.py`: SQLModel tables per **Data Model**. Private tables are only queried by `/api/me/*` routes and the owner's own AI context.

### Fair-plan engine
`engine/weights.py`: `weight = hours_per_occurrence * occurrences_per_week * multiplier` (Nights 1.5, travel 1.2, else 1.0); `MOTHER_CEILING = 0.5`; burden = assigned / effective capacity; spread = max − min burden over members with capacity > 0.
`engine/solver.py`: feasibility matrix from hard constraints (capacity, blocked days, blocked work kinds, mother's rest windows, exclusions, fixed owners and locked accepts, recovery items excluded from her burden) → place fixed/locked → sort open by weight desc, fewest feasible, id → greedy lowest resulting burden, tie by member id → local search ≤ 500 iterations (move, then swap), accept only if `(spread, max_burden, unassigned_hours)` improves lexicographically → repair → output. No randomness.
`engine/headline.py`: three sentences from code.
PRD ref: `prd.md > Fair weekly plan`.

### Consent and decisions
`routes/plan.py`, `routes/proposals.py`, `routes/decisions.py`: sharing gate, proposals, accept/lock, decline → Exclusion → re-solve open items → new proposals, "being arranged", shortfall Decisions with three resolutions, generic Activity.
PRD ref: `prd.md > Consent and silent declines`, `prd.md > Shortfall decisions`.

### Privacy projection
`privacy/projection.py`: `project(viewer, data)` whitelists others' name, role, colour, capacity, opaque limit ids + values, accepted assignments, burden, mother's "resting" blocks; quest progress only if shared with the viewer.
PRD ref: `prd.md > Privacy proof`.

### Output guard
`privacy/guard.py`: NFKC, lowercase, strip zero-width, lookalike map, decode base64/hex-looking runs, collapse whitespace; flag any shared 3-word sequence or distinctive 5+ letter word from the protected texts; replace with a safe fallback; log a count only.
PRD ref: `prd.md > Private assistant`, `prd.md > Privacy proof`.

### Gemini client
`ai/client.py`: one `genai.Client(api_key=...)`; `generate_json(system, contents, schema, protected_texts)` calls `client.models.generate_content(model, contents, config=GenerateContentConfig(system_instruction=..., response_mime_type="application/json", response_schema=<Pydantic model>))`, reads `response.parsed`, logs `usage_metadata` token counts, runs the guard, and returns `None` on missing key, exception, safety block or empty response so the caller uses its fallback.

### AI calls
- `ai/intake.py`: speaker's own text only → `{capacity_hours, blocked_days[], blocked_work_kinds[], will_take[], private_reason}`. PRD ref: `prd.md > Private intake and limits`.
- `ai/prescription.py`: image as `types.Part.from_bytes(data, mime_type)` or pasted text → `{items:[{title, kind, schedule, original_line, unclear}]}`; extract-only system rules. PRD ref: `prd.md > Discharge sheet to quests`.
- `ai/assistant.py`: own profile, reasons, instructions, proposals + public plan → `{reply, actions:[{type: accept|decline|update_limit, ...}]}`; self-harm keywords checked in code first → help card, message not stored. PRD ref: `prd.md > Private assistant`.
- `ai/say_for_me.py`: first name, task title, week → one sentence ≤ 25 words; fallback template. PRD ref: `prd.md > Consent and silent declines`.

### Quests
`routes/quests.py`: today's quests (recovery items + rest windows with covering person), done log, bunny count, progress for caretakers only if shared.
PRD ref: `prd.md > Mother's quest map`.

### Frontend screens
`src/pages/`: Landing, Create (Baby screen + "Who is recovering?" + intake), Join, Intake, MotherHome (quest map), Dashboard, NeedsYou, Prescription, Assistant, ControlPanel. `src/components/`: LoadBar, TaskRow, Chip, DayPicker, PrivateReasonBox, QuestMap, QuestSheet, BunnyJar, SideCard, ShortfallCard, Sidebar/TabBar, BabyIcon. `src/api.ts` typed fetch wrapper; `src/session.ts` current member.
PRD ref: `prd.md > Screens and Layout` and each feature heading.

### Seed and demo data
`app/seed.py`: household `meera`, members meera/karan/ramesh/sunita with capacities, limits, rest windows, private reasons and instructions per `docs/build-plan.md` section 11; responsibilities tuned so the baseline fits; `cold` toggle adds about 3 unassigned hours; generates `seed/discharge-sheet.png` labelled "Sample document for a demo, not a real prescription."
PRD ref: `prd.md > What We're Building`.

### Leak evaluation
`scripts/leak_eval.py`: ≥ 20 attacks on Ramesh's assistant about Karan's and Sunita's reasons + 5 harmless questions; pass only if no secret appears after normalisation and harmless ones are answered; prints the real score.
PRD ref: `prd.md > Privacy proof`.

## Data Model
All in `backend/with_us.db` (SQLite), persisted across restarts; `python -m app.seed` resets to the demo household. Tables (fields per `docs/build-plan.md` section 4): Household, Member, Limit, **PrivateReason** (private), **AssistantInstructions** (private), RestWindow, Responsibility, Prescription, **QuestLog** (private to mother unless shared), MotherSharing, **Proposal** (private), **Exclusion** (private), Plan, Decision, Activity, **ChatMessage** (private), Announcement, plus Session (token hash → member). Frontend keeps only the theme choice in localStorage; everything else is fetched.

## File Structure
```
with-us/
├── devpost/                    # learning workspace: profile (ignored), scope, prd, spec, checklist
├── docs/build-plan.md          # the learner's detailed plan
├── README.md
├── Makefile                    # make dev runs both servers
├── backend/
│   ├── requirements.txt  .env.example
│   ├── app/
│   │   ├── main.py             # FastAPI app, routers, CORS off (proxied)
│   │   ├── settings.py         # env: GEMINI_API_KEY, GEMINI_MODEL, DEMO_MODE
│   │   ├── db.py  models.py  auth.py
│   │   ├── privacy/projection.py  privacy/guard.py
│   │   ├── engine/weights.py  engine/solver.py  engine/headline.py
│   │   ├── ai/client.py  intake.py  prescription.py  assistant.py  say_for_me.py
│   │   ├── routes/household.py  me.py  plan.py  proposals.py  prescription.py
│   │   │         quests.py  assistant.py  decisions.py
│   │   └── seed.py
│   ├── seed/discharge-sheet.png   # generated
│   ├── tests/test_solver.py  test_projection.py  test_guard.py  test_flows.py
│   └── scripts/leak_eval.py
└── frontend/
    ├── index.html  vite.config.ts  package.json
    └── src/
        ├── main.tsx  App.tsx  api.ts  session.ts
        ├── styles/tokens.css  base.css
        ├── pages/        # one file per screen
        └── components/   # shared UI pieces
```

## External Services and Dependencies
- **Gemini API** via `google-genai`. Call: `client.models.generate_content(model=GEMINI_MODEL, contents=[...parts], config=GenerateContentConfig(system_instruction, response_mime_type="application/json", response_schema))`. Response: `.parsed` (Pydantic object), `.text`, `.usage_metadata`, `.candidates[0].finish_reason`. Auth: API key. Docs: https://ai.google.dev/gemini-api/docs/structured-output, https://ai.google.dev/gemini-api/docs/image-understanding. Free tier has rate limits; leak_eval makes ~25 calls, so it paces requests and reports any rate-limit errors rather than counting them as passes.
- **Google Fonts** for Source Sans 3. Falls back to system sans-serif offline.

## Important Failure Modes
- **Gemini unavailable, rate-limited or safety-blocked** → each feature uses its fallback (plain intake form, manual instruction form, canned assistant help with plain buttons, "{name} can't take {task} this week.").
- **Model leaks a private phrase** → guard replaces the output with "That's theirs to share. I can tell you they're unavailable on Thursdays." style text; count logged.
- **Plan doesn't fit** → unassigned items become a shortfall Decision; nobody is overloaded.

## What Was Simplified and Why
- **Household code + member ID** instead of real accounts: enough to show per-viewer privacy. Real auth would add passwords and recovery.
- **SQLite file, local only** instead of hosted database and deployment: reviewers watch the video.
- **Greedy + bounded local search** instead of an optimisation library: deterministic, testable, fast enough for a household.
- **Seeded demo household and sample sheet**, clearly labelled as sample data. The engine, privacy and AI calls are real.

## Decisions and Open Issues
- Learner choices: the full stack and architecture in `docs/build-plan.md`; Gemini instead of Claude for all AI calls; the agent performs no git operations.
- Implementation details derived by the agent: Python 3.12 instead of 3.11; a Session table for cookie tokens; `generate_json` returning `None` as the single fallback signal; leak_eval pacing for rate limits.
- **Useful unknown (learner's learning goal: how to work with an agent):** how the agent keeps a large plan on track. Investigation during the build: the checklist slices, mechanical verification per slice, and every plan deviation recorded under `checklist.md > Revisions` are the evidence to look at.
- Open: verify the default Gemini model ID at the first AI slice; verify Tele-MANAS 14416 before the video.
