import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_create_and_list_habit():
    r = client.post("/habits", json={"name": "Read 20 minutes"})
    assert r.status_code == 200
    hid = r.json()["id"]
    r2 = client.get("/habits")
    assert r2.status_code == 200
    assert any(h["id"] == hid for h in r2.json())


def test_checkin_flow():
    hid = client.post("/habits", json={"name": "Stretch"}).json()["id"]
    r = client.post(f"/habits/{hid}/checkin", json={"day": "2026-09-22"})
    assert r.status_code == 200
    r2 = client.get(f"/habits/{hid}/checkins")
    assert r2.json() == ["2026-09-22"]


def test_checkin_unknown_habit_404():
    r = client.post("/habits/99999/checkin", json={"day": "2026-09-22"})
    assert r.status_code == 404


def error_message(response):
    return response.json()["detail"][0]["msg"]


@pytest.mark.parametrize("name", ["", "   ", "\t\n"])
def test_create_habit_rejects_blank_name(name):
    r = client.post("/habits", json={"name": name})
    assert r.status_code == 422
    assert error_message(r) == "Value error, name must not be empty"


def test_create_habit_rejects_missing_name():
    assert client.post("/habits", json={}).status_code == 422


def test_create_habit_trims_name():
    r = client.post("/habits", json={"name": "  Meditate  "})
    assert r.json()["name"] == "Meditate"
    assert {"id": r.json()["id"], "name": "Meditate"} in client.get("/habits").json()


@pytest.mark.parametrize(
    "day",
    ["22/09/2026", "2026-9-22", "2026-02-30", "20260922", "2026-W39-2", " 2026-09-22", "", "today"],
)
def test_checkin_rejects_malformed_day(day):
    hid = client.post("/habits", json={"name": "Stretch"}).json()["id"]
    r = client.post(f"/habits/{hid}/checkin", json={"day": day})
    assert r.status_code == 422
    assert "YYYY-MM-DD" in error_message(r)
    assert client.get(f"/habits/{hid}/checkins").json() == []


def test_checkin_accepts_leap_day():
    hid = client.post("/habits", json={"name": "Stretch"}).json()["id"]
    assert client.post(f"/habits/{hid}/checkin", json={"day": "2028-02-29"}).status_code == 200
