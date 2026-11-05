from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from unittest.mock import patch
from sqlalchemy import select
from app.models import Booking, Worker
from app.services import worker_features
from app.ai_client import RecommendationResult, WorkerRecommendation, AIServiceError
from tests.helpers import account, booking, complete, service_request, transition, worker, enroll


def setup_job(api):
    customer, _ = account(api)
    wh, professional, _ = worker(api)
    job = booking(api, customer, service_request(api, customer), professional)
    return customer, wh, professional, job


def features(api, professional):
    with api.app.state.sessions() as db:
        return worker_features(db, [db.get(Worker, professional["id"])], None)[0]


def test_deadline_required_and_after_appointment(api):
    c, _ = account(api)
    _, w, _ = worker(api)
    r = service_request(api, c)
    payload = {
        "requestId": r["id"],
        "workerId": w["id"],
        "scheduledAt": r["preferredAt"],
        "scheduledEndAt": (
            datetime.fromisoformat(r["preferredAt"]) + timedelta(hours=1)
        ).isoformat(),
    }
    assert api.post("/api/v1/bookings", headers=c, json=payload).status_code == 422
    for deadline in (r["preferredAt"], "2020-01-01T00:00:00Z", "2040-01-01T00:00:00"):
        assert (
            api.post(
                "/api/v1/bookings", headers=c, json={**payload, "deadlineAt": deadline}
            ).status_code
            == 422
        )


def test_confirmation_dispute_ownership_and_duplicate_confirmation(api):
    c, w, professional, job = setup_job(api)
    stranger, _ = account(api)
    for state in ("accepted", "in_progress", "awaiting_confirmation"):
        assert transition(api, w, job["id"], state).status_code == 200
    assert features(api, professional)["completed_jobs_before"] == 0
    assert transition(api, w, job["id"], "completed").status_code == 409
    assert transition(api, stranger, job["id"], "completed").status_code == 404
    assert transition(api, c, job["id"], "in_progress").status_code == 422
    path = f"/api/v1/bookings/{job['id']}"
    response = api.patch(
        path + "/status", headers=c, json={"status": "in_progress", "note": "The tap still leaks."}
    )
    assert response.status_code == 200
    assert response.json()["data"]["reportedCompletedAt"] is None
    assert transition(api, c, job["id"], "completed").status_code == 409
    assert transition(api, w, job["id"], "awaiting_confirmation").status_code == 200
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda _: transition(api, c, job["id"], "completed"), range(2)))
    assert sorted(r.status_code for r in responses) == [200, 409]
    assert features(api, professional)["completed_jobs_before"] == 1
    assert features(api, professional)["late_rate_before"] == 0


def test_worker_cancellation_requires_reason_customer_does_not_penalize_worker(api):
    c, w, professional, job = setup_job(api)
    assert transition(api, c, job["id"], "cancelled").status_code == 200
    assert features(api, professional)["cancellation_rate_before"] is None
    job = booking(api, c, service_request(api, c), professional)
    assert transition(api, w, job["id"], "accepted").status_code == 200
    path = f"/api/v1/bookings/{job['id']}/status"
    assert api.patch(path, headers=w, json={"status": "cancelled"}).status_code == 422
    result = transition(api, w, job["id"], "cancelled")
    assert result.status_code == 200
    assert result.json()["data"]["cancelledByRole"] == "worker"
    assert features(api, professional)["cancellation_rate_before"] == 1


def test_complaint_access_review_and_verified_rate(api):
    c, w, professional, job = setup_job(api)
    complete(api, w, job["id"], c)
    stranger, _ = account(api)
    admin, _ = account(api, "admin")
    path = f"/api/v1/bookings/{job['id']}/complaint"
    data = {"reason": "The repaired pipe started leaking again."}
    assert api.post(path, headers=stranger, json=data).status_code == 404
    assert api.post(path, headers=w, json=data).status_code == 403
    response = api.post(path, headers=c, json=data)
    assert response.status_code == 201
    assert api.post(path, headers=c, json=data).status_code == 409
    assert features(api, professional)["complaint_rate_before"] is None
    review = f"/api/v1/admin/complaints/{response.json()['data']['id']}/resolution"
    decision = {
        "status": "upheld",
        "resolution": "Inspected the repair and confirmed faulty installation.",
    }
    assert api.patch(review, headers=c, json=decision).status_code == 403
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(
            pool.map(lambda _: api.patch(review, headers=admin, json=decision), range(2))
        )
    assert sorted(r.status_code for r in responses) == [200, 409]
    assert features(api, professional)["complaint_rate_before"] == 1
    assert (
        api.get(f"/api/v1/bookings/{job['id']}", headers=w).json()["data"]["complaint"][
            "resolution"
        ]
        == decision["resolution"]
    )


def test_prospective_snapshot_evaluation_and_late_outcome(api):
    c, customer_user = account(api)
    w, professional, _ = worker(api)
    admin, _ = account(api, "admin")
    enroll(api, admin, "customers", customer_user["id"])
    enroll(api, admin, "workers", professional["id"])
    api.app.state.settings.ai_enabled = True
    prediction = RecommendationResult(
        1,
        1,
        [WorkerRecommendation(professional["id"], "Test", 50, "Intermediate", 60, "Test", 0.8, 80)],
        "artifact-test-version",
    )
    with patch("app.services.recommend_workers", return_value=prediction):
        job = booking(api, c, service_request(api, c), professional)
    with api.app.state.sessions() as db:
        record = db.get(Booking, job["id"])
        snapshot = record.prediction.copy()
        # Advance the outcome clock past the agreed deadline without changing the snapshot.
        deadline = record.deadline_at
    for state in ("accepted", "in_progress"):
        assert transition(api, w, job["id"], state).status_code == 200
    with patch("app.models.utcnow", return_value=deadline + timedelta(hours=1)):
        assert transition(api, w, job["id"], "awaiting_confirmation").status_code == 200
        assert transition(api, c, job["id"], "completed").status_code == 200
    report = api.get("/api/v1/admin/model-evaluation", headers=admin).json()["data"]
    assert report["sampleCount"] == 1
    result = report["models"][0]
    assert result["onTimeRate"] == 0 and result["accuracyAtHalf"] == 0
    assert abs(result["brierScore"] - 0.64) < 0.000001
    assert sum(b["count"] for b in result["calibration"]) == 1
    with api.app.state.sessions() as db:
        assert db.get(Booking, job["id"]).prediction == snapshot
    assert features(api, professional)["late_rate_before"] == 1
    assert api.get("/api/v1/admin/model-evaluation", headers=c).status_code == 403
    with patch("app.services.recommend_workers", side_effect=AIServiceError("offline")):
        booking(api, c, service_request(api, c), professional)
    report = api.get("/api/v1/admin/model-evaluation", headers=admin).json()["data"]
    assert report["excluded"]["unconfirmed"] == 1
