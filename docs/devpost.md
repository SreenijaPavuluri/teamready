# Unblock: Devpost submission

**Tagline:** An onboarding agent network that does the work for new hires, can't make things up, and tests your docs
with synthetic new hires before real people start.

**Links** (fill in after deploy): live site `https://LIVE-DOMAIN/` · New Hire Portal `/app` · Canary New Hires `/canary`
· Agent Activity `/activity` · GitHub `https://github.com/SreenijaPavuluri/unblock` · CREAO run
https://agent.creao.ai/share/0773babf9c5d456f0fc0446a58d6da2f

---

## Inspiration

Your first weeks at a job are a maze of small blockers: which form, which channel, who owns the dashboard, is this doc
still right? New hires lose days to questions nobody has answered for them. They interrupt the same busy senior people,
and they hit the same walls the last cohort hit. AI assistants over internal docs make it worse when they invent a
confident answer: a new hire can't tell a real answer from a made-up one.

We wanted an onboarding buddy that (1) only says what it can prove, (2) actually does the work instead of handing you a
to-do list, and (3) stops the same walls from hitting the next person.

## What it does

**For the new hire (in ASI:One, or the web portal):**
- **Verified answers.** Every claim is checked word for word against an approved company doc before the new hire sees
  it. Stale docs are flagged and left out. If the docs don't answer, Unblock doesn't guess: it finds the right person,
  with a visible, fair score, and drafts the message.
- **It does the work.** "Do my checklist" makes Unblock plan the whole onboarding checklist. It joins the right Slack
  channels, enrolls the new hire in required training, books the first 1:1 with the manager (with a calendar invite)
  and opens IT tickets. For analytics access it drafts the request to the manager and **files the access form the
  moment the manager approves**. It says plainly what it won't do: MFA and passwords, and in-person IT setup. Every
  action shows exactly what will happen and runs only after the new hire approves.
- **Safety by design.** A risk gate runs before any model call: pay, performance, benefits eligibility and harassment
  questions go straight to a named person. A Guardian check stops any draft or form that contains a password, an ID
  number or health details. Only a human manager can approve access.
- **Follow-up.** A Tracker agent notices when nobody replied and offers a polite reminder (sent only after approval).

**For People Ops and doc owners:**
- **Friction Map:** anonymous patterns of what keeps blocking new hires (topics and doc paths only, groups of 5+), sold
  as a full report through the Fetch.ai Payment Protocol.
- **Canary New Hires:** three synthetic new hires (a Data Analyst, a Backend Engineer, a Product Designer in the EU) walk
  the onboarding docs through the same verified-answer pipeline, step by step, before real people start. They find the
  walls (a checklist step with no how-to, a stale runbook that still comes up, a missing doc for one office) and check
  each one against the Friction Map: confirmed by real new hires, or predicted. On our synthetic company they rediscover
  the two walls real hires hit most (13 and 10 blockers) and predict two that nobody has reported yet.
- **Doc fixes, drafted by CREAO.** For each wall, the CREAO Doc Steward drafts a one-line fix. Unblock checks that it
  quotes the doc word for word, and the doc owner (a person) decides.

## How we built it

- **Seven Fetch.ai uAgents on Agentverse** (Chat Protocol, mailbox mode, ASI:One): `unblock-orchestrator` (front door,
  risk gate, Guardian, actions), `unblock-knowledge` (search + Sonnet + verifier), `unblock-routing` (who to ask),
  `unblock-manager` (the human approval gate), `unblock-insights` (Friction Map + Payment Protocol), `unblock-tracker`
  (follow-ups) and `unblock-canary` (Canary New Hires). They exchange typed messages (knowledge, routing, approval and
  tracking requests). Interactive Cards carry the review, approve and reject buttons. If a specialist doesn't answer in
  time, the orchestrator runs the same step locally and says so.
- **Sonnet (sonnet-5-5)** drafts claims with quotes; **plain Python decides** what's shown (the verifier checks
  quote presence, negation, word overlap and numbers). Confidence is computed in code from four visible factors.
