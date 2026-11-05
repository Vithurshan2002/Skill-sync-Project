"""Train a separate candidate from real, versioned pre-outcome snapshots. Never replace the active model."""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import accuracy_score, brier_score_loss, precision_score, recall_score, roc_auc_score
from sklearn.pipeline import Pipeline

ROOT = Path(__file__).resolve().parent
CONTRACT = json.loads((ROOT / "feature_contract.json").read_text())
FEATURES = CONTRACT["features"]


def prepare(payload):
    if payload.get("featureVersion") != CONTRACT["version"] or payload.get("target") != CONTRACT["target"]:
        raise ValueError("Incompatible feature contract or target; export fresh recorded snapshots.")
    rows = payload.get("rows", [])
    seen = set()
    for row in rows:
        if row.get("data_source") != "real" or row.get("feature_version") != CONTRACT["version"]:
            raise ValueError("Demo/test or unversioned rows cannot be used for retraining.")
        if row["booking_id"] in seen:
            raise ValueError("Duplicate booking in export.")
        seen.add(row["booking_id"])
        if type(row.get("completed_on_time")) is not int or row["completed_on_time"] not in (0, 1):
            raise ValueError("Labels must be confirmed binary outcomes.")
        for feature in FEATURES:
            value = row[feature]
            if value is not None:
                if type(value) not in (int, float) or not np.isfinite(value) or value < 0:
                    raise ValueError(f"Invalid feature: {feature}")
                if ("rate_before" in feature and value > 1) or (feature == "avg_rating_before" and value > 5):
                    raise ValueError(f"Out-of-range feature: {feature}")
                if feature == "completed_jobs_before" and value != int(value):
                    raise ValueError("Completed-job count must be integral.")
        predicted, outcome = datetime.fromisoformat(row["predicted_at"]), datetime.fromisoformat(row["outcome_at"])
        if not predicted.tzinfo or not outcome.tzinfo or outcome < predicted:
            raise ValueError("Outcomes must follow timezone-aware snapshot times.")
    if len(rows) < CONTRACT["minimum_training_rows"]:
        raise ValueError(f"Need at least {CONTRACT['minimum_training_rows']} eligible real outcomes; found {len(rows)}. Active model unchanged.")
    frame = pd.DataFrame(rows)
    if frame.worker_id.nunique() < CONTRACT["minimum_training_workers"]:
        raise ValueError("Need outcomes from at least five workers.")
    frame["captured"] = pd.to_datetime(frame.predicted_at, utc=True)
    frame["observed"] = pd.to_datetime(frame.outcome_at, utc=True)
    frame = frame.sort_values(["captured", "booking_id"])
    cutoff = frame.iloc[int(len(frame) * .8)].captured
    # Purge training jobs whose outcome was still unknown when the test period began.
    train = frame[(frame.captured < cutoff) & (frame.observed < cutoff)]
    test = frame[frame.captured >= cutoff]
    for split, minimum, name in ((train, CONTRACT["minimum_class_rows"], "training"), (test, 5, "test")):
        counts = split.completed_on_time.value_counts()
        if any(counts.get(label, 0) < minimum for label in (0, 1)):
            raise ValueError(f"Not enough on-time and late outcomes in chronological {name} split; collect more data.")
    return train, test, cutoff


def metrics(labels, probabilities):
    y, p = np.asarray(labels), np.asarray(probabilities)
    bands = []
    for index in range(5):
        mask = np.minimum((p * 5).astype(int), 4) == index
        bands.append({"lower": index / 5, "upper": (index + 1) / 5, "count": int(mask.sum()),
                      "meanPrediction": float(p[mask].mean()) if mask.any() else None,
                      "observedOnTimeRate": float(y[mask].mean()) if mask.any() else None})
    return {"sampleCount": len(y), "accuracy": float(accuracy_score(y, p >= .5)),
            "precision": float(precision_score(y, p >= .5, zero_division=0)),
            "recall": float(recall_score(y, p >= .5, zero_division=0)),
            "brierScore": float(brier_score_loss(y, p)),
            "rocAuc": float(roc_auc_score(y, p)) if len(set(y)) == 2 else None,
            "calibration": bands}


def probabilities(model, frame):
    return model.predict_proba(frame[FEATURES].astype(float))[:, list(model.classes_).index(1)]


def train_candidate(payload, baseline_path):
    train, test, cutoff = prepare(payload)
    candidate = Pipeline([
        ("missing_values", SimpleImputer(strategy="median", keep_empty_features=True)),
        ("random_forest", RandomForestClassifier(n_estimators=300, random_state=42, class_weight="balanced")),
    ])
    candidate.fit(train[FEATURES].astype(float), train.completed_on_time)
    baseline = joblib.load(baseline_path)
    predicted = probabilities(candidate, test)
    incumbent = probabilities(baseline, test)
    score = metrics(test.completed_on_time, predicted)
    old_score = metrics(test.completed_on_time, incumbent)
    groups = {}
    for category in sorted(test.category.unique()):
        mask = (test.category == category).to_numpy()
        groups[category] = metrics(test.completed_on_time[mask], predicted[mask])
    unseen = ~test.worker_id.isin(train.worker_id)
    return candidate, {
        "featureVersion": CONTRACT["version"], "target": CONTRACT["target"],
        "baselineSha256": hashlib.sha256(Path(baseline_path).read_bytes()).hexdigest(),
        "cutoff": cutoff.isoformat(), "trainRows": len(train), "testRows": len(test),
        "purgedRows": len(payload["rows"]) - len(train) - len(test),
        "candidate": score, "baseline": old_score, "byCategory": groups,
        "unseenWorkers": metrics(test.completed_on_time[unseen], predicted[unseen.to_numpy()]) if unseen.any() else None,
        "reviewRecommended": score["brierScore"] < old_score["brierScore"],
        "deployment": "Candidate only. Review class balance, calibration, subgroup sample sizes and baseline comparison before deployment; active artifact unchanged.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--baseline", type=Path, default=ROOT / "models/reliability_rf.joblib")
    args = parser.parse_args()
    try:
        if args.output_dir.exists():
            raise ValueError("Output directory already exists; choose a new candidate directory.")
        raw = args.dataset.read_bytes()
        model, report = train_candidate(json.loads(raw), args.baseline)
        args.output_dir.mkdir(parents=True, exist_ok=False)
        artifact = args.output_dir / "reliability_rf.joblib"
        joblib.dump(model, artifact)
        report.update(datasetSha256=hashlib.sha256(raw).hexdigest(), artifactSha256=hashlib.sha256(artifact.read_bytes()).hexdigest())
        (args.output_dir / "evaluation.json").write_text(json.dumps(report, indent=2, allow_nan=False), encoding="utf-8")
        artifact.with_suffix(".metadata.json").write_text(json.dumps({"artifactSha256": report["artifactSha256"], "featureVersion": CONTRACT["version"], "datasetSha256": report["datasetSha256"]}, indent=2), encoding="utf-8")
        (args.output_dir / "feature_contract.json").write_text(json.dumps(CONTRACT, indent=2), encoding="utf-8")
        print(json.dumps(report, indent=2))
    except (ValueError, KeyError) as error:
        parser.exit(2, f"Retraining not performed: {error}\n")


if __name__ == "__main__":
    main()
