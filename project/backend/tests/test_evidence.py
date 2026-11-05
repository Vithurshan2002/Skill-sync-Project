from copy import deepcopy
from sqlalchemy import select
from app import evidence
from app.models import Booking, User, Worker, WorkerMetric
from app.services import worker_features
from tests.helpers import account, booking, complete, enroll, service_request, worker


def test_category_quality_uses_recorded_reviews_not_seed_totals(api):
    c, _ = account(api)
    w, profile, _ = worker(api, categories=["Plumbing", "Electrical"])
    for category, rating in (("Plumbing", 5), ("Electrical", 1)):
        job = booking(api, c, service_request(api, c, category=category), profile)
        complete(api, w, job["id"], c)
        assert (
            api.post(
                f"/api/v1/bookings/{job['id']}/review",
                headers=c,
                json={"rating": rating, "comment": "Recorded category feedback."},
            ).status_code
            == 201
        )
    with api.app.state.sessions() as db:
        record = db.get(Worker, profile["id"])
        record.review_count, record.rating_total = 900, 4500
        for metric in record.metrics:
            metric.completed_jobs = 999
        db.commit()
    with api.app.state.sessions() as db:
        record = db.get(Worker, profile["id"])
        plumbing = worker_features(db, [record], "cat08")[0]
        electrical = worker_features(db, [record], "cat04")[0]
        assert plumbing["completed_jobs"] == electrical["completed_jobs"] == 1
        assert plumbing["rating"] == 5 and electrical["rating"] == 1
        assert plumbing["avg_rating_before"] == electrical["avg_rating_before"] == 3
        assert plumbing["completed_jobs_before"] == 2
    result = api.get(f"/api/v1/workers/{profile['id']}").json()["data"]
    assert result["reviewCount"] == 2 and result["rating"] == 3
    request = service_request(api, c)
    rec = api.post(f"/api/v1/requests/{request['id']}/recommendations", headers=c, json={}).json()[
        "data"
    ]["recommendations"][0]
    assert "Plumbing rating 5.00/5 from 1 recorded reviews." in rec["reasons"]
    assert rec["evidence"]["completedJobs"] == 1


def test_provenance_is_admin_only_prospective_and_excludes_test_history(api):
    c, user = account(api)
    w, profile, _ = worker(api)
    admin, _ = account(api, "admin")
    old = booking(api, c, service_request(api, c), profile)
    complete(api, w, old["id"], c)
    path = f"/api/v1/admin/data-sources/customers/{user['id']}"
    assert (
        api.patch(
            path, headers=c, json={"dataSource": "real", "note": "Attempted self enrollment."}
        ).status_code
        == 403
    )
    enroll(api, admin, "customers", user["id"])
    enroll(api, admin, "workers", profile["id"])
    new = booking(api, c, service_request(api, c), profile)
    assert new["dataSource"] == "real"
    assert (
        api.get(f"/api/v1/bookings/{old['id']}", headers=c).json()["data"]["dataSource"] == "test"
    )
    with api.app.state.sessions() as db:
        snapshot = deepcopy(db.get(Booking, new["id"]).prediction)
        assert snapshot["inputs"]["completed_jobs_before"] == 0
        assert snapshot["featureVersion"] == evidence.FEATURE_VERSION
    complete(api, w, new["id"], c)
    exported = api.get("/api/v1/admin/training-dataset", headers=admin).json()["data"]
    assert len(exported["rows"]) == 1
    assert exported["rows"][0]["completed_jobs_before"] == 0
    assert exported["rows"][0]["probability"] is None  # Offline snapshots still train later.
    assert exported["excluded"]["nonRealData"] == 1
    assert exported["readiness"]["readyForSplitCheck"] is False
    assert api.get("/api/v1/admin/training-dataset", headers=c).status_code == 403
    with api.app.state.sessions() as db:
        assert db.get(Booking, new["id"]).prediction == snapshot
    profile_data = api.get("/api/v1/worker/profile", headers=w).json()["data"]
    assert profile_data["evidence"]["completedJobs"] == 1
    assert profile_data["dataSource"] == "real"


def test_demo_identity_cannot_be_laundered_into_real(api):
    _, profile, user = worker(api)
    admin, _ = account(api, "admin")
    with api.app.state.sessions() as db:
        db.get(User, user["id"]).data_source = "demo"
        db.commit()
    path = f"/api/v1/admin/data-sources/workers/{profile['id']}"
    for destination in ("test", "real"):
        assert (
            api.patch(
                path,
                headers=admin,
                json={"dataSource": destination, "note": "Attempt to promote demo identity."},
            ).status_code
            == 409
        )


def test_real_customer_with_test_worker_remains_test_and_source_cannot_be_injected(api):
    c, user = account(api)
    _, profile, _ = worker(api)
    admin, _ = account(api, "admin")
    enroll(api, admin, "customers", user["id"])
    job = booking(api, c, service_request(api, c), profile)
    assert job["dataSource"] == "test"
    assert api.patch("/api/v1/me", headers=c, json={"dataSource": "real"}).status_code == 422


def test_no_legacy_snapshots_are_exported_as_current_contract(api):
    c, user = account(api)
    w, profile, _ = worker(api)
    admin, _ = account(api, "admin")
    enroll(api, admin, "customers", user["id"])
    enroll(api, admin, "workers", profile["id"])
    job = booking(api, c, service_request(api, c), profile)
    complete(api, w, job["id"], c)
    with api.app.state.sessions() as db:
        record = db.get(Booking, job["id"])
        record.prediction = {**record.prediction, "featureVersion": "outcomes-v1"}
        db.commit()
    report = api.get("/api/v1/admin/training-dataset", headers=admin).json()["data"]
    assert report["rows"] == [] and report["excluded"]["incompatibleSnapshot"] == 1
