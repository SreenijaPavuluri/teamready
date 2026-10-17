import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ["UNBLOCK_TODAY"] = "2026-10-17"
os.environ["UNBLOCK_LLM"] = "extractive"
os.environ["SMTP_HOST"] = ""
os.environ["DEMO_RECIPIENT_OVERRIDE"] = ""

import pytest  # noqa: E402

from unblock import friction, routing  # noqa: E402


@pytest.fixture(autouse=True)
def isolated_runtime(tmp_path, monkeypatch):
    monkeypatch.setattr(routing, "FEEDBACK_PATH", tmp_path / "feedback.json")
    monkeypatch.setattr(friction, "LIVE_EVENTS_PATH", tmp_path / "live.json")
    import unblock.actions as actions
    monkeypatch.setattr(actions, "OUTBOX_DIR", tmp_path / "outbox")
    from unblock import activity, portal
    monkeypatch.setattr(activity, "PATH", tmp_path / "activity.jsonl")
    monkeypatch.setattr(portal, "PATH", tmp_path / "portal.json")
    yield
