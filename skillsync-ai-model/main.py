"""Inference API for the saved SkillSync models; never trains or writes data."""

from contextlib import asynccontextmanager
import logging
import hashlib
import json
import math
from pathlib import Path
from typing import Annotated

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from scoring import calculate_skill_score, calculate_recommendation_score, generate_explanation

LOGGER = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parent
NLP_MODEL_PATH = PROJECT_ROOT / "models" / "nlp_svm.joblib"
RELIABILITY_MODEL_PATH = PROJECT_ROOT / "models" / "reliability_rf.joblib"
FEATURE_CONTRACT = json.loads((PROJECT_ROOT / "feature_contract.json").read_text())
RELIABILITY_FEATURES = tuple(FEATURE_CONTRACT["features"])
nlp_model = None
reliability_model = None
model_errors: dict[str, str] = {}
reliability_version = None
training_contract_status = "legacy_unverified"


def load_models():
    """Load independently so health describes missing or incompatible artifacts."""
    global nlp_model, reliability_model, reliability_version, training_contract_status
    training_contract_status = "legacy_unverified"
    reliability_version = None
    nlp_model = reliability_model = None
    model_errors.clear()
    for name, path in (("classification", NLP_MODEL_PATH), ("reliability", RELIABILITY_MODEL_PATH)):
        if not path.is_file():
            model_errors[name] = "artifact_missing"
            continue
        try:
            model = joblib.load(path)
            if name == "classification":
                model.predict(["My kitchen sink is leaking"])
                nlp_model = model
            else:
                if list(model.feature_names_in_) != list(RELIABILITY_FEATURES):
                    raise ValueError("Reliability artifact has an incompatible feature schema")
                positive_index = list(model.classes_).index(1)
                probe = pd.DataFrame([[float("nan")] * len(RELIABILITY_FEATURES)], columns=RELIABILITY_FEATURES)
                probability = float(model.predict_proba(probe)[0][positive_index])
                if not math.isfinite(probability) or not 0 <= probability <= 1:
                    raise ValueError("Reliability artifact produced an invalid probability")
                reliability_version = hashlib.sha256(path.read_bytes()).hexdigest()
                metadata_path = path.with_suffix(".metadata.json")
                if metadata_path.is_file():
                    metadata = json.loads(metadata_path.read_text())
                    if metadata.get("artifactSha256") != reliability_version or metadata.get("featureVersion") != FEATURE_CONTRACT["version"]:
                        raise ValueError("Model metadata does not match artifact or serving contract")
                    training_contract_status = "recorded_outcomes_v2"
                reliability_model = model
        except Exception:
            model_errors[name] = "artifact_load_failed"
            LOGGER.exception("Unable to load %s model", name)


@asynccontextmanager
async def lifespan(_app):
    load_models()
    yield


app = FastAPI(title="SkillSync AI API", version="0.2.0", lifespan=lifespan)


class RequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, allow_inf_nan=False)


class ServiceRequest(RequestModel):
    text: str = Field(min_length=2, max_length=5000)


class ReliabilityRequest(RequestModel):
    # Missing history uses the median imputer already fitted in the saved pipeline.
    completed_jobs_before: int | None = Field(default=None, ge=0)
    cancellation_rate_before: float | None = Field(default=None, ge=0, le=1)
    late_rate_before: float | None = Field(default=None, ge=0, le=1)
    avg_response_minutes_before: float | None = Field(default=None, ge=0)
    avg_rating_before: float | None = Field(default=None, ge=0, le=5)
    complaint_rate_before: float | None = Field(default=None, ge=0, le=1)


class WorkerRecommendationRequest(RequestModel):
    experience_years: float = Field(ge=0)
    completed_jobs: int = Field(ge=0)
    rating: float | None = Field(default=None, ge=0, le=5)
    certified: bool | None = None
    complaint_rate: float | None = Field(default=None, ge=0, le=1)
    reliability_probability: float = Field(ge=0, le=1)
    available: bool
    distance_km: float | None = Field(default=None, ge=0)


class WorkerCandidate(ReliabilityRequest):
    worker_id: Annotated[str, StringConstraints(min_length=1, max_length=128)] | int
    name: str = Field(min_length=1, max_length=200)
    experience_years: float = Field(ge=0)
    completed_jobs: int = Field(ge=0)
    rating: float | None = Field(default=None, ge=0, le=5)
    certified: bool | None = None
    complaint_rate: float | None = Field(default=None, ge=0, le=1)
    available: bool
    distance_km: float | None = Field(default=None, ge=0)


class MultipleWorkersRequest(RequestModel):
    feature_version: str | None = None
    workers: list[WorkerCandidate] = Field(max_length=1000)
    top_k: int = Field(default=3, ge=1, le=1000)

    @model_validator(mode="after")
    def unique_worker_ids(self):
        if self.feature_version is not None and self.feature_version != FEATURE_CONTRACT["version"]:
            raise ValueError("Unsupported worker feature contract")
        ids = [str(worker.worker_id) for worker in self.workers]
        if len(ids) != len(set(ids)):
            raise ValueError("Worker IDs must be unique")
        return self


