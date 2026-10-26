---
doc: prd
status: approved
---

# With Us: Product Requirements

A web app that plans one week of recovery, baby duties and house chores around a new mother, shared fairly and privately across her household.
Source: `scope.md > The Unique Kernel`, `scope.md > Why This Matters to the Learner`. Detailed source: `docs/build-plan.md`.

## The Core Journey
Source: `scope.md > The Core Loop`, `scope.md > What "Working" Looks Like`.

1. Someone lands on the With Us landing page and taps "Create a household".
2. They pick "Baby girl" or "Baby boy" on the baby screen, then fill in "Who is recovering?" (her name, baby's name, date the baby arrived, anything to keep in mind).
3. They set their own capacity, blocked days and work kinds, and optionally a private reason. They get a household code and member ID to share.
4. Other members join with the code and do the same private intake. They can type freely and let the assistant fill the form instead.
5. Someone uploads or pastes the doctor's discharge sheet. Each extracted line is shown beside the doctor's original words; a person edits, removes or confirms. Confirmed lines become the mother's recovery quests.
6. The mother and partner each turn on "Let With Us share out the work". Only then does the plan get built.
7. Each member finds proposals in "Needs you": accept, or "Not this week" (optionally "Tell the family kindly for me"). Accepted items appear in the shared plan. A decline quietly re-balances the plan; nobody is told who said no.
8. The mother opens her quest map: small steps from her doctor and rest she is guaranteed. She taps a stone, reads the doctor's line and who is covering for her, taps "I did it", and a bunny hops into her jar.
9. If work doesn't fit, a shortfall card asks the household to decide: drop it, mark it as outside help, or someone raises their own capacity.
10. Anyone can ask their private assistant about their own week. It never reveals anyone else's reasons.

Success: the week is published, everyone's load is within their own capacity, the mother's rest is protected, and no private reason has appeared on anyone else's screen.

## Screens and Layout
Desktop width only, filling the full screen, with a left sidebar. No phone layout (learner decisions during the build).

- **Sidebar:** With Us logo, a card for the mother ("Meera, recovering, week 2" with the baby icon), then Home, Needs you (badge count), Plan, Assistant, Control panel. Bottom: "Add a task", About, current member avatar, dark-mode moon.
- **Landing:** headline "Let her rest. We've got the rest.", subline about private limits and a fair week, two action cards (Create, Join), an illustration card that animates from "Meera doing it all" to a shared week, three points: "Her rest comes first", "Shared by what each person can carry", "Your reasons stay with you". No statistics.
- **Baby screen:** "Welcome, little one" / "Tell us about your baby." Two large cards, original line-art baby faces (bow for girl, curl for boy). Continue disabled until one is picked.
- **Create step 1 ("Who is recovering?")**, **Create step 2 / Join / Intake** (capacity slider, day picker, work-kind chips, locked private reason box, "Tell my assistant instead"; the mother's version adds rest windows, the ceiling sentence and quest-sharing toggles).
- **Mother home: quest map.**
- **Dashboard** (everyone else's home).
- **Needs you:** proposal cards and shortfall cards.
- **Discharge sheet:** upload or paste, a reading state, then confirm rows.
- **Assistant:** private chat with a lock header.
- **Control panel:** tabs You, Household, Activity.

## Look and Feel
Source: `scope.md > Inspiration & Identity`.

- Warm cream page, white cards, baby pink surfaces, deeper rose for buttons and links. Baby pink is never a button background with white text.
- Source Sans 3. Page titles large and bold, generous body text (17 px).
- Calm and gentle tone. Pill chips. One rounded load bar split by member colour.
- The mother never sees percentages, health numbers, streaks or red. Missed quests roll to tomorrow quietly.
- Dark mode via a moon toggle, remembered per browser. Animations respect reduced motion.
- No em dashes in any copy. The reference app's name and demo names never appear.

## Features and Behavior

### Household setup and sign-in
- As someone starting a household, I want to create it in a few steps so the family can join.
  - [ ] Baby screen requires a choice before Continue; the choice shows as an icon on the mother's sidebar card and quest map header.
  - [ ] After creation I see the household code and my member ID with copy buttons.
  - [ ] Joining with code plus member ID signs me in; a new name creates a new member.
  - [ ] In demo mode, the login page offers a member switcher.

### Private intake and limits
- As a family member, I want to say what I can carry without explaining myself to everyone.
  - [ ] I set hours a week (0 to 40) with "We measure your share against this, not an even split."
  - [ ] I block days and work kinds (Nights, Driving, Cooking, Appointments, Baby care, Cleaning, Errands).
  - [ ] My reason goes in a locked box: "Only you and your assistant see this. Your family sees the limit, never the reason."
  - [ ] "Tell my assistant instead" turns free text into suggested form fields I review before saving; anything that sounds like a reason lands in the private box.
  - [ ] The mother also sets rest windows and sees "We plan for less than this, so you can rest."

### Discharge sheet to quests
- As the household, I want the doctor's instructions turned into quests without the app adding any medical advice.
  - [ ] Uploading the sample sheet shows four rows, each with the doctor's original line beside it.
  - [ ] Unclear lines show as amber "Ask your doctor" rows.
  - [ ] Nothing becomes a quest until a person taps Confirm. Rows can be edited or removed first.
  - [ ] If reading fails, a manual "Add an instruction" form works the same way.

### Fair weekly plan
- As anyone in the household, I want a week that's fair against each person's own capacity.
  - [ ] Nobody is ever assigned above their own capacity; the mother is planned at half of what she states.
  - [ ] Nobody gets work on a blocked day, a blocked work kind, a task they declined this week, or (for the mother) during her rest.
  - [ ] The dashboard headline reads one of: "The week is shared fairly. Meera's rest is protected.", "[Name] is carrying the most this week.", or "[N] hours a week still need someone."
  - [ ] The same inputs always produce the same plan.
  - [ ] The plan isn't built until both the mother and the partner have turned on sharing; until then dashboards show a setup card.

### Consent and silent declines
- As a family member, I want nothing assigned to me without my yes, and my no kept private.
  - [ ] Each proposal appears only in my Needs you.
  - [ ] Accept locks it into the shared plan.
  - [ ] "Not this week" re-balances quietly; other members see only "Plan updated".
  - [ ] Items still being asked about show as "Being arranged" with no name.
  - [ ] If I turn on "Tell the family kindly for me", one kind line (no reason, no blame) is posted from me. Off by default.

### Shortfall decisions
- As the household, I want to decide together when the work doesn't fit.
  - [ ] Card reads like "3 hours a week still need someone: Cooking (Saturday)." and never names who declined.
  - [ ] Options: drop or pause (mother or partner only), mark as outside help, raise my own capacity.
  - [ ] Turning on the "baby has a cold" demo variant produces a shortfall of about 3 hours.

### Mother's quest map
- As the recovering mother, I want small, calm steps and to know I'm covered.
  - [ ] Header "Good morning, Meera" with the baby icon and "Today has N small steps. Everything else is covered."
  - [ ] A winding path of stones, one per quest today; the current one gently pulses; done stones fill in.
  - [ ] Tapping a stone opens a sheet with the quest, "From your doctor" original line, who is covering ("Ramesh has the baby"), and "I did it".
  - [ ] "I did it" makes a bunny hop into the Bunny jar. Bunnies are the only number she sees.
  - [ ] Rest quests appear for each rest window with who has the baby.
  - [ ] Below the map: "Your week is covered" with responsibility and owner, no percentages.
  - [ ] Footer "Need to talk to someone?" opens the help card.

### Everyone else's dashboard
- As a family member, I want to see how the work around her recovery is shared.
  - [ ] Header "How the work around Meera's recovery is shared", the headline, and the load bar with name, percent of their own capacity and task count.
  - [ ] Mine / Everyone tabs, List / Calendar toggle.
  - [ ] Side cards: Your assistant ("Re-plan now"), next task, Waiting on you, This week counts, Meera's quests in detail (each step, its time, the doctor's line, done or not, who is covering, and her bunnies), only if she shares with me.

### Private assistant
- As a family member, I want help with my own week from an assistant that keeps everyone's secrets.
  - [ ] Header "Only you can see this conversation."
  - [ ] Answers questions about my week, helps me accept, decline or word a limit, drafts a "say it for me" line.
  - [ ] Suggested actions appear as buttons; nothing changes until I tap.
  - [ ] Asked about someone else's reasons, it says it's theirs to share and only tells what's in the plan.
  - [ ] No medical advice; recovery questions point back to the doctor's instructions.
  - [ ] If someone mentions harming themselves, a help card appears: "You don't have to carry this alone. Talk to someone now: Tele-MANAS 14416 (India)." The message isn't kept.

### Control panel
- As a family member, I want to manage my own details and see exactly what others see.
  - [ ] You tab: code and member ID with copy, profile, capacity, days, work kinds, private reason per limit, "Instructions for your assistant", "See what your assistant is told", "What your household sees".
  - [ ] Household tab: members and the two sharing switches.
  - [ ] Activity tab: generic lines only.

### Privacy proof
- As a reviewer, I want evidence the privacy promise holds.
  - [ ] Signed in as any member, no other member's reason, instructions, proposal or decline appears anywhere on screen or in responses.
  - [ ] A leak test of at least 20 attacks plus 5 harmless questions prints a real score; the video quotes only that number.

## States and Boundaries
- **First use:** sharing switches off, so dashboards show a setup card and no plan exists.
- **Empty quests:** before the discharge sheet is confirmed, the quest map shows only rest quests and a gentle prompt.
- **AI unavailable or blocked:** every AI feature falls back (plain intake form, manual instruction form, canned assistant help with plain buttons, template "{name} can't take {task} this week."). The demo never breaks.
- **Shortfall:** work that fits nobody becomes a decision card, never a silent overload.
- **Persistence:** the household, members, limits, plan, quests and bunnies persist across sessions.
- **Permissions:** only the mother or partner can drop or pause tasks and set the sharing switches; each person changes only their own capacity; only the mother sees and logs her quests unless she shares progress.
- **Missed quests:** roll to tomorrow quietly. No streaks or penalties.

## Product Decisions
- Fairness is measured against each person's own capacity, not an even split, because people can carry different amounts.
- The mother is planned at half her stated capacity, because her recovery comes first.
- Declines are never announced; the plan re-balances quietly, because guilt about saying no is part of the problem (`scope.md > Why This Matters to the Learner`).
- A person confirms every discharge-sheet line, because the app must never add or interpret medical advice.
- The mother sees bunnies, not numbers, because the experience should feel calm, not like a scoreboard.
- Assignment and fairness are never decided by AI; AI only reads text and drafts words.

## What We're Building
Everything under Features and Behavior, with the seed household (Meera, Karan, Ramesh, Sunita), the sample discharge sheet labelled as a demo document, and the "baby has a cold" variant.

## Deferred From the POC
- **Hosting:** optional; reviewers watch the video.

## Possible Later Enhancements
- Real accounts, calendar sync and reminders once the core idea is proven.

## Non-Goals
- Logins beyond household code plus member ID: not needed to prove the kernel.
- Calendar sync and push notifications: integration work outside the fairness and privacy idea.
- Lab values, symptom tracking, diagnosis, dosing advice: medical territory.
- Native mobile apps, a phone-width layout and payments: out of proportion; the app is desktop only.

## Open Questions
- Tele-MANAS number (14416) must be verified before the video. Can wait for the build.
