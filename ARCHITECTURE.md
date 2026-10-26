# With Us: Architecture

This document explains how With Us is put together: the main parts, how data moves between them, how the fair plan is computed, how privacy is enforced, and where Gemini fits in. For setup and features, see [README.md](README.md).

---

## Contents

1. [The big picture](#1-the-big-picture)
2. [Design principles](#2-design-principles)
3. [Backend structure](#3-backend-structure)
4. [Data model](#4-data-model)
5. [The fair-plan engine](#5-the-fair-plan-engine)
6. [The consent flow](#6-the-consent-flow)
7. [Privacy: three layers](#7-privacy-three-layers)
8. [AI: where Gemini is used, and where it is not](#8-ai-where-gemini-is-used-and-where-it-is-not)
9. [The mother's quest map](#9-the-mothers-quest-map)
10. [Authentication and sessions](#10-authentication-and-sessions)
11. [Frontend structure](#11-frontend-structure)
12. [Deployment](#12-deployment)
13. [Testing strategy](#13-testing-strategy)
14. [Known limits](#14-known-limits)

---

## 1. The big picture

```
┌──────────────────────────────┐        ┌──────────────────────────────────────────────┐
│  Browser                     │        │  Backend (FastAPI)                           │
│  React + Vite SPA            │  /api  │                                              │
│                              │ ─────► │  routes/      HTTP endpoints                 │
│  pages/  components/         │ cookie │     │                                        │
│  session.tsx  api.ts         │ ◄───── │     ├──► planning.py ──► engine/  (no AI)    │
└──────────────────────────────┘  JSON  │     │                                        │
                                        │     ├──► privacy/projection.py (whitelist)   │
                                        │     │                                        │
                                        │     └──► ai/ ──► Gemini ──► privacy/guard.py │
                                        │                                              │
                                        │  models.py ──► SQLite (local) / Postgres     │
                                        └──────────────────────────────────────────────┘
```

- The **frontend** is a single-page React app. It talks to the backend only through `/api`, with an httpOnly session cookie.
- The **backend** is a FastAPI app. Routes are thin; the logic lives in `planning.py`, `engine/`, `privacy/` and `ai/`.
- The **engine** computes the fair plan. It is plain Python with no AI and no database access.
- The **privacy** layer decides what any viewer may see about anyone else, and checks every AI output before it leaves the server.
- The **AI** layer holds four narrow Gemini features. Each one returns structured JSON and has a non-AI fallback.

## 2. Design principles

These come straight from the product's three rules and shaped most technical choices.

| Principle | What it means in the code |
| --- | --- |
| **The mother gets her space** | Her rest windows are a hard feasibility constraint in the solver. Her effective capacity is `capacity × 0.5`. Her own recovery quests never count toward her load. |
| **The maths is never left to AI** | `engine/` has no imports from `ai/`. Assignments, burden, spread and the dashboard headline are all computed in Python. Gemini never sees or edits the plan's numbers. |
| **Your reasons never leave you** | Private data has its own tables, household responses go through a whitelist, the assistants are only given their owner's private data, and an output guard checks every reply. |
| **AI is optional** | Every Gemini call goes through one function that returns `None` on any failure. Each caller has a fallback, so the app works with no key at all. |
| **Deterministic and testable** | Same input, same plan. Sorting is by explicit keys and ties break on ids, so property tests can assert exact behaviour. |

## 3. Backend structure

```
backend/app/
├── main.py           App, router registration, /api/health
├── settings.py       Env vars, database URL, upload folder
├── db.py             SQLAlchemy engine; init_db(); get_session()
├── models.py         SQLModel tables
├── auth.py           Session cookie, current_member, permission helpers
├── planning.py       DB ⇄ engine bridge, replan(), publish()
├── seed.py           Demo household, sample discharge sheet, ensure_demo()
├── engine/
│   ├── weights.py    Multipliers, capacity, burden
│   ├── solver.py     The fair-plan solver
│   └── headline.py   Dashboard headline text
├── privacy/
│   ├── projection.py What others may see (whitelist)
│   └── guard.py      Output guard for AI text and announcements
├── ai/
│   ├── client.py     The only module that calls Gemini
│   ├── intake.py     Free text → intake form fields
│   ├── prescription.py  Discharge sheet → instruction rows
│   ├── assistant.py  Personal assistant (context, rules, crisis check)
│   └── say_for_me.py One kind sentence for a decline
└── routes/
    ├── household.py  Create, join, sign in, demo, settings, responsibilities, activity
    ├── me.py         The signed-in member's private profile, limits, reasons, previews
    ├── plan.py       Plan view, proposals, accept/decline, shortfall decisions
    ├── prescription.py  Upload, read, confirm the discharge sheet
    ├── quests.py     Today's quests, marking done, shared progress
    └── assistant.py  Chat, history, guard on replies
```

A request typically goes: **route** → `current_member` (auth) → load the household → call `planning`, `ai` or the projection → return a dict built only from whitelisted fields.

## 4. Data model

All tables are in `backend/app/models.py`. The split between **shared** and **private** tables is the first privacy layer.

### Shared (household-facing, always projected)

| Table | Purpose |
| --- | --- |
| `Household` | Code, who the mother is, baby details, week start, fairness tolerance, both sharing switches, the `cold` demo switch |
| `Member` | Name, role (mother, partner, parent, relative, helper), capacity in hours a week, colour |
| `Limit` | A public limit: `kind` is `day` or `work_kind`, plus a random `opaque_id`. No reason is stored here. |
| `RestWindow` | The mother's protected rest times (days, start, end) |
| `Responsibility` | A unit of work: title, kind (recovery, baby, home), work kind, days, times, hours per occurrence, travel, a fixed owner if any, where it came from (doctor or family), the doctor's original line, and flags for active, outside help and cold-only |
| `Plan` | A published, versioned snapshot: accepted assignments, burden per member, unassigned items, "being arranged" items, spread and headline |
| `Decision` | A shortfall card: which responsibility, hours, days. No names. |
| `Activity` | The household log. Mostly "Plan updated". |
| `Announcement` | A "say it for me" sentence a member chose to post |
| `Prescription` | An uploaded or pasted discharge sheet and the extracted rows, plus who confirmed it |

### Private (only the owner's routes and the owner's own AI context read these)

| Table | Purpose |
| --- | --- |
| `PrivateReason` | Why a member has a limit, in their own words |
| `AssistantInstructions` | How a member wants their assistant to behave (for example, Meera's "say it for me, kindly") |
| `Proposal` | A request for one member to take one responsibility this week: pending, accepted, declined or withdrawn |
| `Exclusion` | A decline: this member won't take this responsibility this week |
| `ChatMessage` | A member's own assistant history |
| `QuestLog` | Which of the mother's quests she marked done, and when |
| `MotherSharing` | Whether the mother shares her quest progress, and with whom |
| `SessionToken` | Hashed session tokens |

JSON columns (`days`, `assignments_json` and so on) use SQLAlchemy's `JSON` type, so the same models work on SQLite and Postgres.

## 5. The fair-plan engine

`backend/app/engine/` turns members and responsibilities into assignments. It knows nothing about the database, HTTP or AI.

### 5.1 Weights and burden (`weights.py`)

- **Weekly hours** of a responsibility = hours per occurrence × number of days.
- **Weight** = weekly hours × a multiplier: **1.5** for night work, **1.2** for driving or anything with travel, **1.0** otherwise. An hour awake at 3 am costs more than an hour of laundry.
- **Effective capacity** = stated capacity, except the mother, who is planned at **0.5 ×** what she states.
- **Burden** = assigned weight ÷ effective capacity. 0.6 means "60% full against your own capacity".

Fairness means **everyone's burden is about the same**, not everyone doing the same hours. Someone who offers 4 hours and someone who offers 20 can both be 60% full.

### 5.2 The solver (`solver.py`)

`solve(members, resps, excluded, locked)` runs these steps:

1. **Feasibility matrix.** For each responsibility, list who can take it. A member is excluded if they have no capacity, declined it this week, have a blocked day it falls on, have blocked its work kind, or (for the mother) it overlaps one of her rest windows. Night work with no times is treated as 22:00 to 06:00, and windows that cross midnight are split.
2. **Pinned items first.** Accepted proposals (`locked`) are placed and never move. Responsibilities with a fixed owner go to that owner if feasible and there is room; otherwise they are unassigned.
3. **Order the rest** by weight (largest first), then fewest feasible members, then id.
4. **Greedy pass.** Give each item to the feasible member with room whose resulting burden would be lowest (ties go to the lower member id).
5. **Local search**, up to 500 iterations. Try moving one item to another member, then try swapping two items between members. Accept a change only if it improves the objective.
6. **Repair.** For each item still unassigned, place it with anyone who has room, or move one other item away to make room. Then run local search again.

Recovery items (the mother's own quests) are skipped: they are hers, and they never count toward her burden.

### 5.3 The objective

The solver compares plans with a **lexicographic** tuple, smallest first:

```
(spread, max_burden, unassigned_hours)
```

- **spread** = (highest burden − lowest burden) × 100, in percentage points.
- The mother is **left out of the spread**. Her 0.5 ceiling already protects her, and her near-zero load would otherwise dominate the spread and push work back toward her.
- **Hard constraint:** nobody's load may exceed their effective capacity (with a tiny epsilon for floating point). Nothing in the search can break this.

### 5.4 The headline (`headline.py`)

The dashboard line is chosen by code:

- If work is unassigned: "3 hours a week still need someone."
- Else if the spread is above the household's tolerance (15 points by default): "{Name} is carrying the most this week."
- Else: "The week is shared fairly. {Mother}'s rest is protected."

## 6. The consent flow

`backend/app/planning.py` connects the engine to people. The key idea: **the engine's draft is never shown to the household.** It only ever becomes private proposals.

```
                 ┌─────────────────────────┐
  sharing on ──► │ replan()                │
  accept     ──► │  1. load members, limits│
  decline    ──► │     rest, exclusions    │
  decision   ──► │  2. locked = accepted   │
  cold toggle──► │  3. solve()             │
                 │  4. sync proposals      │──► private Proposal rows (Needs you)
                 │  5. sync shortfalls     │──► Decision cards (no names)
                 │  6. publish()           │──► Plan (accepted work only)
                 │  7. log "Plan updated"  │──► Activity
                 └─────────────────────────┘
```

1. **Sharing gate.** Nothing is planned until both the mother and the partner turn on sharing. Until then `/api/plan` returns `ready: false`.
2. **Proposals.** For each open assignment from the solver, there is exactly one pending `Proposal` for that member. If the solver now picks someone else, the old proposal is marked `withdrawn` and a new one is created.
3. **Accept.** The proposal becomes `accepted`, so the next solve locks it in place. The published plan now shows it.
4. **Decline.** The proposal becomes `declined` and an `Exclusion` is stored for that member, responsibility and week. `replan()` runs and the work goes to someone else, or becomes a shortfall. The household sees only "Plan updated".
5. **Say it for me.** If the person ticked "Tell the family kindly for me", Gemini writes one sentence from only their first name and the task title. It passes the output guard against their own private reasons and is posted as an `Announcement`.
6. **Shortfalls.** Each item the solver could not place gets one open `Decision`. Options are **drop** (mother or partner only), **outside help** (removed from the plan and listed separately), or **raise my capacity**. When an item becomes covered, its decision closes itself.
7. **Publish.** `publish()` writes a new `Plan` version from **accepted** proposals only, measures burden on that, lists pending items as "Being arranged", and writes the headline.

## 7. Privacy: three layers

Each layer assumes the one before it might fail.

### Layer 1: separate tables

Reasons, instructions, proposals, exclusions, chats and quest logs live in their own tables (section 4). Household-facing code never joins on them. Routes that read them (`routes/me.py`, the proposal routes, assistant history) filter by the signed-in member's id.

### Layer 2: per-viewer projection (`privacy/projection.py`)

Every household-facing payload about a member or responsibility is built by this module from a fixed whitelist:

- **About a member:** id, name, role, colour, capacity, whether they are the mother, and their limits as `{opaque_id, kind, value}`. For the mother, her rest windows labelled "Resting".
- **About a responsibility:** a fixed list of fields (`RESP_FIELDS`). Internal fields such as the fixed owner and cold-only flag are left out.
- **The mother's quest progress** is shown only to her, and in detail to the people she chose to share with (`can_see_progress`). Everyone else gets nothing.

The module never imports the private tables, which makes it easy to review.

**Control panel previews** use the same code: "What your household sees" is literally the projection of you, and "What your assistant is told" is literally the context string sent to Gemini.

### Layer 3: the output guard (`privacy/guard.py`)

The assistants never receive other people's private text in the first place. The guard is a backup that runs on **every assistant reply, every suggested action label and every announcement**. It checks the output against the private text it must never contain (for the assistant: every other member's reasons and instructions).

Before matching, it normalises the output:

1. Unicode NFKC normalisation.
2. Remove zero-width and soft-hyphen characters.
3. Decode any base64 or hex runs and append the decoded text.
4. Lowercase and map lookalike letters (Cyrillic and Greek lookalikes, and leetspeak such as `0→o`, `3→e`, `@→a`).
5. Collapse spaced-out letters (`k a r a n` → `karan`).

Then it flags a leak if:

- any **three-word run** from a secret appears in the output, unless all three words are public or filler (names, days, work kinds, task titles, common words, or 3 letters or fewer); or
- any **distinctive word** from a secret (5+ letters, not a common or public word) appears.

On a hit, it replaces the text with "That's theirs to share. I can only tell you what's in the plan." and logs a count, never the text.

The public vocabulary exception exists because a correct answer like "Karan is unavailable on Thursday and Friday" shares words with his private reason. That case was found by the real-model leak test and is now a regression test.

## 8. AI: where Gemini is used, and where it is not

### 8.1 One client (`ai/client.py`)

All Gemini traffic goes through `generate_json(system, contents, schema, temperature)`:

- Uses the `google-genai` SDK with `system_instruction`, `response_mime_type="application/json"` and a **Pydantic `response_schema`**, so replies are typed objects, not free text.
- Counts input and output tokens and calls (shown at `/api/health`).
- Returns **`None`** when there is no key, or on any error: network, quota, safety block or bad JSON. It logs the error type and code, never the content.

Gemini rejects empty strings as enum values, so optional enum fields use an explicit value such as `"none"`.

### 8.2 The four features

| Feature | Module | What Gemini sees | Output | Fallback |
| --- | --- | --- | --- | --- |
| Intake reader | `ai/intake.py` | Only the speaker's own free text | Capacity, blocked days, blocked work kinds, offers, and any reason moved into `private_reason` | The plain form |
| Discharge sheet reader | `ai/prescription.py` | Only the uploaded image or pasted text, never member data | One row per instruction: short title, exact original line, schedule, weekdays, time, icon, `unclear` flag | Each pasted line becomes a row; lines without "daily" are marked unclear |
| Personal assistant | `ai/assistant.py` | The member's own profile, limits, reasons and instructions, their pending proposals, the published plan, the doctor's lines, the mother's rest times, and others' public limits only | A reply under 90 words plus suggested actions (accept, decline, add a limit) | A short message and accept/decline buttons for each pending request |
| Say it for me | `ai/say_for_me.py` | Only a first name and a task title | One kind sentence, at most 25 words, with no reason | A template: "{Name} can't take {task} this week." |

Every output is cleaned after it comes back:

- Days and work kinds are filtered to the known lists.
- Capacity is clamped to 0 to 40.
- Suggested actions are kept only if they refer to the member's own pending proposals.
- Em dashes are removed.
- Assistant replies, action labels and announcements go through the guard.

### 8.3 What Gemini never does

- Assign work, compute burden or fairness, or write the headline.
- See another member's reasons or instructions.
- Add, change or interpret medical advice. The prescription prompt says to extract only what is written, and a person must confirm every row before it becomes a quest.
- Handle a crisis message. `is_crisis()` matches self-harm phrases first; the reply is a fixed help line (Tele-MANAS 14416) with no AI call, and the message is not stored.

## 9. The mother's quest map

`routes/quests.py` builds today's quests for the mother from two sources:

- **Recovery responsibilities** confirmed from the discharge sheet. Daily items get a per-day key (`r{id}-{date}`). Weekly items get a per-week key, and a missed one rolls forward to later days that week. Undated items (such as "Wound check on day 10") stay until done.
- **Rest windows**, shown as "Lie down, 2 pm to 4 pm" or "Sleep, 10 pm to 6 am".

For each quest with a time, it checks whether an accepted baby task overlaps it and, if so, adds "Sunita has the baby." so she can actually rest.

Marking a quest done writes a `QuestLog` row, which the frontend shows as a bunny in her jar. There are no percentages, streaks or red states on her screen. `GET /quests/progress` returns her quests in detail to the people she shares with, and nothing to anyone else.

## 10. Authentication and sessions

- People join a household with its **household code** plus their **member id** (a short slug). This is a deliberately light model for a proof of concept, not production authentication.
- On sign-in, the server creates a random token, stores only its **SHA-256 hash** in `SessionToken`, and sets it as an **httpOnly, SameSite=Lax** cookie (also **Secure** on Vercel), valid for 30 days.
- `current_member` resolves the cookie on every protected route. `require_mother_or_partner` guards actions such as dropping work.
- In demo mode, `/api/demo/login?member=…` signs in by link and `/api/demo/members` lists the sample household.

## 11. Frontend structure

```
frontend/src/
├── main.tsx          Router and session provider
├── App.tsx           Routes
├── api.ts            fetch wrapper and shared types
├── session.tsx       Loads /api/household; exposes the signed-in member
├── styles/
│   ├── tokens.css    Colour, spacing and type tokens (light and dark)
│   └── base.css      Layout grids and component styles
├── components/
│   ├── Shell.tsx     Sidebar navigation around signed-in pages
│   ├── QuestMap.tsx  Stepping stones, quest sheet, bunny jar, help card
│   ├── SharedQuests.tsx  Compact shared-progress card
│   ├── Cards.tsx     Side cards, proposal cards, shortfall cards
│   ├── LoadBar.tsx   Burden bar per person
│   ├── TaskRow.tsx   One task with its status
│   ├── Chip.tsx, BabyIcon.tsx, PrivateReasonBox.tsx
└── pages/
    ├── Landing.tsx   Intro and demo member switcher
    ├── Create.tsx, Join.tsx, Intake.tsx
    ├── MotherHome.tsx   Quest map (mother's home)
    ├── Dashboard.tsx    Everyone else's home: their week, the whole week, load bars
    ├── NeedsYou.tsx     Pending requests with accept and "Not this week"
    ├── Prescription.tsx Upload, paste or use the sample; confirm rows
    ├── Assistant.tsx    Private chat with suggested actions
    ├── ControlPanel.tsx Limits, reasons, instructions, previews, household, activity
    └── About.tsx
```

- `/home` shows the quest map to the mother and the dashboard to everyone else, using `session.tsx`.
- The layout is built for desktop width and uses the full screen with CSS grids. There is no phone layout.
- During development, Vite proxies `/api` to the backend (`API_PORT`, default 8787), so cookies stay same-origin. In production, Vercel serves both from one domain.

## 12. Deployment

```
            https://with-us-omega.vercel.app
                         │
            ┌────────────┴─────────────┐
            │ Vercel rewrites          │
            │  /api/*  → api/index.py  │
            │  /*      → index.html    │
            └────┬────────────────┬────┘
                 │                │
   Static files (frontend/dist)   Python function (FastAPI)
                                  │
                                  └──► Neon Postgres (DATABASE_URL)
                                  └──► Gemini API (GEMINI_API_KEY)
```

- `api/index.py` adds `backend/` to `sys.path`, imports the FastAPI app, and on a cold start runs `ensure_demo()` (with `DEMO_MODE=1`). That creates the tables and seeds the demo household only if it is missing.
- `settings.py` picks the database: `WITH_US_DB`, then `DATABASE_URL`, then `POSTGRES_URL`, else local SQLite. It rewrites `postgres://` to `postgresql://` for SQLAlchemy.
- On Postgres, `db.py` uses `NullPool` with `pool_pre_ping`, so a serverless function never holds connections between invocations.
- Uploads go to `/tmp/with-us-uploads` on Vercel, because the rest of the filesystem is read-only. They are short-lived, which is fine because the extracted rows are what matters and they are stored in the database.
- The function bundles `backend/app/**` and `backend/seed/**` and may run for up to 60 seconds (enough for an image read by Gemini).

## 13. Testing strategy

| Level | Where | Approach |
| --- | --- | --- |
| Engine properties | `tests/test_solver.py` | 200 randomly generated households, checking capacity, blocked days and kinds, rest windows, declines, determinism, scale invariance, locked placements, plus the seed and cold weeks |
| Privacy | `tests/test_projection.py` | Signs in as each member and scans every GET response for any other member's private text |
| Guard | `tests/test_guard.py` | Encodings, lookalikes, spacing tricks, and public facts that must pass |
| Flows | `tests/test_flows.py` | End-to-end API flows through FastAPI's TestClient, with AI forced off |
| Real model | `scripts/leak_eval.py` | 24 attacks and 5 harmless questions against the real Gemini model on a throwaway database; latest score 24/24 safe, 5/5 useful |

The unit and flow tests never call Gemini, so they are fast, free and repeatable. The leak test is the only one that spends tokens.

## 14. Known limits

This is a hackathon proof of concept. Things we would change before real use:

- **Authentication** is a household code plus member id. Real use needs proper accounts and invitations.
- **One week at a time.** The plan covers the current week only; there is no history or multi-week planning.
- **Shared demo.** With demo mode on, every visitor to the live site uses the same household.
- **Uploads are temporary** on Vercel (`/tmp`).
- **The guard is a backup, not a proof.** The main protection is that the assistant never receives other people's private text. The guard can still miss a heavily paraphrased leak, or block a harmless sentence.
- **Desktop only.** There is no phone layout yet.
- **English UI.** The assistant can reply in other languages, but the interface is English only.
