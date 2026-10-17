"""Shared agent setup: seeds, addresses, Agentverse mailbox mode."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from uagents import Agent  # noqa: E402
from uagents.crypto import Identity  # noqa: E402

from unblock.config import env, env_bool  # noqa: E402

PUBLISH = bool(env("AGENTVERSE_API_KEY"))
READMES = Path(__file__).resolve().parent / "readmes"

# name -> (seed env var, default seed, local port)
AGENTS = {
    "orchestrator": ("ORCHESTRATOR_SEED", "unblock orchestrator demo seed CHANGE ME", 8100),
    "knowledge": ("KNOWLEDGE_SEED", "unblock knowledge demo seed CHANGE ME", 8101),
    "routing": ("ROUTING_SEED", "unblock routing demo seed CHANGE ME", 8102),
    "manager": ("MANAGER_SEED", "unblock manager demo seed CHANGE ME", 8103),
    "insights": ("INSIGHTS_SEED", "unblock insights demo seed CHANGE ME", 8104),
}


def seed(name: str) -> str:
    seed_env, default, _ = AGENTS[name]
    return env(seed_env, default)


def address(name: str) -> str:
    return Identity.from_seed(seed(name), 0).address


def create_agent(name: str, title: str, description: str, tags: list[str]) -> Agent:
    _, _, port = AGENTS[name]
    key = env("AGENTVERSE_API_KEY") or None
    mailbox = bool(key) and env_bool("UNBLOCK_MAILBOX", True)
    readme = READMES / f"{name}.md"
    return Agent(
        name=title,
        seed=seed(name),
        port=port,
        endpoint=None if mailbox else [f"http://127.0.0.1:{port}/submit"],
        agentverse=key,
        mailbox=mailbox,
        publish_agent_details=bool(key),
        description=description,
        readme_path=str(readme) if readme.exists() else None,
        metadata={"tags": ["unblock", "la-hacks-ai-2026", "workday", "onboarding", "innovationlab", *tags]},
    )
