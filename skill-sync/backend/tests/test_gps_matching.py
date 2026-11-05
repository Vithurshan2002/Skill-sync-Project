from datetime import datetime, timedelta

import pytest
from sqlalchemy import select

from app.location import distance_km
from app.models import AuditEvent, Booking, Worker
from tests.helpers import account, booking, request_payload, service_request, worker


def test_haversine_handles_zero_dateline_and_antipodes():
    assert distance_km(0, 0, 0, 0) == 0
    assert distance_km(0, 0, 1, 0) == pytest.approx(111.195, abs=0.01)
    assert distance_km(0, 179, 0, -179) == pytest.approx(222.39, abs=0.02)
    assert distance_km(0, 0, 0, 180) == pytest.approx(20015.114, abs=0.02)


@pytest.mark.parametrize(
    "coords",
    [
        {"latitude": 91, "longitude": 80},
        {"latitude": 7, "longitude": 181},
        {"latitude": 7},
        {"longitude": 80},
        {"latitude": None, "longitude": 80},
        {"latitude": "NaN", "longitude": 80},
        {"latitude": "Infinity", "longitude": 80},
    ],
)
def test_invalid_job_coordinates_are_rejected(api, coords):
    customer, _ = account(api)
    response = api.post("/api/v1/requests", headers=customer, json=request_payload(**coords))
    assert response.status_code == 422


def test_worker_location_is_atomic_private_and_requires_reapproval(api):
    owner, profile, _ = worker(api)
    path = "/api/v1/worker/profile"
    for payload in [
        {"latitude": 7, "longitude": 80},
        {"serviceRadiusKm": 20},
        {"latitude": 7, "longitude": 80, "serviceRadiusKm": 0},
        {"latitude": 7, "longitude": 80, "serviceRadiusKm": 501},
    ]:
        assert api.patch(path, headers=owner, json=payload).status_code == 422
    # An older pending baseline has no GPS fields; the diff must still render.
    with api.app.state.sessions() as db:
        row = db.get(Worker, profile["id"])
        if row.review_baseline:
            row.review_baseline = {
                k: v
                for k, v in row.review_baseline.items()
                if k not in {"serviceLocation", "serviceRadiusKm"}
            }
        db.commit()
    result = api.patch(
        path,
        headers=owner,
        json={
            "latitude": 0,
            "longitude": 0,
            "serviceRadiusKm": 20,
        },
    )
    assert result.status_code == 200, result.text
    assert result.json()["data"]["verified"] is False
    assert any(x["field"] == "serviceLocation" for x in result.json()["data"]["profileChanges"])
    assert api.get(path, headers=owner).json()["data"]["latitude"] == 0
    admin, _ = account(api, "admin")
    approval = api.patch(
        f"/api/v1/admin/workers/{profile['id']}/verification",
        headers=admin,
        json={"verified": True, "note": "Checked the saved service location."},
    )
    assert approval.status_code == 200, approval.text
    public = api.get(f"/api/v1/workers/{profile['id']}").json()["data"]
    assert public["latitude"] is None and public["longitude"] is None
    assert public["profileChanges"] == []
    assert (
        api.patch(
            path,
            headers=owner,
            json={
                "latitude": None,
                "longitude": None,
                "serviceRadiusKm": None,
            },
        ).json()["data"]["verified"]
        is False
    )


