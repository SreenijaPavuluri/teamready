# Unblock

![tag:innovationlab](https://img.shields.io/badge/innovationlab-3D8BD3)
![tag:hackathon](https://img.shields.io/badge/hackathon-5F43F1)

**A "who do I ask?" agent network for new hires that can't make things up.**
Built for LA Hacks AI Hackathon 2026: Workday "Build the Future of Work with AI" and the Fetch.ai ASI:One Agent Challenge.

A new hire describes a blocker in ASI:One. Unblock answers only from approved company docs, verifies every claim word for word, finds the right person to ask when the docs fall short, drafts the message, and sends it only after the new hire approves. Access requests go to a human manager. Pay, performance and harassment questions go straight to a person. People Ops gets an anonymous Friction Map of what keeps blocking new hires, and pays for the full report through the Fetch.ai Payment Protocol.

## The problem

New hires get stuck on questions nobody has answered for them. Ownership lives in people's heads, docs disagree or go stale, and the same busy senior engineer gets every question. AI assistants over internal docs make it worse when they invent a confident answer: a new hire can't tell a real answer from a made-up one.

## Agents

All five agents are registered on Agentverse, implement the Chat Protocol, and can be used on their own from ASI:One. Run `python scripts/addresses.py` to print the addresses for your seeds.

| Agent | What it does | Address |
| --- | --- | --- |
| `unblock-orchestrator` | ASI:One front door. Risk gate, coordinates the others, Interactive Cards, executes approved actions, relays manager decisions. | `agent1q...` |
| `unblock-knowledge` | Search over approved docs, Sonnet drafts claims with quotes, a plain-code verifier keeps only verified claims, flags stale and conflicting docs, computes confidence. | `agent1q...` |
| `unblock-routing` | Who to ask: 50% skills, 30% team, 20% availability, fairness rotation, learns from "wrong person". | `agent1q...` |
| `unblock-manager` | Human approval gate. Only the manager can approve access requests. | `agent1q...` |
| `unblock-insights` | Friction Map from anonymous events (groups of 5+ only). Full report with an AI-drafted doc fix for 0.1 FET via the Payment Protocol. | `agent1q...` |

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
4. every number in the claim also appears in the quote ("100 USD" can't hide behind a quote that says "75 USD").

Only verified claims are shown. The model's free text never is. If nothing verifies, Unblock routes the question to a person instead of guessing.

### Confidence

Computed in code from four visible factors, with no fixed base points: retrieval strength (30), agreement between sources (25), doc freshness (15), and the share of claims verified (30). Below 60, or when docs disagree, Unblock routes to a person.

## Trust panel

Every answer and every proposed action shows: what Unblock did, sources with dates and owners, confidence and its factors, claims blocked, why this person, the data used and not used, and Approve / Edit / Reject.

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
```

It reports behavior accuracy, citation accuracy, helper accuracy, unsupported claims blocked, and how many adversarial questions were answered instead of routed. Results are written to `eval/RESULTS_<mode>.md`.

Baseline with no model (extractive): 34/40 behavior, 27/27 citations, 2/2 helpers, but it "answers" **5 of 5** adversarial questions with irrelevant quotes. Recognizing when the docs don't actually answer the question is exactly the judgment Sonnet adds, and the verifier makes sure that judgment can't turn into an invented fact.

<!-- Paste your Sonnet results here after running the eval. -->

## Run it

**Requirements:** Python 3.11+, an Anthropic API key, an Agentverse API key.

```bash
pip install -r requirements.txt
cp .env.example .env          # fill in the keys and your own agent seeds
python scripts/generate_events.py
python -m pytest -q           # 33 tests, no network needed
./scripts/run_all.sh          # runs the five agents as separate processes (logs in logs/)
# or: python agents/main.py   # all five in one process
```

With `AGENTVERSE_API_KEY` set, each agent starts in mailbox mode and prints an Agent Inspector link. Open each link once and connect the mailbox; the agent then appears in Agentverse with its README and badges. In ASI:One, search for **unblock-orchestrator** (or @-mention its address) and start chatting.

**Try it without ASI:One or an API key:**

```bash
UNBLOCK_LLM=extractive python scripts/local_demo.py
```

This runs the five real agents plus a test new hire and a test manager, and prints the whole conversation: verified answer, stale-doc flag, routing to a person, "wrong person", an access request approved by the manager agent, and the high-impact stop.

**Real email (optional):** set the SMTP values in `.env` (a Gmail app password works) and `DEMO_RECIPIENT_OVERRIDE` to an inbox you control. Without SMTP, approved emails are saved to `outbox/` and the reply says "Simulated". Unblock never claims a send that didn't happen.

**Lock the manager gate:** set `MANAGER_ALLOWED_SENDERS` to the manager's ASI:One address. Otherwise the manager agent says it's in demo mode.

## Demo script (3 minutes)

1. **Hook:** "It's Maya's third week. She's stuck, and she doesn't know who to ask."
2. "How do I set up my dev environment?" Verified, cited answer and the trust panel.
3. "What's our deploy process for staging?" The legacy runbook is flagged as two years stale and left out; Unblock offers to tell its owner.
4. "How many vacation days do I get?" The docs don't say. Unblock doesn't guess: it routes to People Ops and drafts the message. Click "wrong person"; the ranking updates live.
5. "I need access to the analytics dashboard." A request goes to the manager agent; the manager approves in their own chat; Maya is notified.
6. "Can the AI decide whether I deserve a promotion?" Stopped before any search, with the right person named.
7. Switch to People Ops: "friction map", then "full report", pay 0.1 FET, get the drafted fix for the onboarding checklist, send it to the doc owner.
8. Close on the eval numbers.

## Project layout

```
agents/      the five uAgents (+ readmes/ for Agentverse profiles, main.py to run all)
unblock/     shared library: retrieval, verifier, confidence, risk gate, routing, friction map, flow, cards
data/        synthetic company: 30 docs, 15 people, the new hire, policies, events
eval/        40 labeled questions and the eval runner
scripts/     local end-to-end demo, event generator, address printer
tests/       33 tests: verifier, risk gate, retrieval, routing, friction map, conversation flow, Sonnet parsing
```

All company data is fictional (Lumen Labs). No real or confidential employee data is used.
