from sqlalchemy import select

from app.models import AuditEvent
from tests.helpers import account, booking, complete, service_request, worker, enroll


def test_real_models_database_and_booking_flow(api, real_ai_url):
    api.app.state.settings.ai_enabled = True
    api.app.state.settings.ai_base_url = real_ai_url
    customer, customer_user = account(api)
    stranger, _ = account(api)
    professional, profile, _ = worker(api)
    admin, _ = account(api, "admin")
    enroll(api, admin, "customers", customer_user["id"])
    enroll(api, admin, "workers", profile["id"])
    worker(api, name="Wrong Category", categories=["Electrical"])
    request = service_request(api, customer, category=None)
    path = f"/api/v1/requests/{request['id']}"
    assert api.post(path + "/classify", headers=stranger).status_code == 404
    classified = api.post(path + "/classify", headers=customer)
    assert classified.status_code == 200, classified.text
    assert classified.json()["data"]["category"] == "Plumbing"
    assert classified.json()["data"]["source"] == "model"
    response = api.post(path + "/recommendations", headers=customer, json={})
    assert response.status_code == 200, response.text
    result = response.json()["data"]
    assert result["source"] == "model"
    assert [entry["workerId"] for entry in result["recommendations"]] == [profile["id"]]
    match = result["recommendations"][0]
    assert match["coldStart"] is True
    assert "late_rate_before" in match["imputedFeatures"]
    assert "certified" in match["missingScoringFeatures"]
    assert "distance_km" in match["missingScoringFeatures"]
    assert 0 <= match["reliabilityProbability"] <= 1
    assert 0 <= match["matchScore"] <= 100
    booked = booking(api, customer, request, profile)
    assert api.post(path + "/classify", headers=customer).status_code == 409
    complete(api, professional, booked["id"], customer)
    review = api.post(
        f"/api/v1/bookings/{booked['id']}/review",
        headers=customer,
        json={"rating": 5, "comment": "Careful repair, thank you."},
    )
    assert review.status_code == 201, review.text
    performance = api.get("/api/v1/worker/performance", headers=professional)
    assert performance.status_code == 200, performance.text
    data = performance.json()["data"]
    assert data["completedJobs"] == 1 and data["rating"] == 5
    assert data["coldStart"] is False and data["modelStatus"] == "available"
    assert "avg_response_minutes_before" not in data["imputedFeatures"]
    assert "avg_rating_before" not in data["imputedFeatures"]
    assert "late_rate_before" not in data["imputedFeatures"]
    assert "cancellation_rate_before" not in data["imputedFeatures"]
    admin, _ = account(api, "admin")
    evaluation = api.get("/api/v1/admin/model-evaluation", headers=admin).json()["data"]
    assert evaluation["sampleCount"] == 1
    assert len(evaluation["models"][0]["modelVersion"]) == 64
    with api.app.state.sessions() as db:
        snapshots = db.scalars(
            select(AuditEvent).where(AuditEvent.record_id == request["id"])
        ).all()
        assert {entry.action for entry in snapshots} == {
            "request.classified",
            "request.recommendations",
        }
        snapshot = next(entry for entry in snapshots if entry.action == "request.recommendations")
        assert snapshot.details["inputs"][0]["certified"] is None
        assert snapshot.details["result"]["recommendations"][0]["workerId"] == profile["id"]


def test_reject_untrained_category_and_keep_manual_override(api):
    customer, _ = account(api)
    request = service_request(api, customer)
    path = f"/api/v1/requests/{request['id']}"
    assert api.patch(path, headers=customer, json={"category": "Painting"}).status_code == 422
    assert api.patch(path, headers=customer, json={"category": "Welding"}).status_code == 200
    result = api.post(path + "/classify", headers=customer)
    assert result.json()["data"]["source"] == "existing"
    assert result.json()["data"]["category"] == "Welding"
