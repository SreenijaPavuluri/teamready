"""The orchestrator's conversation logic, independent of uAgents so it can be tested.

The agent supplies `services` (calls to the other agents, with local fallback)
and a `store` (per-sender state). Every reply is a Reply: text, plus an optional
Interactive Card.
"""
import asyncio
import re
import uuid
from dataclasses import dataclass

from . import render
from .data import load_people, load_user
from .llm import ExtractiveLLM, LLMError
from .risk import assess


@dataclass
class Reply:
    text: str
    kind: str | None = None
    payload: dict | None = None
    terminal: bool = False


APPROVE = {"approve", "approved", "yes", "send", "send it", "approve and send", "looks good", "go ahead"}
REJECT = {"reject", "no", "cancel", "don't send", "dont send", "stop"}
GREETINGS = {"hi", "hello", "hey", "help", "start", "what can you do", "what can you do?"}

INTRO = (
    "Hi, I'm **Unblock**, your onboarding buddy at Lumen Labs. No question is too basic.\n\n"
    "Tell me what's blocking you, in your own words. I'll answer only from approved company docs and show "
    "my sources, or find the right person to ask and draft the message for you. Nothing is sent without your OK.\n\n"
    "Try: \"How do I set up my dev environment?\", \"I need access to the analytics dashboard\", "
    "\"What's our deploy process for staging?\" or \"How many vacation days do I get?\""
)


def _command(text: str, selection: dict, has_pending: bool = False) -> str:
    action = str(selection.get("action", "")).lower()
    if action:
        return action
    t = text.lower().strip().rstrip(".!")
    if t in APPROVE:
        return "approve"
    if t in REJECT:
        return "reject"
    if t.startswith("edit:"):
        return "edit"
    if t in GREETINGS:
        return "intro"
    short = len(t.split()) <= 6
    for key, phrases in {
        "wrong_person": ["wrong person", "not the right person", "someone else"],
        "wrong_answer": ["looks wrong", "that's wrong", "thats wrong", "outdated", "incorrect"],
        "ask_helper": ["ask_helper", "ask someone", "ask a person", "still stuck"],
        "book_1_1": ["book_1_1", "book a 1:1", "schedule a 1:1", "book a meeting"],
        "friction_map": ["friction map", "friction"],
        "status": ["status", "any update"],
    }.items():
        if short and any(p in t for p in phrases):
            return key
    # Planner-routed card clicks arrive as a sentence that mentions the selection id.
    # Only read them that way when a draft is waiting and it isn't a question.
    if has_pending and "?" not in t:
        for key in ("approve", "reject", "wrong_person", "wrong_answer", "ask_helper", "book_1_1"):
            if re.search(rf"\b{key}\b", t):
                return key
    return ""


