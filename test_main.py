from datetime import date

from fastapi.testclient import TestClient

from main import app, get_today

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


def test_streak_counts_consecutive_days_up_to_today():
    app.dependency_overrides[get_today] = lambda: date(2026, 9, 22)
    hid = client.post("/habits", json={"name": "Walk"}).json()["id"]
    for day in ["2026-09-20", "2026-09-21", "2026-09-22"]:
        client.post(f"/habits/{hid}/checkin", json={"day": day})
    r = client.get(f"/habits/{hid}/streak")
    assert r.json() == {"habit_id": hid, "streak": 3}


def test_streak_is_zero_without_checkin_today():
    app.dependency_overrides[get_today] = lambda: date(2026, 9, 22)
    hid = client.post("/habits", json={"name": "Journal"}).json()["id"]
    client.post(f"/habits/{hid}/checkin", json={"day": "2026-09-21"})
    assert client.get(f"/habits/{hid}/streak").json()["streak"] == 0
