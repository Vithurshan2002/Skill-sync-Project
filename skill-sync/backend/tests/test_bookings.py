from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta

import pytest
from sqlalchemy import func, select

from app.models import Booking, BookingEvent, Review
from tests.helpers import account, booking, complete, service_request, transition, worker


def test_booking_lifecycle_review_notifications_and_counts_persist(api):
    customer, _ = account(api)
    worker_headers, professional, _ = worker(api)
    request = service_request(api, customer)
    record = booking(api, customer, request, professional)
    path = f"/api/v1/bookings/{record['id']}"
    assert record["status"] == "pending"
    assert record["quotedRateLkr"] == 2500
    assert (
        api.patch(
            "/api/v1/worker/profile", headers=worker_headers, json={"rateLkr": 4000}
        ).status_code
        == 200
    )
    assert api.get(path, headers=customer).json()["data"]["quotedRateLkr"] == 2500
    assert (
        api.patch(
            f"/api/v1/requests/{request['id']}", headers=customer, json={"category": "Electrical"}
        ).status_code
        == 409
    )
    assert (
        api.post(
            path + "/review",
            headers=customer,
            json={"rating": 5, "comment": "Excellent repair work."},
        ).status_code
        == 409
    )
    assert transition(api, customer, record["id"], "accepted").status_code == 409
    assert transition(api, worker_headers, record["id"], "completed").status_code == 409

    complete(api, worker_headers, record["id"], customer)
    saved = api.get(path, headers=customer).json()["data"]
    assert [event["status"] for event in saved["history"]] == [
        "pending",
        "accepted",
        "in_progress",
        "awaiting_confirmation",
        "completed",
    ]
    assert saved["request"]["status"] == "closed"
    assert transition(api, customer, record["id"], "cancelled").status_code == 409
    assert transition(api, worker_headers, record["id"], "accepted").status_code == 409
    assert (
        api.post(
            path + "/review",
            headers=customer,
            json={"rating": 5, "comment": "Excellent repair work."},
        ).status_code
        == 201
    )
    assert (
        api.post(
            path + "/review",
            headers=customer,
            json={"rating": 2, "comment": "Second review attempt."},
        ).status_code
        == 409
    )
    assert api.get(path, headers=customer).json()["data"]["review"]["rating"] == 5
    performance = api.get("/api/v1/worker/performance", headers=worker_headers).json()["data"]
    assert performance["completedJobs"] == 1
    assert performance["rating"] == 5
    assert performance["reviewCount"] == 1
    assert performance["reliabilityProbability"] is None
    assert performance["performance"][0]["skillScore"] is None
    assert api.get("/api/v1/dashboard", headers=customer).json()["data"]["bookingsByStatus"] == {
        "completed": 1
    }
    notices = api.get("/api/v1/notifications", headers=worker_headers).json()["data"]
    assert len(notices) == 3
    notice_id = notices[0]["id"]
    assert (
        api.patch(f"/api/v1/notifications/{notice_id}", headers=customer, json={}).status_code
        == 404
    )
    response = api.patch(
        f"/api/v1/notifications/{notice_id}", headers=worker_headers, json={"read": True}
    )
    assert response.status_code == 200
    read_at = response.json()["data"]["readAt"]
    assert read_at is not None
    assert (
        api.patch(f"/api/v1/notifications/{notice_id}", headers=worker_headers, json={}).json()[
            "data"
        ]["readAt"]
        == read_at
    )
    public = api.get(f"/api/v1/workers/{professional['id']}").json()["data"]
    assert public["reviews"][0]["comment"] == "Excellent repair work."
    assert "customerId" not in public["reviews"][0]
    assert public["reviews"][0]["customerName"] == "Anu"
    assert set(public["reviews"][0]) == {"customerName", "rating", "comment", "createdAt"}


@pytest.mark.parametrize("terminal", ["cancelled", "rejected"])
def test_cancelled_or_rejected_request_can_be_booked_again(api, terminal):
    customer, _ = account(api)
    worker_headers, professional, _ = worker(api)
    request = service_request(api, customer)
    first = booking(api, customer, request, professional)
    actor = customer if terminal == "cancelled" else worker_headers
    assert transition(api, actor, first["id"], terminal).status_code == 200
    second = booking(api, customer, request, professional)
    assert second["id"] != first["id"]
    assert second["status"] == "pending"
    assert transition(api, worker_headers, first["id"], "accepted").status_code == 409
    assert (
        api.post(
            f"/api/v1/bookings/{first['id']}/review",
            headers=customer,
            json={"rating": 5, "comment": "Cannot review this job."},
        ).status_code
        == 409
    )


def test_customer_can_cancel_accepted_or_in_progress_work(api):
    customer, _ = account(api)
    worker_headers, professional, _ = worker(api)
    request = service_request(api, customer)
    first = booking(api, customer, request, professional)
    assert transition(api, worker_headers, first["id"], "accepted").status_code == 200
    assert transition(api, customer, first["id"], "cancelled").status_code == 200
    second = booking(api, customer, request, professional)
    assert transition(api, worker_headers, second["id"], "accepted").status_code == 200
    assert transition(api, worker_headers, second["id"], "in_progress").status_code == 200
    assert transition(api, customer, second["id"], "cancelled").status_code == 200


