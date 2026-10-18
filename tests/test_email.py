from unblock import actions


def test_unreachable_mail_server_saves_to_outbox_instead_of_hanging(monkeypatch):
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    actions._reach.clear()
    monkeypatch.setattr(actions, "_reachable", lambda host, port: False)
    r = actions.send_email("someone@lumen.example", "Hi", "Body", "maya.chen@lumen.example")
    assert r["status"] == "simulated" and "isn't reachable from this network" in r["detail"]


def test_no_smtp_host_is_simulated():
    r = actions.send_email("someone@lumen.example", "Hi", "Body", "maya.chen@lumen.example")
    assert r["status"] == "simulated" and "not configured" in r["detail"]
