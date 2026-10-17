"""The verifier: plain code that decides which AI claims a new hire may see.

A claim passes only if:
1. it cites a doc that was actually retrieved for this question,
2. its supporting quote appears word for word in that doc (after normalizing
   case, quotes, dashes and spaces),
3. the quote is long enough to mean something (at least 4 words), and
4. every number in the claim also appears in the quote, so "100 USD" can't be
   backed by a quote that says "75 USD".
Anything else is blocked and never shown as fact.
"""
from dataclasses import dataclass

from .data import Doc
from .text import normalize, numbers

MIN_QUOTE_WORDS = 4


@dataclass
class Claim:
    text: str
    quote: str
    source_id: str


@dataclass
class Verdict:
    claim: Claim
    passed: bool
    reason: str


def verify_claim(claim: Claim, allowed_docs: dict[str, Doc]) -> Verdict:
    doc = allowed_docs.get(claim.source_id)
    if doc is None:
        return Verdict(claim, False, f"cites {claim.source_id or 'no source'}, which was not retrieved")
    quote = normalize(claim.quote)
    if len(quote.split()) < MIN_QUOTE_WORDS:
        return Verdict(claim, False, "supporting quote is too short to verify")
    if quote not in normalize(doc.body):
        return Verdict(claim, False, f"quote not found word for word in {doc.id}")
    missing = numbers(claim.text) - numbers(claim.quote)
    if missing:
        return Verdict(claim, False, f"number {', '.join(sorted(missing))} is not in the quoted source")
    return Verdict(claim, True, f"verified in {doc.id}")


def verify_all(claims: list[Claim], allowed_docs: dict[str, Doc]) -> list[Verdict]:
    return [verify_claim(c, allowed_docs) for c in claims]
