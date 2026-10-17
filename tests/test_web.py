from fastapi.testclient import TestClient

import web.app as webapp

client = TestClient(webapp.app)


def test_landing_page_and_health():
    assert "Stuck in your first weeks" in client.get("/").text
    assert client.get("/api/health").json()["ok"] is True


def test_ask_returns_only_verified_claims():
    r = client.post("/api/ask", json={"question": "How do I deploy to staging?"}).json()
    assert r["kind"] == "answer" and all(c["source_id"] == "D13" for c in r["claims"])
    assert any(c["type"] == "stale doc" for c in r["conflicts"])


def test_ask_stops_high_impact_questions():
    r = client.post("/api/ask", json={"question": "Will I get a bonus this year?"}).json()
    assert r["kind"] == "stop" and not r["claims"] and "person" in r["speech"]


def test_voice_tool_speaks_and_checks_secret(monkeypatch):
    r = client.post("/api/voice/ask", json={"question": "How do I reset my password?"}).json()
    assert r["kind"] == "answer" and r["answer"].startswith("Here's what the docs say") and r["sources"]
    monkeypatch.setenv("VOICE_TOOL_SECRET", "s3cret")
    assert client.post("/api/voice/ask", json={"question": "hi there"}).status_code == 401
    ok = client.post("/api/voice/ask", json={"question": "How do I reset my password?"}, headers={"X-Unblock-Secret": "s3cret"})
    assert ok.status_code == 200


def test_voice_never_guesses():
    r = client.post("/api/voice/ask", json={"question": "Is there free lunch on Fridays?"}).json()
    assert r["kind"] == "route" and "won't guess" in r["answer"]


def test_friction_and_agents_endpoints():
    m = client.get("/api/friction").json()
    assert m["clusters"] and m["storage"] == "JSON files"
    assert len(client.get("/api/agents").json()) == 6


def test_rate_limit(monkeypatch):
    monkeypatch.setattr(webapp, "RATE", 2)
    webapp._hits.clear()
    codes = [client.post("/api/ask", json={"question": "How do I reset my password?"}).status_code for _ in range(3)]
    assert codes == [200, 200, 429]
    webapp._hits.clear()
