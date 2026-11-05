import pytest
from sqlalchemy import func, select
from unittest.mock import patch

from app.ai_client import (
    AIServiceError,
    ClassificationResult,
    RecommendationResult,
    WorkerRecommendation,
)
from app.models import AuditEvent
from tests.helpers import account, service_request, worker


def test_classify_success_with_model_provenance_and_audit(api, monkeypatch):
    headers, user = account(api, "customer")
    req = service_request(
        api,
        headers,
        category=None,
        description="The pipe burst in the bathroom and water is everywhere.",
    )
    path = f"/api/v1/requests/{req['id']}/classify"

    # Enable AI on the test client app
    api.app.state.settings.ai_enabled = True

    with patch("app.services.classify_text") as mock_classify:
        mock_classify.return_value = ClassificationResult(
            text="The pipe burst in the bathroom and water is everywhere.",
            category="Plumbing",
        )
        response = api.post(path, headers=headers)
        assert response.status_code == 200, response.text
        data = response.json()["data"]
        assert data["category"] == "Plumbing"
        assert data["source"] == "model"
        assert data["classified"] is True
        assert data["modelType"] == "nlp_svm"

    # Check request was updated in database
    req_data = api.get(f"/api/v1/requests/{req['id']}", headers=headers).json()["data"]
    assert req_data["category"] == "Plumbing"

    # Check AuditEvent recorded in database
    with api.app.state.sessions() as db:
        events = db.scalars(
            select(AuditEvent).where(
                AuditEvent.action == "request.classified",
                AuditEvent.record_id == req["id"],
            )
        ).all()
        assert len(events) == 1
        assert events[0].details["predicted_category"] == "Plumbing"
        assert events[0].details["model_type"] == "nlp_svm"


def test_classify_handles_outage_gracefully(api):
    headers, _ = account(api, "customer")
    req = service_request(api, headers, category=None)
    path = f"/api/v1/requests/{req['id']}/classify"

    api.app.state.settings.ai_enabled = True

    with patch("app.services.classify_text", side_effect=AIServiceError("Connection refused")):
        response = api.post(path, headers=headers)
        assert response.status_code == 503
        assert response.json()["error"]["code"] == "model_unavailable"


def test_classify_preserves_existing_category(api):
    headers, _ = account(api, "customer")
    req = service_request(api, headers, category="Electrical")
    path = f"/api/v1/requests/{req['id']}/classify"

    api.app.state.settings.ai_enabled = True

    response = api.post(path, headers=headers)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["category"] == "Electrical"
    assert data["source"] == "existing"
    assert data["classified"] is False


def test_recommendations_with_model_scoring_and_audit(api):
    customer, _ = account(api, "customer")
    _, w1, _ = worker(api, name="Alice Plumber", categories=["Plumbing"], yearsExperience=6)
    _, w2, _ = worker(api, name="Bob Plumber", categories=["Plumbing"], yearsExperience=2)

    req = service_request(api, customer, category="Plumbing")
    path = f"/api/v1/requests/{req['id']}/recommendations"

    api.app.state.settings.ai_enabled = True

    with patch("app.services.recommend_workers") as mock_recs:
        mock_recs.return_value = RecommendationResult(
            total_candidates=2,
            top_k=2,
            recommendations=[
                WorkerRecommendation(
                    worker_id=w1["id"],
                    name="Alice Plumber",
                    skill_score=85.0,
                    skill_level="Highly Skilled",
                    recommendation_score=88.5,
                    explanation="Recommended because of high skill competency, strong predicted reliability.",
                    reliability_probability=0.92,
                    reliability_percentage=92.0,
                    imputed_features=["cancellation_rate_before"],
                    cold_start=False,
                    missing_scoring_features=["complaint_rate", "distance_km"],
                ),
                WorkerRecommendation(
                    worker_id=w2["id"],
                    name="Bob Plumber",
                    skill_score=60.0,
                    skill_level="Moderately Skilled",
                    recommendation_score=62.0,
                    explanation="Recommended because of balanced overall performance.",
                    reliability_probability=0.75,
                    reliability_percentage=75.0,
                    imputed_features=[],
                    cold_start=True,
                    missing_scoring_features=["rating", "distance_km"],
                ),
            ],
        )

        response = api.post(path, headers=customer, json={"available": True})
        assert response.status_code == 200, response.text
        data = response.json()["data"]
        assert data["source"] == "model"
        assert len(data["recommendations"]) == 2

        first = data["recommendations"][0]
        assert first["workerId"] == w1["id"]
        assert first["source"] == "model"
        assert first["matchScore"] == 88.5
        assert first["categorySkillScore"] == 85.0
        assert first["reliabilityProbability"] == 0.92
        assert first["reliabilityPercentage"] == 92.0
        assert first["coldStart"] is False
        assert "cancellation_rate_before" in first["imputedFeatures"]

    # Check AuditEvent recorded in database
    with api.app.state.sessions() as db:
        events = db.scalars(
            select(AuditEvent).where(
                AuditEvent.action == "request.recommendations",
                AuditEvent.record_id == req["id"],
            )
        ).all()
        assert len(events) == 1
        assert events[0].details["source"] == "model"
        assert events[0].details["candidates"] == 2


def test_recommendations_fallback_on_ai_failure(api):
    customer, _ = account(api, "customer")
    _, w1, _ = worker(api, name="Alice Plumber", categories=["Plumbing"])
    req = service_request(api, customer, category="Plumbing")
    path = f"/api/v1/requests/{req['id']}/recommendations"

    api.app.state.settings.ai_enabled = True

    with patch("app.services.recommend_workers", side_effect=AIServiceError("AI unreachable")):
        response = api.post(path, headers=customer, json={"available": True})
        assert response.status_code == 200
        data = response.json()["data"]
        # Must fall back gracefully to rule_based
        assert data["source"] == "rule_based"
        assert data["recommendations"][0]["source"] == "rule_based"
        assert data["recommendations"][0]["matchScore"] is None
