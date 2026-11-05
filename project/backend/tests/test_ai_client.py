from copy import deepcopy

import httpx
import pytest

from app import ai_client


def response_body():
    return {
        "total_candidates": 1,
        "top_k": 1,
        "recommendations": [
            {
                "worker_id": "eligible-worker",
                "name": "Worker",
                "skill_score": 68.25,
                "skill_level": "Skilled",
                "recommendation_score": 71.5,
                "explanation": "Available information",
                "reliability_probability": 0.8,
                "reliability_percentage": 80,
                "cold_start": True,
                "imputed_features": ["late_rate_before"],
                "missing_scoring_features": ["distance_km"],
            }
        ],
    }


@pytest.mark.parametrize(
    "change",
    [
        {"worker_id": "not-an-eligible-worker"},
        {"skill_score": 101},
        {"reliability_probability": -0.1},
        {"cold_start": "false"},
        {"imputed_features": "late_rate_before"},
    ],
)
def test_client_rejects_invalid_prediction_metadata_and_unrelated_workers(monkeypatch, change):
    body = response_body()
    body["recommendations"][0].update(change)
    monkeypatch.setattr(
        ai_client,
        "_client",
        lambda *_: httpx.Client(
            base_url="http://inference",
            transport=httpx.MockTransport(lambda request: httpx.Response(200, json=body)),
        ),
    )
    with pytest.raises(ai_client.AIServiceError):
        ai_client.recommend_workers("http://inference", 1, [{"worker_id": "eligible-worker"}], 1)


@pytest.mark.parametrize("kind", ["empty", "duplicate", "nonfinite"])
def test_client_rejects_missing_duplicate_and_nonfinite_results(monkeypatch, kind):
    body = response_body()
    if kind == "empty":
        body["recommendations"] = []
    elif kind == "duplicate":
        body["recommendations"].append(deepcopy(body["recommendations"][0]))
    else:
        body["recommendations"][0]["skill_score"] = "NaN"
    monkeypatch.setattr(
        ai_client,
        "_client",
        lambda *_: httpx.Client(
            base_url="http://inference",
            transport=httpx.MockTransport(lambda request: httpx.Response(200, json=body)),
        ),
    )
    with pytest.raises(ai_client.AIServiceError):
        ai_client.recommend_workers("http://inference", 1, [{"worker_id": "eligible-worker"}], 1)


def test_health_does_not_treat_a_string_as_a_model_status(monkeypatch):
    monkeypatch.setattr(
        ai_client,
        "_client",
        lambda *_: httpx.Client(
            base_url="http://inference",
            transport=httpx.MockTransport(
                lambda request: httpx.Response(200, json={"models": {"reliability": "false"}})
            ),
        ),
    )
    assert ai_client.get_health("http://inference", 1)["status"] == "unreachable"
