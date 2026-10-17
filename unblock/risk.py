"""Risk gate. Runs in code before any model call or search.

stop      -> high-impact topic (pay, performance, benefits eligibility, employment,
             harassment). No search, no draft. Route to a named human channel.
approval  -> elevated or gated access. Unblock may prepare a request, but only the
             manager agent (a human) can approve it.
routine   -> normal onboarding question.
"""
import re
from dataclasses import dataclass

from .data import load_policies


@dataclass
class Risk:
    level: str  # "stop" | "approval" | "routine"
    category: str = "routine onboarding"
    reason: str = "No high-impact workplace category was detected."
    human_id: str = ""
    channel: str = ""
    approver: str = ""
    matched_term: str = ""


def _matches(text: str, term: str) -> bool:
    """Whole words or phrases by default; a trailing * marks a prefix (harass* matches harassment)."""
    term = term.lower().strip()
    if term.endswith("*"):
        return re.search(rf"(?<![a-z0-9]){re.escape(term[:-1])}", text) is not None
    return re.search(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", text) is not None


def assess(query: str) -> Risk:
    text = " " + re.sub(r"\s+", " ", query.lower()) + " "
    policies = load_policies()
    for rule in policies["stop_categories"]:
        for term in rule["terms"]:
            if _matches(text, term):
                return Risk(
                    level="stop",
                    category=rule["category"],
                    reason=rule["reason"],
                    human_id=rule["human_id"],
                    channel=rule["channel"],
                    matched_term=term.strip(),
                )
    for rule in policies["approval_categories"]:
        for term in rule["terms"]:
            if _matches(text, term):
                return Risk(
                    level="approval",
                    category=rule["category"],
                    reason=rule["reason"],
                    approver=rule["approver"],
                    matched_term=term.strip(),
                )
    return Risk(level="routine")
