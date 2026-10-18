# Unblock

![tag:innovationlab](https://img.shields.io/badge/innovationlab-3D8BD3)
![tag:hackathon](https://img.shields.io/badge/hackathon-5F43F1)

**A "who do I ask?" agent network for new hires that can't make things up, and Canary New Hires: synthetic new hires who test your onboarding docs before your people do.**
Built for LA Hacks AI Hackathon 2026: Workday "Build the Future of Work with AI", the Fetch.ai ASI:One Agent Challenge, and CREAO Best Team Empowerment.

A new hire describes a blocker in ASI:One. Unblock answers only from approved company docs, verifies every claim word for word, finds the right person to ask when the docs fall short, drafts the message, and sends it only after the new hire approves. Access requests go to a human manager. Pay, performance and harassment questions go straight to a person. People Ops gets an anonymous Friction Map of what keeps blocking new hires, and pays for the full report through the Fetch.ai Payment Protocol.

## Unblock does the work, not just answers

A chatbot tells a new hire what to do. Unblock does it for them, after they approve:

| Say | Unblock does (in the Lumen system) | Who approves |
| --- | --- | --- |
| "Do my checklist" | Plans every onboarding step: does the ones it can, sends the gated one to the manager, says plainly which it can't (MFA, in-person IT setup) | You, then the manager for access |
| "Which Slack channels should I join?" → **Do it** | Joins #announcements, #ask-people-ops, the team channel and the role's channels (Slack) | You |
| "Sign me up for security training" | Enrolls in Security Awareness Training, due 14 days after the start date (Learning Hub) | You |
| "Schedule my 1:1 with my manager" | Books a 30-minute 1:1 with the agenda from the docs and sends the calendar invite (Calendar, real .ics email) | You |
| "My laptop screen is cracked" | Opens an IT ticket through go/it-help with the description; the Tracker follows up (IT Help) | You |
| "I need access to the analytics dashboard" | Drafts the request to the manager, and **files the go/analytics-access form the moment the manager approves** (Access Hub) | You, then the manager |

Every action is backed by the approved doc that describes it (shown on the card), fills its form from what Unblock
already knows, passes free text through the Guardian, and runs only after approval. Each one leaves a record with an id
("Done for you" in the portal, `what have you done` in ASI:One). It never touches passwords or MFA, pay, performance or
benefits. Lumen's systems are fictional like the company, so each is a small adapter (`unblock/autopilot.py`); a real
deployment swaps in the Slack, LMS, calendar, ServiceNow or access-request API behind the same call.

## Canary New Hires: your docs get a CI pipeline

Every onboarding tool waits for a real new hire to get stuck, then helps. Unblock's **canaries** get stuck first.

Three synthetic new hires (a Data Analyst, a Backend Engineer, a Product Designer in the EU office) go through
onboarding with nothing but the company docs. They walk the New Hire Systems Checklist step by step, then their role's
tasks, and ask Unblock how to do each one, through the same risk gate and verifier a real new hire gets. Where a canary
couldn't do a step from what the docs say, that's a **wall**:

| Wall | What the canary found |
| --- | --- |
| Detour | The checklist says what to do but not how, and doesn't link the doc that does (found only after rephrasing) |
| Stale-doc trap | An out-of-date doc still comes up for the task and gives different instructions |
| Circular | The only source is the checklist itself: no approved doc says how |
| Dead end | No approved doc covers it for that office |

Gated steps (production access needs the manager) and high-impact ones (a person handles them) are working as designed,
not walls. Each wall is checked against the Friction Map: **confirmed** if real new hires already hit it, **predicted**
if nobody has yet. Each one gets a fix for the doc owner: a one-line edit drafted by the CREAO Doc Steward (and checked
word for word), an archive note for a stale doc, or a request to the right person to write the missing step. People Ops
approves before anything is sent.

**Backtest on our synthetic company:** with no knowledge of the Friction Map, the canaries rediscover the two walls real
new hires hit most (13 blockers on analytics access from the checklist, 10 on the legacy deploy runbook) and predict two
nobody has reported yet (no doc says how to turn on MFA; no badge doc for the EU office).

Watch it at **`/canary`**, or message **unblock-canary** in ASI:One: `run`, `report`, `fixes`, `approve F1`. It also runs
on a schedule (`CANARY_INTERVAL_HOURS`, default daily). Code: `unblock/canary.py`, `agents/canary_agent.py`,
personas in `data/canaries.json`. Keyless demo: `UNBLOCK_LLM=extractive python scripts/local_canary_demo.py`.

## The problem

New hires get stuck on questions nobody has answered for them. Ownership lives in people's heads, docs disagree or go stale, and the same busy senior engineer gets every question. AI assistants over internal docs make it worse when they invent a confident answer: a new hire can't tell a real answer from a made-up one.

## Agents

Seven agents, each registered on Agentverse with the Chat Protocol and usable on its own from ASI:One. Run `python scripts/addresses.py` to print the addresses for your seeds. **Go live:** [`docs/GO_LIVE.md`](docs/GO_LIVE.md).

| Agent | What it does | Address |
| --- | --- | --- |
| `unblock-orchestrator` | ASI:One front door. Risk gate, coordinates the others, Interactive Cards, does approved tasks in Lumen's systems (Slack, training, calendar, IT tickets, access forms), relays manager decisions. | `agent1q...` |
| `unblock-knowledge` | Search over approved docs, Sonnet drafts claims with quotes, a plain-code verifier keeps only verified claims, flags stale and conflicting docs, computes confidence. | `agent1q...` |
| `unblock-routing` | Who to ask: 50% skills, 30% team, 20% availability, fairness rotation, learns from "wrong person". | `agent1q...` |
| `unblock-manager` | Human approval gate. Only the manager can approve access requests. | `agent1q...` |
| `unblock-insights` | Friction Map from anonymous events (groups of 5+ only). Full report with an AI-drafted doc fix for 0.1 FET via the Payment Protocol. | `agent1q...` |
| `unblock-tracker` | Follows up when a message or request gets no answer, with a reminder sent only after approval. | `agent1q...` |
| `unblock-canary` | Canary New Hires: synthetic new hires walk the onboarding docs through `unblock-knowledge`, find walls before real hires do, and draft fixes for the doc owners. | `agent1q...` |

### What each agent may do (and nothing more)

Every agent gets only the tools its job needs. The **Guardian** is not a separate agent: it is plain code that every draft passes through before it can be sent, and it can only raise risk, never lower it.

| Agent | Tools it gets | Data it sees | Can it act? |
| --- | --- | --- | --- |
| Orchestrator | Risk gate, Guardian, calls to the other agents, email after approval, the Lumen system adapters (Slack, Learning Hub, Calendar, IT Help, Access Hub) | The question, the new hire's role, team and office | Only after the new hire approves (access forms also need the manager) |
| Knowledge | Doc search, the model, the verifier | Approved company docs | Read only |
| Routing | Helper ranking, feedback | Each person's skills, team, availability and question load | Read only (ranks people) |
| Manager | Hold requests, send decisions | The request, its business reason and verified evidence | Only a human manager decides |
| Insights | Friction Map, doc-fix drafts, payments | Topics and doc ids of past blockers, no names or messages | Drafts a fix; the doc owner publishes it |
| Tracker | Its follow-up list, reminder drafts, email after approval | What was sent, to whom, and when | Only after the new hire approves |
| Canary | Questions to the knowledge agent as fictional new hires, the Friction Map, fix drafts (CREAO) | Approved docs, aggregate blocker counts; never a real person | Drafts fixes; only People Ops can send one |
| Guardian (code) | Rules for pay, performance, benefits, harassment, health, personal data and secrets | Each outgoing draft | Can only stop a draft |

## Sponsor tracks

Full checklist with what each sponsor asks for and the manual steps: [`docs/TRACKS.md`](docs/TRACKS.md).

| Track | How Unblock uses it |
| --- | --- |
| Workday | The product: a new-hire agent with visible responsible-AI controls and a People Ops Friction Map. Reads the new hire's profile from a Workday Build development tenant ([setup](docs/WORKDAY.md)) |
| Fetch.ai | Seven uAgents on Agentverse (one of them sends synthetic new hires through the others), Chat Protocol, ASI:One, Interactive Cards, Payment Protocol (FET) |
| CREAO (Team Empowerment) | The Doc Steward agent on CREAO drafts every doc fix, from the Friction Map and from the walls Canary New Hires find (API Trigger, async), and a scheduled Weekly Digest agent tells doc owners on Slack ([setup](docs/CREAO.md)). Agent ID: `TODO` · Run: `TODO share link` |
| Gemini | Hybrid retrieval with Gemini embeddings; Gemini as a drop-in reasoning model behind the same verifier |
| Snowflake | Cortex chat completions REST API as a third reasoning model |
| Tiger Data | Friction events in a TimescaleDB hypertable, 30-day view from a continuous aggregate |
| ElevenLabs | Voice onboarding buddy: an ElevenLabs agent calls our verified-answer endpoint ([setup](docs/ELEVENLABS.md)) |
| Vultr + GoDaddy | Docker deploy of the web app, agents and HTTPS on one Vultr server, on your domain ([steps](docs/DEPLOY.md)) |
| Solana | People Ops can pay for the report in USDC with Solana Pay, confirmed on-chain |
| DEV | Article draft in `docs/dev_post.md` |

## Web app

`uvicorn web.app:app --port 8080` serves a landing page where anyone can ask a question and see verified claims, blocked claims, sources and confidence; the live Friction Map; the agent addresses; and `POST /api/voice/ask` for the voice agent. It is read-only: actions only happen in ASI:One after approval.

**New Hire Portal (`/app`)** is the web version of the Unblock chat: ask, see verified answers with sources,
approve/edit/reject every draft (Guardian checks each version), "wrong person", access requests the manager approves on
the Manager tab, Tracker reminders, a first-two-weeks checklist from the approved docs, and the profile from Workday
when connected. Details: [`docs/PORTAL.md`](docs/PORTAL.md).

**Canary New Hires (`/canary`)**: press Run and watch three synthetic new hires walk the docs step by step, then see
the walls (confirmed or predicted), the estimated hours a cohort would lose, and the drafted fixes with a before/after.
Sending a fix needs the People Ops key (`PORTAL_MANAGER_KEY`).

**Agent Activity (`/activity`)** shows the agents working, live: a map of who's messaging whom, and a feed of every
step, check and stop (risk gate, verifier, Guardian, routing, manager approval, Tracker, payment, the CREAO run, the
canaries). All seven agents and the web app append to `data/runtime/activity.jsonl` (`unblock/activity.py`); the page polls
`/api/activity`. People's messages appear only when they hold no secrets or health details, and drafted emails never do.
With nothing happening live, **Watch recorded demo** replays `data/demo_activity.json`, a real local run of all six agents.
Turn it off with `UNBLOCK_ACTIVITY=false`.

## How it works

```
 New hire (ASI:One chat)
        |
        v
 unblock-orchestrator ---- risk gate (code, before any model call)
        |                    |-- pay / performance / benefits eligibility / harassment -> STOP, name the right person
        |                    |-- elevated access -> prepare request -> unblock-manager (human approves)
        |                    '-- routine -> continue
        |
        |-- KnowledgeRequest --> unblock-knowledge
        |                          BM25 search -> Sonnet (claims + quotes) -> VERIFIER -> confidence
        |                          only verified claims come back; stale/other-region docs flagged
        |
        |-- RoutingRequest ----> unblock-routing   (weighted score + fairness rotation + feedback)
        |
        |-- drafts message / 1:1 invite / access request  ->  review card: Approve / Edit / Reject
        |-- on approve: send email (+ .ics invite)  or  ApprovalRequest -> unblock-manager
        |-- FrictionEvent (topic only) --> unblock-insights  <-- People Ops: "full report" -> RequestPayment (FET)
```

If a specialist agent doesn't respond in time, the orchestrator runs the same step locally and says so in the trust trace, so the new hire is never left waiting.

### The verifier

Sonnet must return every fact as a claim with a supporting quote and a doc id. Plain code then keeps a claim only if:

1. it cites a doc that was actually retrieved for this question,
2. the quote appears word for word in that doc (case, quotes, dashes and spacing normalized),
3. the quote is at least 4 words long, and
4. the quote isn't cut out of a negated sentence, and the claim keeps any "not" the quote has,
5. most of the claim's words appear in the quote, so the claim can't say more than its source, and
6. every number in the claim also appears in the quote ("100 USD" can't hide behind a quote that says "75 USD").

Only verified claims are shown. The model's free text never is. If nothing verifies, Unblock routes the question to a person instead of guessing.

### Confidence

Computed in code from four visible factors, with no fixed base points: retrieval strength (30), agreement between sources (25), doc freshness (15), and the share of claims verified (30). Below 60, or when docs disagree, Unblock routes to a person.

## Trust panel

Every answer and every proposed action shows: what Unblock did, sources with dates and owners, confidence and its factors, claims blocked, why this person, the data used and not used, and Approve / Edit / Reject.

**Guardian:** every draft (messages, 1:1 invites, access requests, follow-ups) is checked before it can be sent. Drafts that mention pay, performance, benefits or harassment, health details, an ID or card number, a password or an API key are stopped until edited.

**Unblock will never:** send or file anything without approval · grant access or approve its own requests · read private DMs, performance reviews or pay data · present an answer as fact without a source.

## Responsible AI (Workday's five principles)

| Principle | How Unblock meets it |
| --- | --- |
| Transparent | Every claim cites its source line; the trust panel shows steps, sources, confidence factors and reasons. |
| Fair | Helper ranking uses only job-relevant factors, shown on screen. Fairness rotation spreads questions across qualified people. Protected characteristics are never inputs. |
| Accountable | Nothing is sent without the new hire's approval. Access requests need a human manager. High-impact topics stop and go to a person. Doc fixes need the doc owner. |
| Privacy-preserving | Synthetic data only. Friction events store a topic and doc ids, never names or message text, and groups under 5 are hidden. Feedback stores source ids only. |
| Reliable | The verifier blocks unsupported claims; stale and conflicting docs lower confidence or route to a person; failed agent calls fall back locally; failed email sends say so. |

## Evaluation

`eval/questions.json` holds 40 labeled questions: 24 the docs answer, 8 they don't (5 of them adversarial, designed to tempt an invented answer), 5 high-impact questions that must stop, and 3 access requests that must go to the manager.

```
python eval/run_eval.py                    # Sonnet
python eval/run_eval.py --llm extractive   # no-model baseline
python eval/run_eval.py --llm gemini --embeddings gemini   # Gemini + hybrid retrieval
python eval/run_eval.py --llm snowflake    # Snowflake Cortex
```

It reports behavior accuracy, citation accuracy, helper accuracy, unsupported claims blocked, and how many adversarial questions were answered instead of routed. Results are written to `eval/RESULTS_<mode>.md`.

Baseline with no model (extractive): 34/40 behavior, 27/27 citations, 2/2 helpers, but it "answers" **5 of 5** adversarial questions with irrelevant quotes. Recognizing when the docs don't actually answer the question is exactly the judgment Sonnet adds, and the verifier makes sure that judgment can't turn into an invented fact.

**With Sonnet (sonnet-5-5), Oct 17:**

| Metric | Sonnet | No model (extractive) |
| --- | --- | --- |
| Behavior accuracy | **40/40** | 34/40 |
| Citation accuracy | **27/27** | 27/27 |
| Adversarial questions answered instead of routed | **0/5** | 5/5 |
| Unsupported claims blocked by the verifier | 2 | 0 |
| Unsupported claims shown to the user | **0** | 0 |
| Helper accuracy | 7/8 | 2/2 |

Sonnet refused to guess on all five trick questions, and the verifier still caught two claims it couldn't find word for
word in the docs. Full table: [`eval/RESULTS_anthropic.md`](eval/RESULTS_anthropic.md).

## Run it

**Requirements:** Python 3.11+, an Anthropic API key, an Agentverse API key.

```bash
pip install -r requirements.txt
cp .env.example .env          # fill in the keys and your own agent seeds
python scripts/generate_events.py
python -m pytest -q           # 88 tests, no network needed
./scripts/run_all.sh          # runs the seven agents as separate processes (logs in logs/)
# or: python agents/main.py   # all seven in one process
```

With `AGENTVERSE_API_KEY` set, each agent starts in mailbox mode and prints an Agent Inspector link. Open each link once and connect the mailbox; the agent then appears in Agentverse with its README and badges. In ASI:One, search for **unblock-orchestrator** (or @-mention its address) and start chatting.

**Try it without ASI:One or an API key:**

```bash
UNBLOCK_LLM=extractive python scripts/local_demo.py
```

This runs the real agents plus a test new hire and a test manager, and prints the whole conversation: verified answer, stale-doc flag, routing to a person, "wrong person", an access request approved by the manager agent, and the high-impact stop.

**Real email (optional):** set the SMTP values in `.env` (a Gmail app password works) and `DEMO_RECIPIENT_OVERRIDE` to an inbox you control. Without SMTP, approved emails are saved to `outbox/` and the reply says "Simulated". Unblock never claims a send that didn't happen.

**Payments:** the insights agent checks that each `CommitPayment` matches its open request (reference, FET, amount, its own wallet, not expired) and cancels on any mismatch or if the report fails. Confirming the transaction hash on the Fetch ledger is left to the ASI:One wallet in this build.

**Safety between agents:** the orchestrator only accepts approval decisions from the manager agent's address, and the manager agent only accepts requests from the orchestrator.

**Lock the manager gate:** set `MANAGER_ALLOWED_SENDERS` to the manager's ASI:One address. Otherwise the manager agent says it's in demo mode.

## Demo script (3 minutes)

1. **Hook:** "It's Maya's third week. She's stuck, and she doesn't know who to ask. What if someone had hit that wall before her?"
2. "How do I set up my dev environment?" Verified, cited answer and the trust panel.
3. "What's our deploy process for staging?" The legacy runbook is flagged as two years stale and left out; Unblock offers to tell its owner.
4. "How many vacation days do I get?" The docs don't say. Unblock doesn't guess: it routes to People Ops and drafts the message. Click "wrong person"; the ranking updates live.
5. **"Do my checklist."** Unblock lays out all six steps: it does three (Slack channels, security training, the 1:1 with
   an invite), sends analytics access to the manager, and says it won't touch MFA. Approve. The manager approves in their
   own chat, and Unblock files the go/analytics-access form by itself. "It doesn't tell Maya what to do. It does it."
6. "Can the AI decide whether I deserve a promotion?" Stopped before any search, with the right person named.
7. Switch to People Ops: "friction map", then "full report", pay 0.1 FET, get the drafted fix for the onboarding checklist, send it to the doc owner.
8. **Canary New Hires:** open `/canary`, press Run. Three synthetic new hires walk the docs; they hit the same analytics
   and staging walls real hires did (confirmed), and two nobody has hit yet (predicted). Send the CREAO-drafted fix.
   "New hires stop being your QA team."
9. Close on the eval numbers.

## Project layout

```
agents/      the seven uAgents (+ readmes/ for Agentverse profiles, main.py to run all)
unblock/     shared library: retrieval, verifier, confidence, risk gate, routing, friction map, flow, cards
data/        synthetic company: 30 docs, 15 people, the new hire, policies, events
eval/        40 labeled questions and the eval runner
scripts/     local end-to-end demos (chat, payment, canaries), event generator, address printer, deploy.sh
web/         landing page, live demo, Canary New Hires page, Friction Map dashboard, voice tool endpoint (FastAPI)
docs/        track checklist, ElevenLabs and deploy guides, DEV article draft, local demo transcript
tests/       88 tests: canaries, verifier, risk gate, retrieval, routing, friction map, payments (FET + Solana), providers, web, conversation flow
Dockerfile, docker-compose.yml   one-server deploy with HTTPS
```

All company data is fictional (Lumen Labs). No real or confidential employee data is used.