def test_gps_matching_radius_fallback_privacy_and_booking_enforcement(api):
    customer, _ = account(api)
    stranger, _ = account(api)
    _, near, _ = worker(
        api, name="Z Near", latitude=7, longitude=80, serviceRadiusKm=10, serviceTowns=["Kandy"]
    )
    _, farther, _ = worker(api, name="A Farther", latitude=7.05, longitude=80, serviceRadiusKm=10)
    _, outside, _ = worker(api, name="Outside", latitude=8, longitude=80, serviceRadiusKm=10)
    _, legacy, _ = worker(api, name="Legacy town only")
    worker(
        api,
        name="Wrong skill",
        latitude=7,
        longitude=80,
        serviceRadiusKm=10,
        categories=["Electrical"],
    )
    worker(api, name="Unavailable", latitude=7, longitude=80, serviceRadiusKm=10, available=False)
    worker(api, name="Not approved", latitude=7, longitude=80, serviceRadiusKm=10, approved=False)
    job = service_request(api, customer, latitude=7, longitude=80)
    path = f"/api/v1/requests/{job['id']}"
    assert api.get(path, headers=stranger).status_code == 404
    response = api.post(path + "/recommendations", headers=customer, json={})
    assert response.status_code == 200, response.text
    results = response.json()["data"]["recommendations"]
    assert [x["workerId"] for x in results] == [near["id"], farther["id"], legacy["id"]]
    assert results[0]["distanceKm"] == 0 and results[0]["locationMatch"] == "gps"
    assert results[0]["worker"]["latitude"] is None
    assert results[1]["distanceKm"] == pytest.approx(5.56, abs=0.02)
    assert results[2]["distanceKm"] is None and results[2]["locationMatch"] == "town"
    assert any("town match only" in reason for reason in results[2]["reasons"])
    assert (
        api.post(
            "/api/v1/bookings",
            headers=customer,
            json={
                "requestId": job["id"],
                "workerId": outside["id"],
                "scheduledAt": job["preferredAt"],
                "scheduledEndAt": (
                    datetime.fromisoformat(job["preferredAt"]) + timedelta(hours=4)
                ).isoformat(),
                "deadlineAt": (
                    datetime.fromisoformat(job["preferredAt"]) + timedelta(hours=4)
                ).isoformat(),
            },
        ).status_code
        == 422
    )
    assert api.patch(path, headers=customer, json={"latitude": 8}).status_code == 422
    booked = booking(api, customer, job, near)
    assert booked["request"]["latitude"] == 7
    assert (
        api.patch(path, headers=customer, json={"latitude": None, "longitude": None}).status_code
        == 409
    )
    no_gps = service_request(api, customer)
    matches = api.post(
        f"/api/v1/requests/{no_gps['id']}/recommendations", headers=customer, json={}
    ).json()["data"]["recommendations"]
    assert outside["id"] in [x["workerId"] for x in matches]
    assert all(x["distanceKm"] is None for x in matches)


def test_actual_model_uses_distance_for_ranking_but_not_reliability(api, real_ai_url):
    api.app.state.settings.ai_enabled = True
    api.app.state.settings.ai_base_url = real_ai_url
    customer, _ = account(api)
    _, far, _ = worker(api, name="A Far", latitude=7.1, longitude=80, serviceRadiusKm=20)
    _, near, _ = worker(api, name="Z Near", latitude=7, longitude=80, serviceRadiusKm=20)
    job = service_request(api, customer, latitude=7, longitude=80)
    response = api.post(f"/api/v1/requests/{job['id']}/recommendations", headers=customer, json={})
    assert response.status_code == 200, response.text
    result = response.json()["data"]
    assert result["source"] == "model"
    first, second = result["recommendations"]
    assert [first["workerId"], second["workerId"]] == [near["id"], far["id"]]
    assert first["matchScore"] > second["matchScore"]
    assert first["reliabilityProbability"] == second["reliabilityProbability"]
    assert "distance_km" not in first["missingScoringFeatures"]
    made = booking(api, customer, job, near)
    with api.app.state.sessions() as db:
        snapshot = db.get(Booking, made["id"]).prediction["inputs"]
        assert snapshot["distance_km"] == 0
        assert "latitude" not in snapshot and "longitude" not in snapshot
        audit = db.scalar(
            select(AuditEvent).where(
                AuditEvent.record_id == job["id"], AuditEvent.action == "request.recommendations"
            )
        )
        assert all(
            "latitude" not in row and "longitude" not in row for row in audit.details["inputs"]
        )
