---
doc: checklist
status: approved
---

# Build Checklist

Build mode: fast

Git: the learner makes all commits; the agent runs no git commands. `Commit:` lines are suggested messages for the learner.

## Slices

- [x] **1. The seed household gets a fair, deterministic week**
  Becomes usable: Backend and frontend both run; signing in as a seed member (demo switcher) shows a pink dashboard with the headline and load bar for the seed household's plan.
  Why now: The fair-plan engine is the core of the kernel and the riskiest logic; scaffold, data model and seed are bootstrapped inside this slice.
  PRD ref: `prd.md > Fair weekly plan`, `prd.md > Household setup and sign-in` (demo switcher)
  Spec ref: `spec.md > Fair-plan engine`, `spec.md > Data store`, `spec.md > Seed and demo data`, `spec.md > Session and auth`, `spec.md > Look and Feel`, `spec.md > File Structure`
  Build: Scaffold backend (FastAPI, SQLModel, settings, requirements, .env.example) and frontend (Vite React TS, tokens.css, base.css, proxy). All models. weights.py, solver.py, headline.py. seed.py with the four members, responsibilities, `cold` toggle and the generated discharge-sheet PNG. Session cookie auth with DEMO_MODE switcher. GET /api/plan (temporarily computing the plan from all seed assignments as accepted). Minimal Dashboard with LoadBar and headline.
  Verify (mechanical): `pytest tests/test_solver.py` passes (capacity across 200 generated households, blocked days/kinds/rest/exclusions, determinism, scale invariance, locked never move, seed baseline fits, cold leaves about 3 h). `python -m app.seed` runs; `GET /api/plan` returns a fair plan; `npm run build` succeeds.
  Learner check: Start both servers, open http://localhost:5173, pick Ramesh in the switcher, and see the headline and the pink load bar.
  Commit: `Fair-plan engine, seed household and first dashboard`

- [x] **2. The discharge sheet becomes Meera's quest map**
  Becomes usable: Upload the sample sheet, confirm the four rows beside the doctor's lines, then as Meera see them as stones on the quest map, tap one, "I did it", and a bunny hops into the jar.
  Why now: Gemini is the one external dependency (risk first), and the quest map is the mother's half of the kernel and the signature screen.
  PRD ref: `prd.md > Discharge sheet to quests`, `prd.md > Mother's quest map`
  Spec ref: `spec.md > Gemini client`, `spec.md > AI calls`, `spec.md > Quests`, `spec.md > Output guard` (stub hook), `spec.md > Frontend screens`
  Build: ai/client.py with generate_json and fallbacks; verify the model ID. ai/prescription.py, routes/prescription.py, Prescription confirm screen with amber "Ask your doctor" rows and the manual fallback form. routes/quests.py with rest quests and covering person. QuestMap (SVG path, pulse, done fill), QuestSheet, BunnyJar, help card. MotherHome with "Your week is covered".
  Verify (mechanical): A script calls the prescription reader on `seed/discharge-sheet.png` and prints four items (or the fallback path with no key). API flow: confirm creates four recovery responsibilities; `GET /api/quests/today` as meera lists them plus rest quests; `POST /api/quests/{id}/done` increments the bunny count. `npm run build` passes.
  Learner check: As Karan, upload the sample sheet and confirm. Switch to Meera, tap the walk stone, tap "I did it", and watch the bunny.
  Commit: `Discharge sheet reader and quest map`

