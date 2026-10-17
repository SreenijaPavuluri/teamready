"""Run the full demo locally, with no ASI:One: a test user and a test manager chat
with the real agents over uAgents messages and print every reply.

    UNBLOCK_LLM=extractive python scripts/local_demo.py   # no API key needed
    python scripts/local_demo.py                          # uses Sonnet

Steps: a verified answer, a stale-doc flag, a question the docs can't answer
(routed to a person, then "wrong person"), an access request approved by the
manager agent, and the high-impact stop.
"""
import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "agents"))
os.environ.setdefault("UNBLOCK_TODAY", "2026-10-17")
os.environ["AGENTVERSE_API_KEY"] = ""  # always local

from common import address  # noqa: E402
from uagents import Agent, Bureau, Context  # noqa: E402
from uagents_core.contrib.protocols.chat import ChatAcknowledgement, ChatMessage  # noqa: E402

from insights_agent import agent as insights  # noqa: E402
from knowledge_agent import agent as knowledge  # noqa: E402
from manager_agent import agent as manager  # noqa: E402
from orchestrator import agent as orchestrator  # noqa: E402
from routing_agent import agent as routing  # noqa: E402
from unblock.chat import message_text, text_message  # noqa: E402
from unblock.routing import reset_feedback  # noqa: E402

SCRIPT = [
    ("user", "How do I set up my dev environment?"),
    ("user", "How do I deploy to staging?"),
    ("user", "reject"),
    ("user", "How many vacation days do I get?"),
    ("user", "wrong person"),
    ("user", "approve"),
    ("user", "I need access to the analytics dashboard"),
    ("user", "approve"),
    ("manager", "pending"),
    ("manager", "approve"),
    ("user", "Can the AI decide whether I deserve a promotion?"),
]

user = Agent(name="demo-new-hire", seed="unblock local demo user")
boss = Agent(name="demo-manager", seed="unblock local demo manager")
queue: asyncio.Queue = asyncio.Queue()
done = asyncio.Event()


def show(who: str, text: str) -> None:
    print(f"\n{'=' * 78}\n{who}\n{'-' * 78}\n{text}")


for a, label in ((user, "UNBLOCK -> new hire"), (boss, "MANAGER AGENT -> manager")):
    @a.on_message(ChatMessage)
    async def got(ctx: Context, sender: str, msg: ChatMessage, label=label):
        await ctx.send(sender, ChatAcknowledgement(timestamp=msg.timestamp, acknowledged_msg_id=msg.msg_id))
        cards = [c for c in msg.content if getattr(c, "type", "") == "metadata"]
        show(label + (f"  [card: {cards[0].metadata.get('card_kind')}]" if cards else ""), message_text(msg))
        await queue.put(label)

    @a.on_message(ChatAcknowledgement)
    async def ack(ctx: Context, sender: str, msg: ChatAcknowledgement):
        pass


@user.on_event("startup")
async def run_script(ctx: Context):
    reset_feedback()
    await asyncio.sleep(2)
    for who, text in SCRIPT:
        show(f"{who.upper()} says", text)
        if who == "user":
            await ctx.send(address("orchestrator"), text_message(text))
        else:
            await boss_ctx.send(address("manager"), text_message(text))
        try:
            await asyncio.wait_for(queue.get(), timeout=120)
        except asyncio.TimeoutError:
            show("TIMEOUT", "no reply within 120s")
        if who == "manager" and text == "approve":
            await asyncio.wait_for(queue.get(), timeout=60)  # the new hire gets the decision
    done.set()
    print("\nDemo finished.")
    os._exit(0)


boss_ctx = None


@boss.on_event("startup")
async def keep(ctx: Context):
    global boss_ctx
    boss_ctx = ctx


bureau = Bureau(port=8010, endpoint=["http://127.0.0.1:8010/submit"])
for a in (orchestrator, knowledge, routing, manager, insights, user, boss):
    bureau.add(a)

if __name__ == "__main__":
    bureau.run()
