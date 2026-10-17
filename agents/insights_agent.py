"""unblock-insights: the Friction Map, sold to People Ops through the Payment Protocol.

Free:  "friction map" -> top clusters (anonymous aggregates only).
Paid:  "full report"  -> 0.1 FET via the Payment Protocol, then the full report
       plus an AI-drafted doc fix for the worst process gap. The doc owner, a
       human, approves the fix before anything changes.
"""
import asyncio
import json
import uuid

from common import PUBLISH, create_agent  # noqa: F401
from uagents import Context, Protocol
from uagents_core.contrib.protocols.payment import (
    CommitPayment,
    CompletePayment,
    Funds,
    RejectPayment,
    RequestPayment,
    payment_protocol_spec,
)

from unblock import render
from unblock.actions import send_email
from unblock.chat import card_message, create_chat_protocol, parse_input, text_message
from unblock.config import env
from unblock.data import load_docs, load_people
from unblock.friction import build_map, fix_target, log_live_event
from unblock.llm import LLMError, get_llm
from unblock.models import FrictionEvent
from unblock.text import normalize

PRICE = env("INSIGHTS_PRICE_FET", "0.1")

agent = create_agent(
    "insights", "unblock-insights",
    "Friction Map for People Ops: groups repeated new-hire blockers into anonymous patterns (groups of 5+ only), "
    "finds the doc behind them, and drafts a fix for the doc owner to approve. Full report: 0.1 FET.",
    ["analytics", "people-ops", "payments"],
)
payment = Protocol(spec=payment_protocol_spec, role="seller")


@agent.on_message(FrictionEvent)
async def on_event(ctx: Context, sender: str, msg: FrictionEvent):
    if msg.doc_id:
        log_live_event(msg.doc_id, msg.docs_read, msg.resolved)


def _wallet() -> str:
    try:
        return str(agent.wallet.address())
    except Exception:
        return str(agent.address)


async def _request_payment(ctx: Context, sender: str) -> None:
    reference = "FR-" + uuid.uuid4().hex[:8].upper()
    ctx.storage.set(f"pay:{sender}", reference)
    testnet = env("FET_USE_TESTNET", "true").lower() == "true"
    await ctx.send(sender, RequestPayment(
        accepted_funds=[Funds(amount=PRICE, currency="FET", payment_method="fet_direct")],
        recipient=_wallet(), deadline_seconds=300, reference=reference,
        description="Unblock Friction Map full report with doc-fix proposal",
        metadata={"agent": "unblock-insights", "service": "friction_map_report",
                  "fet_network": "stable-testnet" if testnet else "mainnet", "mainnet": "false" if testnet else "true",
                  "provider_agent_wallet": _wallet(),
                  "content": f"Pay {PRICE} FET to get the full Friction Map report and a drafted fix for the biggest process gap."},
    ))


def _proposal() -> dict | None:
    fmap = build_map()
    docs = load_docs()
    for cluster in fmap["clusters"]:
        target = fix_target(cluster) if cluster["fixable"] else None
        if not target:
            continue
        doc, source = docs[target[0]], docs[target[1]]
        try:
            fix = get_llm().propose_fix(cluster, doc.body, doc.title, source.body)
        except LLMError as exc:
            return {"cluster": cluster, "error": f"The model is unavailable ({exc}), so no fix was drafted."}
        if normalize(str(fix.get("before_quote", ""))) not in normalize(doc.body):
            return {"cluster": cluster, "error": "The drafted fix didn't quote the doc exactly, so I blocked it."}
        return {"cluster": cluster, "doc_id": doc.id, "doc_title": doc.title, "owner_id": doc.owner,
                "before": fix["before_quote"], "after": fix["after_text"], "rationale": fix.get("rationale", "")}
    return None


