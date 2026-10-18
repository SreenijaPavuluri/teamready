# Demo video script (3:00)

**Screen layout:** ASI:One on the left (signed in as the new hire), `/activity` on the right so judges watch the agents
talk. Have a second browser profile signed in to ASI:One as the manager (Jordan). Open `/canary` in a tab, ready.

**Before recording:** agents running (`python scripts/run_agents.py`, seven "mailbox connected"); `TRACKER_DUE_MINUTES=2`;
run one throwaway question so nothing is cold; clear old chats.

| Time | Screen | Say |
| --- | --- | --- |
| 0:00 | Title card, then ASI:One | "It's Maya's first week. She's stuck, she doesn't know who to ask, and the docs are a maze. Meet Unblock: seven agents that help her, can't make things up, and do the work for her." |
| 0:15 | Type to unblock-orchestrator: **"What's our deploy process for staging?"** Point at the card and the activity map | "Every claim is checked word for word against an approved doc; you can see the source. The old runbook is two years stale, so Unblock leaves it out and offers to tell its owner." |
| 0:40 | **"How many vacation days do I get?"** | "The docs don't say. Most assistants would guess. Unblock won't: in our eval it answered zero of five trick questions. It finds the right person, with a fair, visible score, and drafts the message." |
| 1:00 | **"Do my checklist"**: show the plan card, click **Approve and do them** | "Now the part a chatbot can't do. Unblock plans her whole checklist: it joins her Slack channels, enrolls her in security training and books the 1:1 with an invite. It won't touch MFA, and analytics access needs her manager." |
| 1:25 | Switch to the manager's ASI:One: unblock-manager **"pending"** → **"approve"**. Back to Maya: "I filed it for you: ACC-…" | "Only Jordan, a person, can approve. The moment they do, Unblock files the access form for her. Every action showed exactly what it would do and waited for a yes." |
| 1:50 | `/canary` → **Run the canaries**; the three lanes fill in | "Here's the twist. Before real hires start, three synthetic new hires go through onboarding with only the docs." |
| 2:10 | Point at the walls: Detour (confirmed, 13), stale-doc trap (confirmed, 10), two predicted | "They find the same walls real new hires hit, the analytics checklist step and the stale deploy runbook, plus two nobody has reported yet." |
| 2:25 | Click the CREAO run link on the edit fix; show it on agent.creao.ai | "For each wall, CREAO's Doc Steward drafts a one-line fix. We check it quotes the doc exactly, and the doc owner decides. New hires stop being your QA team." |
| 2:45 | `/activity` totals, then the eval table | "Seven agents on Agentverse, Sonnet behind a verifier, 40 out of 40 on our eval, and a human approving every action. That's Unblock." |

## 30-second backup cut

If ASI:One is slow on the day, record this from the Workday view (`/workday`) instead: switch between Maya, Jordan and
Elena with the toggle at the top, and press **Do my checklist** in the Onboarding Journey. It runs the same logic in the web app:
1. (0:00) "Unblock: an onboarding buddy that can't make things up and does the work." Ask the staging question; show
   the source and the stale-doc flag.
2. (0:10) Click **Do my checklist for me** → **Approve and do them**; show the "Done for you" panel.
3. (0:20) `/canary` → Run; "synthetic new hires find the walls before real people do, and CREAO drafts the fix."

## Things to say if asked
- **"Is it acting on real systems?"** The company is fictional, so Slack, the Learning Hub, the calendar, IT Help and the
  Access Hub are demo adapters behind one action call. The calendar invite is a real email. Swapping in the Slack,
  LMS, calendar or ServiceNow API changes only the adapter.
- **"Where's the AI?"** Sonnet reasons and drafts; plain code verifies, gates and acts. The CREAO Doc Steward drafts the
  doc fixes.
