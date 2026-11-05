"""HTTP client for the SkillSync AI inference service.

Calls the stateless inference API; never sends passwords, tokens, customer
addresses, or other unnecessary personal data.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Any

import httpx

from app.catalog import CATEGORY_LABELS
from app.evidence import FEATURE_VERSION

logger = logging.getLogger("skillsync.ai")


class AIServiceError(Exception):
    """Raised when the AI service is unreachable or returns an invalid response."""

    def __init__(self, message: str, *, recoverable: bool = True):
        super().__init__(message)
        self.recoverable = recoverable


@dataclass
class ClassificationResult:
    text: str
    category: str


@dataclass
class WorkerRecommendation:
    worker_id: str
    name: str
    skill_score: float
    skill_level: str
    recommendation_score: float
    explanation: str
    reliability_probability: float
    reliability_percentage: float
    imputed_features: list[str] = field(default_factory=list)
    cold_start: bool = False
    missing_scoring_features: list[str] = field(default_factory=list)


@dataclass
class RecommendationResult:
    total_candidates: int
    top_k: int
    recommendations: list[WorkerRecommendation]
    model_version: str | None = None


def _client(base_url: str, timeout: float) -> httpx.Client:
    return httpx.Client(base_url=base_url, timeout=timeout)


def classify_text(base_url: str, timeout: float, text: str) -> ClassificationResult:
    """Call the inference service /classify endpoint."""
    try:
        with _client(base_url, timeout) as client:
            response = client.post("/classify", json={"text": text})
    except httpx.TimeoutException:
        raise AIServiceError("AI classification service timed out.")
    except httpx.ConnectError:
        raise AIServiceError("AI classification service is not reachable.")
    except httpx.HTTPError as exc:
        raise AIServiceError(f"AI classification request failed: {exc}")

    if response.status_code == 503:
        raise AIServiceError("AI classification model is unavailable.")
    if response.status_code != 200:
        raise AIServiceError(f"AI classification returned HTTP {response.status_code}.")

    try:
        data = response.json()
        category = str(data["category"])
    except (ValueError, KeyError, TypeError) as exc:
        raise AIServiceError(f"AI classification returned malformed response: {exc}")

    if category not in CATEGORY_LABELS:
        raise AIServiceError(
            f"AI classifier returned unsupported category '{category}'.",
            recoverable=False,
        )

    return ClassificationResult(text=text, category=category)


def get_health(base_url: str, timeout: float) -> dict[str, Any]:
    """Check the AI service health status."""
    try:
        with _client(base_url, timeout) as client:
            response = client.get("/health")
        data = response.json()
        if response.status_code not in {200, 503} or not isinstance(data, dict):
            raise ValueError("Invalid health response")
        models = data.get("models")
        if not isinstance(models, dict) or any(
            type(value) is not bool for value in models.values()
        ):
            raise ValueError("Invalid model status")
        return data
    except Exception:
        return {"status": "unreachable", "models": {}, "errors": {"connection": "unreachable"}}


def recommend_workers(
    base_url: str,
    timeout: float,
    workers: list[dict],
    top_k: int = 10,
) -> RecommendationResult:
    """Call the inference service /recommend endpoint with worker feature data."""
    if not workers:
        return RecommendationResult(total_candidates=0, top_k=top_k, recommendations=[])

    try:
        with _client(base_url, timeout) as client:
            response = client.post(
                "/recommend",
                json={"workers": workers, "top_k": top_k, "feature_version": FEATURE_VERSION},
            )
    except httpx.TimeoutException:
        raise AIServiceError("AI recommendation service timed out.")
    except httpx.ConnectError:
        raise AIServiceError("AI recommendation service is not reachable.")
    except httpx.HTTPError as exc:
        raise AIServiceError(f"AI recommendation request failed: {exc}")

    if response.status_code == 503:
        raise AIServiceError("AI recommendation model is unavailable.")
    if response.status_code != 200:
        raise AIServiceError(f"AI recommendation returned HTTP {response.status_code}.")

    try:
        data = response.json()
        recs = []
        for entry in data["recommendations"]:
            for key, maximum in (
                ("skill_score", 100),
                ("recommendation_score", 100),
                ("reliability_probability", 1),
                ("reliability_percentage", 100),
            ):
                value = entry[key]
                if (
                    type(value) not in (int, float)
                    or not math.isfinite(value)
                    or not 0 <= value <= maximum
                ):
                    raise ValueError("Invalid prediction score")
            for key in ("imputed_features", "missing_scoring_features"):
                value = entry.get(key, [])
                if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
                    raise ValueError("Invalid prediction metadata")
            if type(entry.get("cold_start", False)) is not bool:
                raise ValueError("Invalid cold-start metadata")
            recs.append(
                WorkerRecommendation(
                    worker_id=str(entry["worker_id"]),
                    name=str(entry["name"]),
                    skill_score=float(entry["skill_score"]),
                    skill_level=str(entry["skill_level"]),
                    recommendation_score=float(entry["recommendation_score"]),
                    explanation=str(entry["explanation"]),
                    reliability_probability=float(entry["reliability_probability"]),
                    reliability_percentage=float(entry["reliability_percentage"]),
                    imputed_features=list(entry.get("imputed_features", [])),
                    cold_start=bool(entry.get("cold_start", False)),
                    missing_scoring_features=list(entry.get("missing_scoring_features", [])),
                )
            )
        eligible = {str(worker["worker_id"]) for worker in workers}
        returned = [entry.worker_id for entry in recs]
        if (
            len(returned) != min(top_k, len(workers))
            or len(set(returned)) != len(returned)
            or not set(returned).issubset(eligible)
        ):
            raise ValueError("Unexpected worker IDs or incomplete ranking")
        if any(
            left.recommendation_score < right.recommendation_score
            for left, right in zip(recs, recs[1:])
        ):
            raise ValueError("Predictions are not ranked")
        return RecommendationResult(
            total_candidates=int(data.get("total_candidates", len(recs))),
            top_k=int(data.get("top_k", top_k)),
            recommendations=recs,
            model_version=data.get("model_version")
            if isinstance(data.get("model_version"), str)
            else None,
        )
    except (ValueError, KeyError, TypeError) as exc:
        raise AIServiceError(f"AI recommendation returned malformed response: {exc}")