async def _send_report(ctx: Context, sender: str):
    fmap = build_map()
    proposal = await asyncio.to_thread(_proposal)
    text = render.friction_text(fmap, full=True)
    if not proposal:
        return text_message(text + "\n\nNo cluster has a clear doc fix right now.")
    if "error" in proposal:
        return text_message(text + f"\n\n{proposal['error']}")
    ctx.storage.set(f"fix:{sender}", json.dumps(proposal))
    owner = load_people()[proposal["owner_id"]]
    text += (f"\n\n**Biggest fixable gap: {proposal['cluster']['topic']}.** {proposal['cluster']['pattern']}.\n"
             f"Proposed change to '{proposal['doc_title']}':\n- Before: {proposal['before']}\n- After: {proposal['after']}\n"
             f"Why: {proposal['rationale']}\n\nReply **approve** to send this to {owner['name']} (doc owner) for review, or **reject**.")
    return card_message(text, "review", {
        "title": f"Send a doc fix to {owner['name']}?",
        "summary_rows": [
            {"label": "Cluster", "value": f"{proposal['cluster']['topic']}: {proposal['cluster']['count']} blockers"},
            {"label": "Pattern", "value": proposal["cluster"]["pattern"]},
            {"label": "Before", "value": proposal["before"]}, {"label": "After", "value": proposal["after"]},
            {"label": "Privacy", "value": "Aggregates of 5+ only. No names or message text."}],
        "approve_cta": {"label": "Send to doc owner", "primary": True, "selection": {"action": "approve"}},
        "reject_cta": {"label": "Not now", "selection": {"action": "reject"}},
    })


@payment.on_message(CommitPayment)
async def on_commit(ctx: Context, sender: str, msg: CommitPayment):
    expected = ctx.storage.get(f"pay:{sender}")
    if not expected:
        ctx.logger.warning(f"payment from {sender} with no pending request")
        return
    ctx.storage.remove(f"pay:{sender}")
    await ctx.send(sender, CompletePayment(transaction_id=msg.transaction_id))
    await ctx.send(sender, await _send_report(ctx, sender))


@payment.on_message(RejectPayment)
async def on_reject(ctx: Context, sender: str, msg: RejectPayment):
    ctx.storage.remove(f"pay:{sender}")
    await ctx.send(sender, text_message("No problem, the payment was cancelled. The free Friction Map summary is still available."))


async def chat(ctx: Context, sender: str, text: str):
    sel = parse_input(text)
    action = str(sel.get("action", "")).lower() or text.strip().lower()
    if action in ("approve", "reject"):
        raw = ctx.storage.get(f"fix:{sender}")
        if not raw:
            return "There's no drafted fix waiting. Ask for the full report first."
        ctx.storage.remove(f"fix:{sender}")
        if action == "reject":
            return "Okay, I discarded the proposed fix. Nothing was sent."
        p = json.loads(raw)
        owner = load_people()[p["owner_id"]]
        body = (f"Hi {owner['name'].split()[0]},\n\nUnblock's Friction Map shows {p['cluster']['count']} new-hire blockers about "
                f"{p['cluster']['topic']} in the last 30 days. {p['cluster']['pattern']}.\n\nProposed change to '{p['doc_title']}':\n"
                f"Before: {p['before']}\nAfter: {p['after']}\n\nYou decide whether to publish it.\n\nPeople Ops, via Unblock")
        result = await asyncio.to_thread(send_email, owner["email"], f"Suggested fix for '{p['doc_title']}'", body, "people-ops@lumen.example")
        return f"**{result['status'].capitalize()}.** {result['detail']} {owner['name']} decides whether to publish it."
    if any(w in action for w in ("full report", "buy", "purchase", "pay")):
        await _request_payment(ctx, sender)
        return f"The full report with a drafted doc fix costs {PRICE} FET. I've sent a payment request in this chat."
    return render.friction_text(build_map()) + f"\n\nSay **full report** to get patterns and a drafted fix ({PRICE} FET)."


agent.include(create_chat_protocol("unblock-insights", chat), publish_manifest=PUBLISH)
agent.include(payment, publish_manifest=PUBLISH)

if __name__ == "__main__":
    agent.run()