- **CREAO:** the Doc Steward agent (API Trigger, async polling) drafts doc fixes for the Friction Map and the canaries.
  A Weekly Digest agent posts each doc owner's top gap to Notion.
- **Web app (FastAPI):** a New Hire Portal with the same conversation, a manager tab and a "Done for you" panel; the
  Canary New Hires page; and Agent Activity, a live map of every message between the agents.
- **Workday:** reads the new hire's name, title, organization and work email from a Workday Build development tenant
  (only those four fields), with a local fallback.
- 96 automated tests, a 40-question eval, Docker deploy.

## Challenges we ran into

- **Making "refuse to guess" measurable.** The extractive baseline "answered" all 5 adversarial questions with
  irrelevant quotes. With Sonnet behind the verifier, it answers none of them.
- **Model answers vary run to run, but the canaries must not.** Each checklist step is asked once and shared across
  canaries. When a canary rephrases, it judges the result on what the search found, which is deterministic. Four runs
  in a row give the same walls.
- **Agentverse mailboxes:** running all agents in one process left only some of them reachable. We moved to one process
  per agent, with a launcher that checks and retries every mailbox.
- **An SDK change mid-hackathon:** the current Anthropic SDK rejects `temperature` for the newest models, which silently
  routed every question to a person until we caught it in the eval.

## Accomplishments we're proud of

- **Eval with Sonnet: 40/40 behavior, 27/27 citations, 0/5 adversarial questions answered**, 2 unsupported claims
  blocked by the verifier and 0 shown to the user.
- An agent that does onboarding tasks end to end, including a manager-gated step, without ever acting on its own.
- Canary New Hires found real walls with no knowledge of the Friction Map.

## What we learned

The interesting part of an onboarding agent isn't the answer, it's the judgment around it: when not to answer, who
should decide, what to do on the new hire's behalf, and how to make the next person's first week easier.

## What's next

Real connectors behind the same action calls (Slack, the LMS, Google/Outlook calendar, ServiceNow, Workday time off),
canaries for every role and office, and measuring time-to-first-commit for new hires before and after.

---

## Sponsor tracks

**Fetch.ai: ASI:One Agent Challenge.** Seven uAgents registered on Agentverse in mailbox mode with the Chat Protocol,
usable from ASI:One. The orchestrator coordinates the knowledge, routing, manager and tracker agents with typed
messages. The manager agent is a human approval gate (only the configured manager's address can approve). The canary
agent sends synthetic new hires through the knowledge agent. Interactive Cards for every review. The insights agent
sells its full report through the Payment Protocol (FET). Try `unblock-orchestrator` with "do my checklist", or
`unblock-canary` with "run". Agent addresses are in the README.

**Workday: Build the Future of Work with AI.** A new-hire agent built on Workday's responsible-AI principles: every
claim cited and verified, approve-before-act on every action, a human manager for access, and high-impact topics handed
to a person. It reads the new hire's profile from a Workday Build development tenant (four fields only)
<!-- if the tenant isn't connected by submission, replace with: "with a local fallback profile in the demo" -->. For
People Ops, the Friction Map and Canary New Hires turn individual blockers into fixable patterns, and doc owners stay in
control.

**CREAO: Best Team Empowerment.** The CREAO Doc Steward (agent ID `b450ed0d-985d-4079-917f-d9f9ee75e812`) does the core
work of the doc-fix loop. Our backend calls it through the API Trigger, polls the run, and checks its reply quotes the
doc exactly. The doc owner, a person, approves. A second CREAO agent, the Weekly Digest, posts each doc owner's top gap
to Notion. Remove the Doc Steward and the docs never get fixed. Run:
https://agent.creao.ai/share/0773babf9c5d456f0fc0446a58d6da2f

<!-- MLH prizes: add a paragraph only for what is live at submission (e.g. Vultr + GoDaddy domain if deployed). -->

**Team:** Sreenija (integration, autopilot actions, Canary New Hires, go-live), Lux (Fetch.ai agents on Agentverse,
mailbox launcher, ASI:One fixes), Kusum (CREAO Doc Steward and Weekly Digest). <!-- adjust names and roles -->
