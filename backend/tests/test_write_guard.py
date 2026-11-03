"""The write guard must fail closed: no key or wrong key -> 403, reads open."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app, raise_server_exceptions=False)


def test_post_without_key_denied():
    resp = client.post("/api/feedback", json={})
    assert resp.status_code == 403


def test_post_with_wrong_key_denied():
    resp = client.post("/api/feedback", json={}, headers={"x-api-key": "wrong"})
    assert resp.status_code == 403


def test_put_and_delete_also_guarded():
    assert client.put("/api/events/whatever").status_code == 403
    assert client.delete("/api/events/whatever").status_code == 403


def test_get_is_not_guarded():
    # History is a plain read; it must reach the route (200 with a DB,
    # but never a 403 from the guard).
    resp = client.get("/api/digest/history")
    assert resp.status_code != 403