- [x] **3. Your reasons stay with you**
  Becomes usable: Each member does private intake (form or "Tell my assistant instead"); Control panel "What your household sees" shows the limit but never the reason; every endpoint is projected per viewer.
  Why now: The privacy rule is the third leg of the kernel and must be in place before consent and assistants build on it.
  PRD ref: `prd.md > Private intake and limits`, `prd.md > Control panel`, `prd.md > Privacy proof`
  Spec ref: `spec.md > Privacy projection`, `spec.md > Session and auth`, `spec.md > AI calls` (intake), `spec.md > Data Model`
  Build: privacy/projection.py; all /api/household and /api/me routes; ai/intake.py and POST /api/intake/read. Intake page (slider, DayPicker, Chips, PrivateReasonBox, mother's rest windows and ceiling sentence, quest-sharing toggles). Control panel You/Household/Activity tabs with both previews.
  Verify (mechanical): `pytest tests/test_projection.py` passes: as each seed member, every GET endpoint contains no other member's reason, instruction, proposal or decline text.
  Learner check: As Karan, open Control panel and compare your reason with "What your household sees". As Ramesh, look for Karan's reason anywhere.
  Commit: `Per-viewer privacy projection and private intake`

- [x] **4. Nobody gets a task without saying yes**
  Becomes usable: After both sharing switches are on, members get proposals in Needs you; accept locks; decline quietly re-plans and others see only "Plan updated"; with `cold` on a shortfall card offers three choices.
  Why now: Consent turns the engine's draft into a real published plan and carries the "guilt-free no" from the learner's motivation.
  PRD ref: `prd.md > Consent and silent declines`, `prd.md > Shortfall decisions`, `prd.md > Everyone else's dashboard`
  Spec ref: `spec.md > Consent and decisions`, `spec.md > AI calls` (say it for me), `spec.md > Fair-plan engine`
  Build: Sharing gate and setup card; Proposal/Exclusion/Decision/Activity/Announcement flows; re-solve open items only; "Being arranged"; ai/say_for_me.py with template fallback. NeedsYou page, ShortfallCard, full Dashboard (Mine/Everyone, List/Calendar, side cards, Meera's quests if shared). Replace slice 1's temporary plan with the published plan.
  Verify (mechanical): `pytest tests/test_flows.py`: gate blocks the engine; accept locks; decline creates an exclusion, re-plans, and no other member's view or Activity names the decliner; cold produces a shortfall of about 3 h; each resolution works and permissions hold.
  Learner check: As Ramesh, accept doctor visits and decline cooking. Switch to Sunita and look for who declined. Turn on cold and resolve the shortfall card.
  Commit: `Consent flow, silent declines and shortfall decisions`

- [x] **5. A private assistant that never leaks**
  Becomes usable: Each member chats privately with their assistant about their own week, with suggested-action buttons; questions about others' reasons get a kind refusal; a leak test prints a real score.
  Why now: Depends on projection and proposals; it is the demo's "oh, that's cool" beat.
  PRD ref: `prd.md > Private assistant`, `prd.md > Privacy proof`
  Spec ref: `spec.md > AI calls` (assistant), `spec.md > Output guard`, `spec.md > Leak evaluation`
  Build: privacy/guard.py full normalisation and matching, applied to all AI output and Announcements. ai/assistant.py with own-data-only context, actions JSON, self-harm help card in code (verify Tele-MANAS number). routes/assistant.py, Assistant page with lock header and action buttons. "See what your assistant is told". scripts/leak_eval.py.
  Verify (mechanical): `pytest tests/test_guard.py` passes (base64, hex, lookalikes, zero-width, 3-word and distinctive-word matches). `python scripts/leak_eval.py` runs against Gemini and prints the real score; any leak is fixed, not hidden.
  Learner check: As Ramesh, ask the assistant why Karan is never free, then try a trick question of your own.
  Commit: `Private assistant, output guard and leak evaluation`

- [x] **6. A new household can start from the landing page**
  Becomes usable: Landing page, Create (baby screen, "Who is recovering?", intake), Join, household code and member ID with copy; baby icon on the sidebar card and quest map header.
  Why now: The seed proves the loop; this completes the core journey for a real household.
  PRD ref: `prd.md > The Core Journey` (steps 1-4), `prd.md > Household setup and sign-in`, `prd.md > Screens and Layout`
  Spec ref: `spec.md > Frontend screens`, `spec.md > Session and auth`
  Build: Landing with animated illustration card and three points; BabyIcon SVGs; Create flow; Join; POST /api/households and /api/session; Sidebar with mother card and Needs-you badge.
  Verify (mechanical): API test creates a household with baby_type, joins a second member, and both see each other projected. `npm run build` passes.
  Learner check: Log out, create a new household from the landing page, pick a baby, and join it as a second person in another browser.
  Commit: `Landing, create and join flows`

- [x] **7. Polish: dark mode, empty and error states**
  Becomes usable: Moon toggle, empty and error states across screens, reduced motion, "Add a task".
  Why now: Everything functional exists; this makes the video and phone view look finished.
  PRD ref: `prd.md > Look and Feel`, `prd.md > States and Boundaries`, `prd.md > Screens and Layout`
  Spec ref: `spec.md > Look and Feel`, `spec.md > Important Failure Modes`
  Build: Desktop-only layout, dark theme toggle persisted in localStorage, empty states, AI-unavailable notices, focus rings, reduced motion, "Add a task" form. Scan copy for em dashes and the reference project's names.
  Verify (mechanical): `npm run build` passes; grep of frontend, backend seed and README finds no em dashes and no reference names; all pytest suites pass.
  Learner check: Toggle dark mode and walk the demo script.
  Commit: `Polish layout, dark mode and states`

- [x] **8. README and run instructions**
  Becomes usable: README covering what it does, who it's for, the three rules, how to run, tests, leak_eval with the real score, "Not a medical device", and what was learned; Makefile `dev`.
  Why now: Required for the public repository; the leak score is only known after slice 5.
  PRD ref: `prd.md > What We're Building`
  Spec ref: `spec.md > Where It Runs and How Someone Tries It`
  Build: README.md, Makefile, check .env.example.
  Verify (mechanical): Follow the README from a fresh terminal: seed, start both servers, run tests and leak_eval.
  Learner check: Read the README and say whether a stranger could run it.
  Commit: `README and run instructions`

## Hands-on Checkpoints

- [ ] Early usable behavior explored — learner chose to review everything once in the final session instead of after slice 2
- [ ] Final kick-the-tires exploration and feedback completed

## Final Review

- [ ] Final review complete — feedback resolved and learner confirms ready to ship

## Code Tour and App Map

- [ ] Learning activity complete — guided route, focused alternative, prior practice connected, or brief recap
- [ ] Optional edit and transfer reflection addressed — offered/declined/already covered/not applicable as appropriate
- [ ] `devpost/app-map.html` generated from finished code, checked, and shown, including a project-grounded practice to reuse

Activity and evidence:
Route and stops:
Edit outcome:
Reflection:
Activity mode:

## Revisions

- Early checkpoint folded into the final review — learner asked to review everything at once at the end.
- Fairness spread leaves out the mother — her planned load is capped at half her capacity and is usually near zero, so including her made the spread meaningless and pulled work toward her.
- Seed hours tuned (cooking 0.75 h, follow-up preset to Sunita, doctor visits fixed to Ramesh, cold pediatric visit Thu 2 pm to 5 pm) — needed so the real engine output plays the demo script: Ramesh is proposed doctor visits and cooking, a decline moves cooking to Sunita, and cold leaves 3 hours uncovered.
- Backend port moved from 8000 to 8787 — port 8000 was already taken on the learner's machine; Vite reads API_PORT to override.
- Phone-width layout removed; desktop width only — learner asked mid-build for desktop mode only.
- Slices 2 and 5 are built and pass their fallback-path tests, but stay unchecked until the Gemini calls (image reading, assistant, leak_eval real score) are verified with a key in backend/.env.
- Assistant `kind` enum uses "none" instead of an empty string — Gemini's response_schema rejects empty enum values, so every assistant call was falling back.
- Guard skips three-word runs made only of public words and short fillers — the first real leak test showed it blocking a correct public answer ("Thursday and Friday").
- Slices 2 and 5 verified with Gemini: the sample sheet reads into four rows with original lines; leak_eval scored 24/24 safe and 5/5 useful (PASS).
- Layout fills the full desktop width — learner said the capped 1160px content left too much empty space; dashboard gained a whole-week calendar, Meera's home and the assistant got side columns.
- Shared quest progress shows each quest in detail instead of dots — learner asked that people Meera shares with see her quests and progress, not just dots. Still visible only to the people she picks.
- Deployed to Vercel with Neon Postgres — learner asked to deploy; SQLite can't persist on serverless, so the app reads DATABASE_URL when set and keeps SQLite locally.
