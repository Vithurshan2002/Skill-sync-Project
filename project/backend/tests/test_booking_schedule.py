"""Appointment overlap, lifecycle, timezone and concurrent booking protection."""

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta, timezone
from threading import Barrier

import pytest
from sqlalchemy import func, select

from app.models import Booking
from tests.helpers import account, complete, service_request, transition, worker


def payload(request, professional, start, end):
    return {
        "requestId": request["id"],
        "workerId": professional["id"],
        "scheduledAt": start.isoformat(),
        "scheduledEndAt": end.isoformat(),
        "deadlineAt": (end + timedelta(hours=4)).isoformat(),
    }


def setup(api):
    customer, _ = account(api)
    worker_headers, professional, _ = worker(api)
    start = (datetime.now(UTC) + timedelta(days=3)).replace(
        hour=4, minute=30, second=0, microsecond=0
    )
    first_request = service_request(api, customer)
    first = api.post(
        "/api/v1/bookings",
        headers=customer,
        json=payload(first_request, professional, start, start + timedelta(hours=2)),
    )
    assert first.status_code == 201, first.text
    return customer, worker_headers, professional, start, first.json()["data"]


@pytest.mark.parametrize("start_hours,end_hours", [(0, 2), (1, 3), (-1, 1), (-1, 3), (0.5, 1)])
def test_overlapping_windows_are_rejected_and_request_stays_unbooked(api, start_hours, end_hours):
    customer, _, professional, start, _ = setup(api)
    job = service_request(api, customer)
    response = api.post(
        "/api/v1/bookings",
        headers=customer,
        json=payload(
            job,
            professional,
            start + timedelta(hours=start_hours),
            start + timedelta(hours=end_hours),
        ),
    )
    assert response.status_code == 409, response.text
    assert response.json()["error"]["code"] == "booking_time_conflict"
    assert "scheduledAt" in response.json()["error"]["fields"]
    assert (
        api.get("/api/v1/requests/" + job["id"], headers=customer).json()["data"]["status"]
        == "submitted"
    )


def test_adjacent_bookings_same_day_and_other_workers_are_allowed(api):
    customer, _, professional, start, _ = setup(api)
    # First job's deadline extends past its reserved end, and must not block this slot.
    job = service_request(api, customer)
    result = api.post(
        "/api/v1/bookings",
        headers=customer,
        json=payload(job, professional, start + timedelta(hours=2), start + timedelta(hours=3)),
    )
    assert result.status_code == 201, result.text
    _, other, _ = worker(api)
    result = api.post(
        "/api/v1/bookings",
        headers=customer,
        json=payload(service_request(api, customer), other, start, start + timedelta(hours=2)),
    )
    assert result.status_code == 201, result.text


def test_timezone_offsets_cannot_bypass_overlap(api):
    customer, _, professional, start, _ = setup(api)
    data = payload(service_request(api, customer), professional, start, start + timedelta(hours=2))
    data["scheduledAt"] = start.astimezone(timezone(timedelta(hours=5, minutes=30))).isoformat()
    assert api.post("/api/v1/bookings", headers=customer, json=data).status_code == 409


@pytest.mark.parametrize("status", ["cancelled", "rejected", "completed"])
def test_released_bookings_do_not_block_new_requests(api, status):
    customer, wh, professional, start, first = setup(api)
    if status == "completed":
        complete(api, wh, first["id"], customer)
    else:
        actor = customer if status == "cancelled" else wh
        assert transition(api, actor, first["id"], status).status_code == 200
    result = api.post(
        "/api/v1/bookings",
        headers=customer,
        json=payload(
            service_request(api, customer), professional, start, start + timedelta(hours=2)
        ),
    )
    assert result.status_code == 201, result.text


@pytest.mark.parametrize("status", ["accepted", "in_progress", "awaiting_confirmation"])
def test_active_booking_statuses_still_reserve_time(api, status):
    customer, wh, professional, start, first = setup(api)
    for next_status in ["accepted", "in_progress", "awaiting_confirmation"]:
        assert transition(api, wh, first["id"], next_status).status_code == 200
        if next_status == status:
            break
    assert (
        api.post(
            "/api/v1/bookings",
            headers=customer,
            json=payload(
                service_request(api, customer), professional, start, start + timedelta(hours=2)
            ),
        ).status_code
        == 409
    )


def test_simultaneous_different_requests_cannot_double_book_worker(api):
    customer, _ = account(api)
    wh, professional, _ = worker(api)
    start = datetime.now(UTC) + timedelta(days=3)
    requests = [service_request(api, customer), service_request(api, customer)]
    barrier = Barrier(2)

    def submit(job):
        barrier.wait(timeout=10)
        return api.post(
            "/api/v1/bookings",
            headers=customer,
            json=payload(job, professional, start, start + timedelta(hours=2)),
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(submit, requests))
    assert sorted(r.status_code for r in results) == [201, 409]
    with api.app.state.sessions() as db:
        assert db.scalar(select(func.count()).select_from(Booking)) == 1
    notices = api.get("/api/v1/notifications", headers=wh).json()["data"]
    assert sum(n["message"].startswith("New booking:") for n in notices) == 1


@pytest.mark.parametrize("end", [None, "before", "equal", "after_deadline", "naive"])
def test_invalid_or_missing_end_time_is_rejected(api, end):
    customer, _ = account(api)
    _, professional, _ = worker(api)
    start = datetime.now(UTC) + timedelta(days=3)
    data = payload(service_request(api, customer), professional, start, start + timedelta(hours=2))
    if end is None:
        del data["scheduledEndAt"]
    elif end == "naive":
        data["scheduledEndAt"] = (start + timedelta(hours=2)).replace(tzinfo=None).isoformat()
    else:
        data["scheduledEndAt"] = (
            start + timedelta(hours={"before": -1, "equal": 0, "after_deadline": 7}[end])
        ).isoformat()
    assert api.post("/api/v1/bookings", headers=customer, json=data).status_code == 422


@pytest.mark.parametrize("has_deadline", [True, False])
def test_legacy_bookings_reserve_until_deadline_or_unknown_end(api, has_deadline):
    customer, _, professional, start, first = setup(api)
    with api.app.state.sessions() as db:
        old = db.get(Booking, first["id"])
        old.scheduled_end_at = None
        if not has_deadline:
            old.deadline_at = None
        db.commit()
    result = api.post(
        "/api/v1/bookings",
        headers=customer,
        json=payload(
            service_request(api, customer),
            professional,
            start + timedelta(hours=3),
            start + timedelta(hours=4),
        ),
    )
    assert result.status_code == 409


def test_worker_cannot_accept_legacy_overlapping_pending_jobs(api):
    customer, wh, professional, start, first = setup(api)
    second = api.post(
        "/api/v1/bookings",
        headers=customer,
        json=payload(
            service_request(api, customer),
            professional,
            start + timedelta(hours=3),
            start + timedelta(hours=4),
        ),
    ).json()["data"]
    with api.app.state.sessions() as db:
        old = db.get(Booking, first["id"])
        old.scheduled_end_at = None  # Original deadline overlaps the second booking.
        db.commit()
    result = transition(api, wh, second["id"], "accepted")
    assert result.status_code == 409
    assert "note" in result.json()["error"]["fields"]
    assert transition(api, customer, first["id"], "cancelled").status_code == 200
    assert transition(api, wh, second["id"], "accepted").status_code == 200