def test_wrong_customer_worker_and_admin_cannot_mutate_booking(api):
    customer, _ = account(api)
    stranger, _ = account(api)
    worker_headers, professional, _ = worker(api)
    other_worker, _, _ = worker(api, name="Other Worker")
    admin, _ = account(api, "admin")
    request = service_request(api, customer)
    record = booking(api, customer, request, professional)
    path = f"/api/v1/bookings/{record['id']}"
    for headers in [stranger, other_worker]:
        assert api.get(path, headers=headers).status_code == 404
        assert transition(api, headers, record["id"], "accepted").status_code == 404
        assert api.get("/api/v1/bookings", headers=headers).json()["meta"]["total"] == 0
    assert (
        api.post(
            path + "/review",
            headers=stranger,
            json={"rating": 5, "comment": "Unauthorized review."},
        ).status_code
        == 404
    )
    assert transition(api, admin, record["id"], "accepted").status_code == 403
    assert api.get(path, headers=admin).status_code == 200
    assert api.get(f"/api/v1/requests/{request['id']}", headers=other_worker).status_code == 403
    assert api.get(path, headers=customer).json()["data"]["history"][0]["status"] == "pending"


@pytest.mark.parametrize(
    "profile",
    [
        {"categories": ["Electrical"]},
        {"serviceTowns": ["Galle"]},
        {"available": False},
    ],
)
def test_booking_rechecks_worker_eligibility(api, profile):
    customer, _ = account(api)
    worker_headers, professional, _ = worker(api)
    request = service_request(api, customer)
    assert (
        api.patch("/api/v1/worker/profile", headers=worker_headers, json=profile).status_code == 200
    )
    # Review material edits so this test still exercises category/town matching,
    # independently of the approval barrier covered in test_worker_approval.py.
    if "available" not in profile:
        admin, _ = account(api, "admin")
        assert (
            api.patch(
                f"/api/v1/admin/workers/{professional['id']}/verification",
                headers=admin,
                json={"verified": True, "note": "Changed service details reviewed."},
            ).status_code
            == 200
        )
    response = api.post(
        "/api/v1/bookings",
        headers=customer,
        json={
            "requestId": request["id"],
            "workerId": professional["id"],
            "scheduledAt": request["preferredAt"],
            "scheduledEndAt": (
                datetime.fromisoformat(request["preferredAt"]) + timedelta(hours=4)
            ).isoformat(),
            "deadlineAt": (
                datetime.fromisoformat(request["preferredAt"]) + timedelta(hours=4)
            ).isoformat(),
        },
    )
    assert response.status_code == 422
    assert (
        api.get(f"/api/v1/requests/{request['id']}", headers=customer).json()["data"]["status"]
        == "submitted"
    )
    notices = api.get("/api/v1/notifications", headers=worker_headers).json()["data"]
    assert not any("New booking" in notice["message"] for notice in notices)


def test_concurrent_booking_submission_creates_only_one_booking_and_notification(api):
    customer, _ = account(api)
    worker_headers, professional, _ = worker(api)
    request = service_request(api, customer)
    payload = {
        "requestId": request["id"],
        "workerId": professional["id"],
        "scheduledAt": request["preferredAt"],
        "scheduledEndAt": (
            datetime.fromisoformat(request["preferredAt"]) + timedelta(hours=4)
        ).isoformat(),
        "deadlineAt": (
            datetime.fromisoformat(request["preferredAt"]) + timedelta(hours=4)
        ).isoformat(),
    }
    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(
            executor.map(
                lambda _: api.post("/api/v1/bookings", headers=customer, json=payload), range(2)
            )
        )
    assert sorted(response.status_code for response in responses) == [201, 409]
    with api.app.state.sessions() as db:
        assert db.scalar(select(func.count()).select_from(Booking)) == 1
        assert db.scalar(select(func.count()).select_from(BookingEvent)) == 1
    assert api.get("/api/v1/notifications", headers=worker_headers).json()["meta"]["total"] == 1


def test_concurrent_reviews_only_increment_rating_once(api):
    customer, _ = account(api)
    worker_headers, professional, _ = worker(api)
    request = service_request(api, customer)
    record = booking(api, customer, request, professional)
    complete(api, worker_headers, record["id"], customer)
    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(
            executor.map(
                lambda _: api.post(
                    f"/api/v1/bookings/{record['id']}/review",
                    headers=customer,
                    json={"rating": 4, "comment": "Careful repair and communication."},
                ),
                range(2),
            )
        )
    assert sorted(response.status_code for response in responses) == [201, 409]
    with api.app.state.sessions() as db:
        assert db.scalar(select(func.count()).select_from(Review)) == 1
    public = api.get(f"/api/v1/workers/{professional['id']}").json()["data"]
    assert public["reviewCount"] == 1
    assert public["rating"] == 4


def test_concurrent_different_jobs_increment_the_same_category_total(api):
    customer, _ = account(api)
    worker_headers, professional, _ = worker(api)
    initial = booking(api, customer, service_request(api, customer), professional)
    complete(api, worker_headers, initial["id"], customer)
    jobs = []
    for offset in range(2):
        appointment = datetime.now().astimezone() + timedelta(days=3, hours=offset * 5)
        record = booking(
            api,
            customer,
            service_request(api, customer, preferredAt=appointment.isoformat()),
            professional,
        )
        assert transition(api, worker_headers, record["id"], "accepted").status_code == 200
        assert transition(api, worker_headers, record["id"], "in_progress").status_code == 200
        assert (
            transition(api, worker_headers, record["id"], "awaiting_confirmation").status_code
            == 200
        )
        jobs.append(record["id"])
    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(
            executor.map(lambda job_id: transition(api, customer, job_id, "completed"), jobs)
        )
    assert [response.status_code for response in responses] == [200, 200]
    result = api.get("/api/v1/worker/performance", headers=worker_headers).json()["data"]
    assert result["completedJobs"] == 3
    assert result["performance"][0]["completedJobs"] == 3
