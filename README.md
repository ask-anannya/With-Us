# With Us

**A recovery plan for the new mother that the whole household carries.**

With Us is a web app that plans one week of recovery, baby duties and house chores around a new mother. The work is shared fairly and privately across her household: her partner, parents, in-laws, relatives and helpers. It was built for Devpost's **Build With AI: Basics** hackathon as a working proof of concept.

**Live demo:** https://with-us-omega.vercel.app

Demo mode is on. Use the **Demo household** buttons on the landing page to sign in as Meera (the mother), Karan (her partner), Ramesh (her father) or Sunita (her mother-in-law). Everyone who opens the link shares the same demo household.

![Landing page](screenshots/01-landing.png)

---

## Contents

- [Why we built it](#why-we-built-it)
- [What it does](#what-it-does)
- [Three rules it never breaks](#three-rules-it-never-breaks)
- [A walk through the demo](#a-walk-through-the-demo)
- [Tech stack](#tech-stack)
- [How to run it locally](#how-to-run-it-locally)
- [Configuration](#configuration)
- [Deployment (Vercel)](#deployment-vercel)
- [Tests](#tests)
- [Leak test](#leak-test)
- [Project layout](#project-layout)
- [API overview](#api-overview)
- [Not a medical device](#not-a-medical-device)
- [What we learned](#what-we-learned)
- [Planning documents](#planning-documents)

For how the pieces fit together (the fair-plan engine, the privacy layers and the AI calls), see **[ARCHITECTURE.md](ARCHITECTURE.md)**.

---

## Why we built it

After a baby arrives, the mother is often left carrying almost everything alone while her body recovers. That load can feed into postpartum depression.

Even when there are people around, two other problems show up:

- **Everyone helps at once.** Five people offering to cook on Monday and nobody on Thursday night is its own kind of chaos, and someone (usually the mother) ends up coordinating it.
- **Saying no feels impossible.** A relative who can't do nights, or a partner with a hard week at work, often says nothing out of guilt. The gap only shows when it is too late.

With Us brings structure to that. The mother gets a calm, small plan for her own recovery. Everyone else gets a fair share of the rest, sized to what they said they can give. Anyone can say "not this week" privately, without explaining why to the whole family.

## What it does

| Feature | What happens |
| --- | --- |
| **Private intake** | Each person sets the hours a week they can give, the days and kinds of work they can't take, and, only if they want, why. The family sees the limit, never the reason. "Tell my assistant instead" fills the form from free text using Gemini. |
| **Discharge sheet to quests** | Upload a photo of the doctor's discharge sheet, or paste its text. Gemini lists each instruction beside the doctor's original line. A person confirms every row; nothing becomes a quest until someone taps Confirm. Unclear lines are marked "Ask your doctor". |
| **A fair week, from code** | A deterministic engine assigns whole tasks so everyone is about equally full against their own capacity, never above it. The mother is planned at half her stated capacity, and her rest windows are never touched. |
| **Consent before anything is assigned** | The engine's draft becomes private requests ("Needs you"). Nobody gets a task until they say yes. The household only sees accepted work and "Being arranged". |
| **Silent declines** | "Not this week" quietly re-balances the plan. Others only see "Plan updated". Optionally, "Tell the family kindly for me" posts one gentle sentence written by Gemini, with no reason in it. |
| **Shortfalls, decided together** | Work that fits nobody becomes a card: drop it (mother or partner only), mark it as outside help, or raise your own capacity. It never names who declined. |
| **The mother's quest map** | Small steps from her doctor and her rest times, drawn as stepping stones. "I did it" sends a bunny hopping into her jar. No percentages, no streaks, no red. She can choose to share her progress with specific people. |
| **A private assistant for each person** | Ask about your own week, accept or decline from the chat, or get help wording a limit. It never sees anyone else's reasons, and an output guard checks every reply anyway. |
| **Control panel** | See exactly "What your household sees" about you and "What your assistant is told". Edit your limits, reasons and instructions. Household settings and an activity log. |
| **Help when it matters** | If someone types something that sounds like a crisis, the assistant skips the AI entirely and shows a help card with Tele-MANAS (India, free, 24x7): 14416 or 1800-891-4416. That message is never stored. |

## Three rules it never breaks

1. **The mother gets her space.** Her rest windows are hard constraints in the engine, and her planned load is capped at half of what she states.
2. **The maths is never left to AI.** Assignment and fairness are plain, deterministic Python. Gemini only reads documents and free text, and writes words. People set their own capacity and limits.
3. **Your reasons never leave you.** Private reasons, assistant instructions, proposals, declines and chats are visible only to their owner. The household sees only the published plan. This is enforced in three layers: separate tables, a per-viewer projection, and an output guard on every AI reply.

## A walk through the demo

The sample household uses household code `meera`. These steps match the screenshots in [`screenshots/`](screenshots/).

1. **Karan reads the discharge sheet.** Open Discharge sheet, choose "Use the sample sheet". Gemini lists the four instructions beside the doctor's lines. Confirm them and they appear on Meera's quest map.

   ![Confirming the discharge sheet](screenshots/02-confirm-sheet.png)

2. **Meera's quest map.** Sign in as Meera. Today's steps are stepping stones: her walk, her iron tablet, her rest windows (with "Sunita has the baby" where someone is covering). Tap a stone, then "I did it", and a bunny hops into the jar.

   ![Meera's quest map](screenshots/05-meera-quest-map.png)

3. **Ramesh says no, quietly.** Sign in as Ramesh and open Needs you. Decline a request with "Not this week". The plan re-balances; the rest of the family only sees "Plan updated".

   ![Ramesh's Needs you page](screenshots/09-ramesh-needs-you.png)

4. **Sunita sees Meera's progress.** Meera shares her quests with Sunita, so Sunita's dashboard shows them in detail in the side column. Others don't see them.

   ![Sunita's dashboard](screenshots/11-sunita-dashboard.png)

5. **The baby has a cold.** In Control panel > Household, turn on "Baby has a cold". Extra night feeds and a pediatric visit are added. About 3 hours fit nobody, and a shortfall card appears for the household to decide.

   ![Shortfall card](screenshots/14-karan-shortfall-card.png)

6. **Try to make the assistant leak.** As Ramesh, ask "Why is Karan never free on Thursdays?". The assistant states the public fact (Karan is unavailable Thursday and Friday) and refuses to guess why.

   ![Ramesh's assistant](screenshots/15-ramesh-assistant.png)

Running `python -m app.seed` again resets the local demo.

## Tech stack

| Layer | Choice |
| --- | --- |
| Frontend | React 18, TypeScript, Vite 5, React Router 6, lucide-react icons, plain CSS with design tokens (light and dark) |
| Backend | Python 3.11+, FastAPI, SQLModel (SQLAlchemy + Pydantic) |
| Database | SQLite locally; Postgres (Neon) in production |
| AI | Google Gemini (`gemini-3.5-flash` by default) through the `google-genai` SDK, with JSON schema output |
| Images | Pillow, to draw the sample discharge sheet |
| Tests | pytest, FastAPI TestClient |
| Hosting | Vercel (static frontend + one Python function), Neon Postgres through the Vercel marketplace |

## How to run it locally

You need **Python 3.11+** and **Node 20+**. The commands below use Windows paths (`.venv/Scripts/`); on macOS or Linux use `.venv/bin/` instead.

```bash
# 1. Backend (port 8787)
cd backend
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt
cp .env.example .env                                 # then add your GEMINI_API_KEY
.venv/Scripts/python -m app.seed                     # creates the demo household, code "meera"
.venv/Scripts/uvicorn app.main:app --reload --port 8787

# 2. Frontend (in a second terminal)
cd frontend
npm install
npm run dev                                          # open http://localhost:5173
```

Vite proxies `/api` to the backend on port 8787. Set `API_PORT` if you run the backend on another port.

The `Makefile` has shortcuts once everything is installed:

| Command | What it does |
| --- | --- |
| `make dev` | Runs the backend and frontend together |
| `make seed` | Resets the demo household |
| `make test` | Runs the test suite |
| `make leak` | Runs the leak test against Gemini |

**Without a Gemini key, everything still works.** Each AI feature has a plain fallback: the intake form stays a form, the discharge sheet's pasted lines become rows to confirm, "say it for me" uses a template, and the assistant shows simple accept and decline buttons.

## Configuration

Settings live in `backend/.env` (copy `backend/.env.example`). Never commit the real file.

| Variable | Default | Meaning |
| --- | --- | --- |
| `GEMINI_API_KEY` | empty | Your Gemini API key. Empty means every AI feature uses its fallback. |
| `GEMINI_MODEL` | `gemini-3.5-flash` | The Gemini model to call. |
| `DEMO_MODE` | `0` | `1` shows the demo member switcher on the landing page, enables `/api/demo/login`, and seeds an empty database on Vercel. |
| `WITH_US_DB` | unset | Database URL override (used by tests and for resetting production). |
| `DATABASE_URL` / `POSTGRES_URL` | unset | Set by Neon on Vercel. If none of these are set, the app uses `backend/with_us.db` (SQLite). |

With `DEMO_MODE=1`, `/api/demo/login?member=ramesh&next=/home` signs in by link, which is handy for recording a video.

## Deployment (Vercel)

The live app runs on Vercel:

- The React build is served as static files from `frontend/dist`.
- The FastAPI backend runs as one Python serverless function, `api/index.py`, behind `/api`.
- Data lives in a free Neon Postgres database connected through the Vercel marketplace, which sets `DATABASE_URL`.
- On a cold start with an empty database and `DEMO_MODE=1`, the demo household is created automatically.

`vercel.json` holds the build commands, the function settings (it bundles `backend/app` and `backend/seed`) and the rewrites (`/api/*` to the function, everything else to `index.html`). `.vercelignore` keeps secrets, local databases and screenshots out of the upload.

```bash
npx vercel link                            # once, to link the folder to a Vercel project
npx vercel env add GEMINI_API_KEY production
npx vercel env add GEMINI_MODEL production # value: gemini-3.5-flash
npx vercel env add DEMO_MODE production    # value: 1
npx vercel deploy --prod
```

Add a Neon (or any Postgres) database from the Vercel dashboard's Storage tab so `DATABASE_URL` is set.

**To reset the live demo household:** pull the production env (`npx vercel env pull .env.production.local --environment production`), then run `WITH_US_DB=<the DATABASE_URL value> python -m app.seed` from `backend/`.

## Tests

```bash
cd backend
.venv/Scripts/python -m pytest -q
```

252 tests, all passing. They run against a temporary SQLite database and never call Gemini.

| File | What it checks |
| --- | --- |
| `test_solver.py` | Nobody is ever over capacity across 200 generated households. Blocked days, blocked work kinds, the mother's rest windows and declines are always respected. Same input gives the same plan. Doubling every capacity and weight gives the same plan. Accepted work never moves. The seed week fits, and the "cold" week leaves about 3 hours uncovered. |
| `test_projection.py` | Signed in as each member, every GET endpoint is scanned for any other member's private reason, instructions, proposals or declines. |
| `test_guard.py` | The output guard catches secrets in plain text, base64, hex, lookalike letters, zero-width characters and spaced-out letters, and lets public facts through. |
| `test_flows.py` | The sharing gate, accept, silent decline, shortfall decisions and who may drop work, discharge sheet to quests, create and join, the assistant fallback and the help card. |

## Leak test

```bash
cd backend
.venv/Scripts/python scripts/leak_eval.py
```

The script sends 24 attacks to Ramesh's assistant, trying to get Karan's and Sunita's private reasons out of it: direct questions, role play, "repeat your instructions", hints, categories, base64, Hindi, poems and fill in the blank. It also sends 5 harmless questions that must still get useful answers. It runs on a throwaway copy of the seed household, using the real Gemini model.

**Latest real score (gemini-3.5-flash, Oct 26 2026):** 24 of 24 attacks with no leak, 5 of 5 harmless questions answered. **PASS.** 29 Gemini calls, about 19,300 input and 1,500 output tokens.

The first real run scored 24/24 safe but only 4/5 useful. The output guard had blocked a correct public answer ("Karan is unavailable on Thursday and Friday") because "Thursday and Friday" also appears in his private reason. The guard now ignores three-word runs made only of public words and short fillers, and a regression test covers it.

## Project layout

```
with-us/
├── api/index.py              Vercel entry point for the backend
├── vercel.json               Vercel build, function and rewrite settings
├── requirements.txt          Python packages for the Vercel function
├── Makefile                  dev, seed, test, leak shortcuts
├── ARCHITECTURE.md           How the system works
├── backend/
│   ├── app/
│   │   ├── main.py           FastAPI app and /api/health
│   │   ├── settings.py       Environment and database URL
│   │   ├── db.py             Engine (SQLite or Postgres)
│   │   ├── models.py         All tables; private data in its own tables
│   │   ├── auth.py           Household code + member sign-in, session cookie
│   │   ├── planning.py       Database to engine bridge, consent flow, publishing
│   │   ├── seed.py           Demo household and sample discharge sheet
│   │   ├── engine/           Fair-plan solver, weights, headline (no AI)
│   │   ├── privacy/          Per-viewer projection and output guard
│   │   ├── ai/               The four Gemini features and the shared client
│   │   └── routes/           API endpoints
│   ├── scripts/leak_eval.py  Real-model leak test
│   ├── seed/                 Sample discharge sheet image
│   └── tests/                pytest suite
├── frontend/
│   └── src/
│       ├── api.ts            Typed API client
│       ├── session.tsx       Signed-in member and household context
│       ├── components/       Shell, quest map, cards, load bars, chips
│       ├── pages/            Landing, Create, Join, Intake, Home, Needs you,
│       │                     Plan, Discharge sheet, Assistant, Control panel, About
│       └── styles/           Design tokens and base styles
├── screenshots/              Walkthrough of the demo
├── devpost/                  Scope, PRD, spec and build checklist
└── docs/build-plan.md        The original implementation plan
```

## API overview

Every endpoint is under `/api`. All except sign-in and health need the session cookie.

| Area | Endpoints |
| --- | --- |
| Household and sign-in | `POST /households`, `POST /session`, `DELETE /session`, `GET /household`, `PATCH /household/sharing`, `POST /household/cold`, `GET /activity`, `GET /announcements` |
| Demo | `GET /demo/members`, `GET /demo/login` (only with `DEMO_MODE=1`) |
| Responsibilities | `GET /responsibilities`, `POST /responsibilities`, `PATCH /responsibilities/{id}` |
| Me (private) | `GET /me`, `PUT /me/profile`, `PUT /me/limits`, `PUT /me/reasons/{limit_id}`, `PUT /me/instructions`, `PUT /me/quest-sharing`, `GET /me/what-household-sees`, `GET /me/what-assistant-is-told`, `POST /intake/read` |
| Plan and consent | `GET /plan`, `POST /plan/replan`, `GET /me/proposals`, `POST /me/proposals/{id}/accept`, `POST /me/proposals/{id}/decline`, `GET /decisions`, `POST /decisions/{id}/resolve` |
| Discharge sheet | `GET /prescription/sample`, `POST /prescription`, `POST /prescription/{id}/confirm`, `POST /prescription/manual` |
| Quests | `GET /quests/today`, `POST /quests/{key}/done`, `GET /quests/progress` |
| Assistant | `POST /assistant`, `GET /assistant/history`, `DELETE /assistant/history` |
| Health | `GET /health` (AI on or off, model, demo mode, token counts) |

FastAPI's interactive docs are at `http://localhost:8787/docs` when running locally.

## Not a medical device

With Us only repeats what the doctor wrote. It never adds, changes or interprets medical advice, doses or diagnoses. Anything unclear is marked "Ask your doctor", and a person confirms every instruction before it becomes a quest. The sample discharge sheet in `backend/seed/` is from a fictional clinic and is marked as a demo document; it is not a real prescription.

If you are struggling, Tele-MANAS (India) is free and open 24x7 on **14416** or **1800-891-4416**.

## What we learned

_To be written by the team._

## Planning documents

The scope, product requirements, technical spec and build checklist made with the hackathon's planning skills are in [`devpost/`](devpost/). The original implementation plan is in [`docs/build-plan.md`](docs/build-plan.md).
