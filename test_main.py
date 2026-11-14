from datetime import date

import pytest
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


@pytest.fixture
def today_is_sept_22():
    app.dependency_overrides[get_today] = lambda: date(2026, 9, 22)
    yield
    app.dependency_overrides.clear()


def habit_with_checkins(*days):
    hid = client.post("/habits", json={"name": "Walk"}).json()["id"]
    for day in days:
        client.post(f"/habits/{hid}/checkin", json={"day": day})
    return hid


def streak(hid):
    return client.get(f"/habits/{hid}/streak").json()["streak"]


def test_streak_counts_consecutive_days_up_to_today(today_is_sept_22):
    hid = habit_with_checkins("2026-09-20", "2026-09-21", "2026-09-22")
    r = client.get(f"/habits/{hid}/streak")
    assert r.status_code == 200
    assert r.json() == {"habit_id": hid, "streak": 3}


def test_streak_is_zero_without_checkin_today(today_is_sept_22):
    assert streak(habit_with_checkins("2026-09-21")) == 0


def test_streak_is_zero_with_no_checkins(today_is_sept_22):
    assert streak(habit_with_checkins()) == 0


def test_streak_stops_at_a_missed_day(today_is_sept_22):
    assert streak(habit_with_checkins("2026-09-18", "2026-09-19", "2026-09-21", "2026-09-22")) == 2


def test_streak_counts_duplicate_checkins_once(today_is_sept_22):
    assert streak(habit_with_checkins("2026-09-22", "2026-09-22", "2026-09-21")) == 2


def test_streak_ignores_future_checkins(today_is_sept_22):
    assert streak(habit_with_checkins("2026-09-22", "2026-09-23")) == 1


def test_streak_crosses_month_boundary():
    app.dependency_overrides[get_today] = lambda: date(2026, 3, 1)
    try:
        assert streak(habit_with_checkins("2026-02-27", "2026-02-28", "2026-03-01")) == 3
    finally:
        app.dependency_overrides.clear()


def test_streak_skips_malformed_stored_days(today_is_sept_22):
    assert streak(habit_with_checkins("not-a-date", "2026-09-22")) == 1


def test_streak_unknown_habit_404():
    r = client.get("/habits/99999/streak")
    assert r.status_code == 404
    assert r.json() == {"detail": "unknown habit"}