class SmartWorkerCandidate(WorkerCandidate):
    category: str = Field(min_length=1, max_length=100)


class SmartRecommendationRequest(MultipleWorkersRequest):
    text: str = Field(min_length=2, max_length=5000)
    workers: list[SmartWorkerCandidate] = Field(max_length=1000)


def require_model(model, name):
    if model is None:
        raise HTTPException(status_code=503, detail=f"{name} model is unavailable. Check the AI service /health endpoint and saved artifacts.")


def classify_text(text):
    require_model(nlp_model, "Classification")
    try:
        return str(nlp_model.predict([text])[0])
    except Exception as exc:
        LOGGER.exception("Classification inference failed")
        raise HTTPException(status_code=503, detail="Classification inference failed.") from exc


def reliability_probabilities(workers):
    require_model(reliability_model, "Reliability")
    if not workers:
        return []
    rows = [
        {feature: getattr(worker, feature) if getattr(worker, feature) is not None else float("nan")
         for feature in RELIABILITY_FEATURES}
        for worker in workers
    ]
    try:
        frame = pd.DataFrame(rows, columns=RELIABILITY_FEATURES)
        positive_index = list(reliability_model.classes_).index(1)
        probabilities = [float(row[positive_index]) for row in reliability_model.predict_proba(frame)]
        if len(probabilities) != len(workers) or any(not math.isfinite(p) or not 0 <= p <= 1 for p in probabilities):
            raise ValueError("Invalid reliability model output")
        return probabilities
    except Exception as exc:
        LOGGER.exception("Reliability inference failed")
        raise HTTPException(status_code=503, detail="Reliability inference failed.") from exc


def reliability_metadata(worker):
    return {
        "imputed_features": [field for field in RELIABILITY_FEATURES if getattr(worker, field) is None],
        "cold_start": worker.completed_jobs_before is None or worker.completed_jobs_before == 0,
    }


def score_worker(worker, probability):
    skill = calculate_skill_score(worker.experience_years, worker.completed_jobs, worker.rating, worker.certified, worker.complaint_rate)
    return {
        "skill_score": skill["skill_score"],
        "skill_level": skill["level"],
        "recommendation_score": calculate_recommendation_score(skill["skill_score"], probability, worker.rating, worker.available, worker.distance_km),
        "explanation": generate_explanation(skill["skill_score"], probability, worker.rating, worker.distance_km),
        "missing_scoring_features": [field for field in ("rating", "certified", "complaint_rate", "distance_km") if getattr(worker, field) is None],
    }


def rank_workers(workers):
    probabilities = reliability_probabilities(workers)
    ranked = []
    for worker, probability in zip(workers, probabilities):
        result = {
            "worker_id": worker.worker_id,
            "name": worker.name,
            **score_worker(worker, probability),
            "reliability_probability": round(probability, 4),
            "reliability_percentage": round(probability * 100, 2),
            **reliability_metadata(worker),
        }
        if isinstance(worker, SmartWorkerCandidate):
            result.update(category=worker.category, rating=worker.rating, distance_km=worker.distance_km)
        ranked.append(result)
    return sorted(ranked, key=lambda worker: worker["recommendation_score"], reverse=True)


@app.get("/")
def root():
    return {"message": "SkillSync AI API is running."}


@app.get("/health")
def health():
    ready = nlp_model is not None and reliability_model is not None
    return JSONResponse(status_code=200 if ready else 503, content={
        "status": "ready" if ready else "unavailable",
        "models": {"classification": nlp_model is not None, "reliability": reliability_model is not None},
        "errors": model_errors,
        "categories": [str(category) for category in nlp_model.classes_] if nlp_model is not None else [],
        "reliability_features": list(RELIABILITY_FEATURES),
        "serving_feature_version": FEATURE_CONTRACT["version"],
        "training_contract_status": training_contract_status,
    })


@app.post("/classify")
def classify_service(request: ServiceRequest):
    return {"text": request.text, "category": classify_text(request.text)}


@app.post("/reliability")
def predict_reliability(worker: ReliabilityRequest):
    probability = reliability_probabilities([worker])[0]
    return {
        "reliability_probability": round(probability, 4),
        "reliability_percentage": round(probability * 100, 2),
        **reliability_metadata(worker),
    }


@app.post("/recommend-score")
def recommendation(worker: WorkerRecommendationRequest):
    return score_worker(worker, worker.reliability_probability)


@app.post("/recommend")
def recommend_workers(request: MultipleWorkersRequest):
    ranked = rank_workers(request.workers)
    return {"total_candidates": len(ranked), "top_k": request.top_k, "recommendations": ranked[:request.top_k], "model_version": reliability_version}


@app.post("/smart-recommend")
def smart_recommend(request: SmartRecommendationRequest):
    predicted_category = classify_text(request.text)
    workers = [worker for worker in request.workers if worker.available and worker.category.casefold() == predicted_category.casefold()]
    ranked = rank_workers(workers)
    result = {"request": request.text, "predicted_category": predicted_category, "matched_workers": len(ranked), "recommendations": ranked[:request.top_k]}
    if not ranked:
        result["message"] = "No available workers found."
    return result