class Orchestrator:
    def __init__(self, services, store, llm_factory):
        self.s = services
        self.store = store
        self.llm_factory = llm_factory

    # ---------- helpers ----------
    def _user(self) -> dict:
        return load_user()

    async def _draft(self, purpose: str, recipient: dict, facts: list[str], question: str, ask: str = "") -> tuple[dict, str]:
        """purpose instructs the model; ask is the first-person line the no-model template uses."""
        user = self._user()
        try:
            llm = self.llm_factory()
            if getattr(llm, "mode", "") == "extractive":
                return llm.draft(ask or purpose, user, recipient, facts, question), ""
            return await asyncio.to_thread(llm.draft, purpose, user, recipient, facts, question), ""
        except LLMError as exc:
            return ExtractiveLLM().draft(ask or purpose, user, recipient, facts, question), f"\n(Template draft: the model is unavailable: {exc})"

    def _pending(self, kind: str, person: dict, draft: dict) -> dict:
        return {"type": kind, "to_id": person["id"] if "id" in person else person.get("person_id", ""),
                "to_name": person["name"], "to_role": person["role"], "to_email": person["email"],
                "subject": str(draft.get("subject", "Question from a new hire"))[:120], "body": str(draft.get("body", ""))[:1500]}

    def _review(self, state: dict, prefix: str = "") -> Reply:
        p = state["pending"]
        text = render.action_text(p, state.get("answer"), state.get("helper"), state.get("rotation_note", ""))
        return Reply((prefix + "\n\n" + text).strip(), "review", render.action_card(p, state.get("answer"), state.get("helper")))

    async def _route(self, sender: str, state: dict, exclude: list[str] | None = None) -> Reply:
        user = self._user()
        answer = state.get("answer") or {}
        routing = await self.s.routing(state["question"], user, answer.get("retrieved_doc_ids", []), exclude or [])
        chosen = routing.get("chosen")
        if not chosen:
            return Reply("I couldn't find anyone who clearly owns this. Try posting in #ask-people-ops; I didn't send anything.")
        people = load_people()
        person = dict(people[chosen["person_id"]])
        helper = {"person_id": chosen["person_id"], "name": chosen["name"], "role": chosen["role"], "reasons": chosen["reasons"]}
        facts = [c["text"] for c in answer.get("claims", [])]
        draft, note = await self._draft("Ask this person for help because the docs don't clearly answer the question. Mention what was already found, if anything.",
                                         person, facts, state["question"], ask="I couldn't find a clear answer in our docs and would really appreciate your help.")
        state.update(helper=helper, topic_key=routing.get("topic_key", ""), rotation_note=routing.get("rotation_note", ""),
                     excluded=list(exclude or []), pending=self._pending("message_helper", person, draft))
        self.store.set(sender, state)
        return self._review(state, note.strip())

    # ---------- entry points ----------
    async def handle(self, sender: str, text: str, selection: dict | None = None) -> Reply:
        selection = selection or {}
        state = self.store.get(sender) or {}
        cmd = _command(text, selection, has_pending=bool(state.get("pending")))

        if cmd == "intro" or (not text and not selection):
            return Reply(INTRO)
        if cmd == "friction_map":
            fmap = await self.s.friction_map()
            return Reply(render.friction_text(fmap) + "\n\nPeople Ops can buy the full report with fix proposals from the Unblock Insights agent.")
        if cmd == "status":
            waiting = state.get("awaiting")
            return Reply(f"Your request {waiting['request_id']} is waiting for {waiting['approver']}." if waiting else "Nothing is waiting on anyone right now.")

        pending = state.get("pending")
        if cmd == "approve" and pending:
            return await self._execute(sender, state)
        if cmd == "reject" and pending:
            state.pop("pending", None)
            self.store.set(sender, state)
            return Reply("Okay, I discarded the draft. Nothing was sent.")
        if cmd == "edit" and pending:
            new_body = re.sub(r"^\s*edit:\s*", "", text, flags=re.I).strip()
            if new_body:
                pending["body"] = new_body
                self.store.set(sender, state)
            return self._review(state, "Updated your draft.")
        if cmd == "wrong_person" and state.get("helper"):
            helper = state["helper"]
            await self.s.wrong_person(helper["person_id"], state.get("topic_key", ""))
            exclude = state.get("excluded", []) + [helper["person_id"]]
            reply = await self._route(sender, state, exclude)
            reply.text = f"Thanks, I noted that {helper['name']} isn't the right person for this and updated the ranking.\n\n" + reply.text
            return reply
        if cmd == "ask_helper" and state.get("question"):
            return await self._route(sender, state)
        if cmd == "book_1_1" and state.get("helper"):
            person = load_people()[state["helper"]["person_id"]]
            draft, note = await self._draft("Ask for a 30-minute 1:1 to get unblocked on the question.", person, [], state["question"],
                                             ask="Could we do a quick 30-minute 1:1 this week? I've sent a calendar invite.")
            state["pending"] = self._pending("book_1_1", person, draft)
            self.store.set(sender, state)
            return self._review(state, note)
        if cmd == "wrong_answer" and state.get("answer"):
            return await self._wrong_answer(sender, state)
        if cmd in ("approve", "reject", "edit", "wrong_person", "ask_helper", "book_1_1", "wrong_answer"):
            return Reply("There's nothing waiting for that right now. Ask me a question to get started.")

        return await self._new_question(sender, text)

    async def _new_question(self, sender: str, question: str) -> Reply:
        user = self._user()
        people = load_people()
        risk = assess(question)
        if risk.level == "stop":
            self.store.set(sender, {})
            human = people[risk.human_id]
            text = render.stop_text(risk.__dict__, human)
            return Reply(text, "detail", {"title": "This needs a person", "summary_rows": [
                {"label": "Category", "value": risk.category}, {"label": "Why I stopped", "value": risk.reason},
                {"label": "What I did", "value": "Stopped before searching, choosing anyone, or drafting"},
                {"label": "Right person", "value": f"{human['name']}, {human['role']}"}], "ctas": []}, terminal=True)

        answer = await self.s.knowledge(question, user)
        state = {"question": question, "answer": answer, "risk": risk.__dict__}

        if risk.level == "approval":
            manager = dict(people[user["manager_id"]])
            facts = [c["text"] for c in answer.get("claims", [])]
            purpose = (f"Ask my manager to approve {risk.category} for my work on {', '.join(user['projects'])}. "
                       "Explain the business reason briefly.")
            draft, note = await self._draft(purpose, manager, facts, question,
                                            ask=f"Could you approve my {risk.category} request? I need it for {', '.join(user['projects'])}.")
            state["pending"] = self._pending("access_request", manager, draft)
            state["helper"] = None
            self.store.set(sender, state)
            return self._review(state, f"**{risk.reason}**{note}")

        if answer.get("decision") == "answer":
            routing = await self.s.routing(question, user, answer.get("retrieved_doc_ids", []), [])
            chosen = routing.get("chosen")
            helper = {"person_id": chosen["person_id"], "name": chosen["name"], "role": chosen["role"], "reasons": chosen["reasons"]} if chosen else None
            state.update(helper=helper, topic_key=routing.get("topic_key", ""), rotation_note=routing.get("rotation_note", ""))
            text = render.answer_text(answer)
            stale = [c for c in answer.get("conflicts", []) if c.get("type") == "stale doc"]
            if stale:
                owner = people[stale[0]["owner_id"]]
                stale_title = render.doc_title(stale[0]["stale_doc_id"])
                note_draft, _ = await self._draft(f"Let the doc owner know '{stale_title}' looks out of date and points new hires to an old process.",
                                                  owner, [stale[0]["description"]], question,
                                                  ask=f"I think '{stale_title}' is out of date: it describes a different process than the current docs. Could you update or archive it?")
                state["pending"] = self._pending("doc_owner_note", owner, note_draft)
                text += (f"\n\nWant me to tell {owner['name']} (the owner) that the old doc is out of date? "
                         "Reply **approve** to send the note I drafted, or **reject**.")
            self.store.set(sender, state)
            await self.s.friction_event(answer["retrieved_doc_ids"][0] if answer.get("retrieved_doc_ids") else "", answer.get("retrieved_doc_ids", [])[:1], True)
            if stale:
                return Reply(text, "review", render.action_card(state["pending"], answer, helper))
            return Reply(text, "detail", render.answer_card(answer, helper))

        self.store.set(sender, state)
        return await self._route(sender, state)

    async def _wrong_answer(self, sender: str, state: dict) -> Reply:
        answer = state["answer"]
        cited = answer.get("citations", [])
        if not cited:
            return await self._route(sender, state)
        people = load_people()
        owner = dict(people[cited[0]["owner_id"]])
        draft, note = await self._draft(f"Flag that the answer from '{cited[0]['title']}' may be wrong or out of date and ask them to confirm.",
                                        owner, [c["text"] for c in answer.get("claims", [])], state["question"],
                                        ask=f"Something in '{cited[0]['title']}' doesn't seem to match what I'm seeing. Could you confirm it's still correct?")
        state["helper"] = {"person_id": owner["id"], "name": owner["name"], "role": owner["role"], "reasons": [f"owns {cited[0]['title']}"]}
        state["pending"] = self._pending("message_helper", owner, draft)
        self.store.set(sender, state)
        await self.s.source_feedback([c["id"] for c in cited])
        return self._review(state, f"Thanks for flagging it. I logged the source ids only, not your message.{note}")

    async def _execute(self, sender: str, state: dict) -> Reply:
        p = state.pop("pending")
        user = self._user()
        answer = state.get("answer") or {}
        if p["type"] == "access_request":
            request_id = "AR-" + uuid.uuid4().hex[:6].upper()
            evidence = [f"{c['text']} [{c['source_id']}]" for c in answer.get("claims", [])]
            status = await self.s.request_approval({
                "request_id": request_id, "category": state.get("risk", {}).get("category", "access"),
                "requester": {"name": user["name"], "role": user["role"], "team": user["team"], "email": user["email"]},
                "subject": p["subject"], "body": p["body"], "evidence": evidence, "sender": sender,
            })
            state["awaiting"] = {"request_id": request_id, "approver": p["to_name"]}
            self.store.set(sender, state)
            self.store.set(f"req:{request_id}", {"sender": sender})
            return Reply(f"Sent request **{request_id}** to {p['to_name']}'s approval agent. {status}\n"
                         "Only your manager can approve it. I'll message you here as soon as they decide.")
        ics = None
        if p["type"] == "book_1_1":
            from .actions import make_ics, next_slot
            ics = make_ics(f"1:1: {user['name']} and {p['to_name']}", user["email"], p["to_email"], next_slot())
        result = await self.s.send_email(p["to_email"], p["subject"], p["body"], user["email"], ics)
        self.store.set(sender, state)
        if p["type"] in ("message_helper", "book_1_1"):
            doc = (answer.get("retrieved_doc_ids") or [""])[0]
            await self.s.friction_event(doc, answer.get("retrieved_doc_ids", [])[:1], False)
        label = {"sent": "Sent", "simulated": "Simulated (email not configured)", "failed": "Not sent"}[result["status"]]
        follow = " Reply **wrong person** if they can't help, and I'll find someone else." if p["type"] == "message_helper" else ""
        return Reply(f"**{label}.** {result['detail']}{follow}")

    async def on_decision(self, decision: dict) -> tuple[str, Reply] | None:
        """Called when the manager agent sends back a decision."""
        sender = decision.get("sender") or (self.store.get(f"req:{decision['request_id']}") or {}).get("sender", "")
        if not sender:
            return None
        state = self.store.get(sender) or {}
        state.pop("awaiting", None)
        self.store.set(sender, state)
        if decision["decision"] == "approved":
            text = f"**{decision.get('approver', 'Your manager')} approved request {decision['request_id']}.**"
            claims = (state.get("answer") or {}).get("claims", [])
            if claims:
                text += "\n\nWhat happens next, from the docs:\n" + "\n".join(f"- {c['text']}  [{c['source_id']}]" for c in claims)
        else:
            text = f"**{decision.get('approver', 'Your manager')} didn't approve request {decision['request_id']}.**"
        if decision.get("note"):
            text += f"\n\nTheir note: {decision['note']}"
        return sender, Reply(text)
