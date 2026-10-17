"""Unblock web app: landing page with a live verified-answer demo, the live Friction
Map, and the voice tool endpoint for an ElevenLabs voice agent.

    uvicorn web.app:app --host 0.0.0.0 --port 8080

The web app is read-only: it answers and explains, but every action (messages,
access requests) happens in ASI:One, where the new hire approves it first.
"""
import asyncio
import sys
import time
from collections import defaultdict, deque
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "agents"))

from fastapi import FastAPI, Header, HTTPException, Request  # noqa: E402
from fastapi.responses import FileResponse, JSONResponse  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402

from unblock import creao, semantic, timeseries, workday  # noqa: E402
from unblock.config import env  # noqa: E402
from unblock.data import load_people, load_user  # noqa: E402
from unblock.friction import build_map  # noqa: E402
from unblock.knowledge import answer  # noqa: E402
from unblock.llm import get_llm_or_unavailable  # noqa: E402
from unblock.risk import assess  # noqa: E402
from unblock.routing import rank  # noqa: E402

app = FastAPI(title="Unblock", docs_url="/api/docs")
STATIC = Path(__file__).resolve().parent / "static"
RATE = int(env("WEB_RATE_PER_MIN", "20"))
_hits: dict[str, deque] = defaultdict(deque)


class Ask(BaseModel):
    question: str = Field(min_length=2, max_length=500)


def _limit(request: Request) -> None:
    ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "?").split(",")[0]
    q = _hits[ip]
    now = time.time()
    while q and now - q[0] > 60:
        q.popleft()
    if len(q) >= RATE:
        raise HTTPException(429, "Too many questions in a minute. Wait a moment and try again.")
    q.append(now)


def _speech(result: dict) -> str:
    """A short spoken version, built only from verified claims."""
    kind = result["kind"]
    if kind == "stop":
        return (f"That's something a person should handle, not an assistant. {result['reason']} "
                f"Please talk to {result['helper']['name']}, {result['helper']['role']}.")
    if kind == "route":
        helper = result.get("helper")
        who = f"{helper['name']}, {helper['role']}" if helper else "People Ops"
        return f"I couldn't find a reliable answer in the approved docs, so I won't guess. The best person to ask is {who}."
    facts = [c["text"].rstrip(".") for c in result["claims"] + result["steps"]][:4]
    source = result["citations"][0]["title"] if result["citations"] else "the approved docs"
    text = "Here's what the docs say. " + ". ".join(facts) + f". That's from {source}."
    if kind == "approval":
        text += f" {result['reason']} You can ask Unblock in ASI:One to prepare the request."
    return text


def run_ask(question: str) -> dict:
    user = load_user()
    people = load_people()
    risk = assess(question)
    if risk.level == "stop":
        human = people[risk.human_id]
        result = {"kind": "stop", "title": "This needs a person", "reason": risk.reason, "category": risk.category,
                  "helper": {"name": human["name"], "role": human["role"]}, "claims": [], "steps": [], "blocked": [],
                  "conflicts": [], "citations": [], "trace": ["Stopped before searching or drafting"], "confidence": None}
    else:
        a = answer(question, user, get_llm_or_unavailable()).to_dict()
        kind = "approval" if risk.level == "approval" else a["decision"]
        helper = None
        if kind == "route":
            r = rank(question, user, a["retrieved_doc_ids"] or None)
            if r.chosen:
                helper = {"name": r.chosen.name, "role": r.chosen.role, "reasons": r.chosen.reasons}
        result = {"kind": kind, "title": a["title"], "reason": risk.reason if kind == "approval" else a["route_reason"],
                  "claims": a["claims"], "steps": a["steps"], "blocked": a["blocked"], "conflicts": a["conflicts"],
                  "citations": a["citations"], "trace": a["trace"], "confidence": a["confidence"], "helper": helper,
                  "llm": a["llm_mode"], "error": a["error"]}
    result["speech"] = _speech(result)
    return result


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.post("/api/ask")
async def api_ask(body: Ask, request: Request):
    _limit(request)
    return await asyncio.to_thread(run_ask, body.question)


@app.post("/api/voice/ask")
async def voice_ask(body: Ask, request: Request, x_unblock_secret: str = Header(default="")):
    """Webhook tool for an ElevenLabs voice agent. Returns `answer` to be spoken."""
    secret = env("VOICE_TOOL_SECRET")
    if secret and x_unblock_secret != secret:
        raise HTTPException(401, "Missing or wrong X-Unblock-Secret header.")
    _limit(request)
    result = await asyncio.to_thread(run_ask, body.question)
    return {"answer": result["speech"], "kind": result["kind"],
            "sources": [c["title"] for c in result["citations"]], "blocked_claims": len(result["blocked"])}


@app.get("/api/friction")
def api_friction():
    return build_map()


@app.get("/api/agents")
def api_agents():
    from common import AGENTS, address

    return [{"name": f"unblock-{n}", "address": address(n)} for n in AGENTS]


@app.get("/api/health")
def health():
    llm = get_llm_or_unavailable()
    return JSONResponse({"ok": True, "llm": llm.mode, "model": getattr(llm, "model", ""),
                         "retrieval": "hybrid (Gemini)" if semantic.enabled() else "keyword (BM25)",
                         "friction_store": "Tiger Data" if timeseries.enabled() else "JSON files",
                         "new_hire_profile": (load_user(), workday.status())[1],
                         "doc_fixes": creao.status()})
