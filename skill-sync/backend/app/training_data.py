"""Export only prospectively enrolled real outcomes, using their original feature snapshots."""

import argparse
from collections import Counter
from datetime import datetime
import json
from pathlib import Path
from sqlalchemy import select
from app import models as m
from app.evidence import CONTRACT, FEATURES, FEATURE_VERSION, aware


def dataset(db):
    rows, excluded = [], Counter()
    for b in db.scalars(select(m.Booking)):
        p = b.prediction or {}
        reason = None
        if b.data_source != "real":
            reason = "nonRealData"
        elif p.get("featureVersion") != FEATURE_VERSION or p.get("dataSource") != "real":
            reason = "incompatibleSnapshot"
        elif b.status != "completed" or not b.confirmed_at or not b.reported_completed_at:
            reason = "cancelled" if b.status == "cancelled" else "unconfirmed"
        elif not b.deadline_at:
            reason = "noDeadline"
        elif b.complaint and b.complaint.status == "pending":
            reason = "pendingComplaint"
        elif aware(b.reported_completed_at) > aware(b.confirmed_at):
            reason = "invalidOutcomeTime"
        else:
            try:
                captured = datetime.fromisoformat(p["predictedAt"])
                if (
                    captured.tzinfo is None
                    or captured > aware(b.reported_completed_at)
                    or captured > aware(b.confirmed_at)
                ):
                    reason = "invalidSnapshotTime"
                if any(f not in p["inputs"] for f in FEATURES):
                    reason = "incompleteSnapshot"
            except (KeyError, ValueError, TypeError):
                reason = "invalidSnapshot"
        if reason:
            excluded[reason] += 1
            continue
        rows.append(
            {
                "booking_id": b.id,
                "worker_id": b.worker_id,
                "category": b.request.category.label,
                "data_source": b.data_source,
                "feature_version": FEATURE_VERSION,
                "predicted_at": p["predictedAt"],
                "outcome_at": aware(b.confirmed_at).isoformat(),
                "model_version": p.get("modelVersion"),
                "probability": p.get("probability"),
                **{f: p["inputs"][f] for f in FEATURES},
                "completed_on_time": int(aware(b.reported_completed_at) <= aware(b.deadline_at)),
            }
        )
    rows.sort(key=lambda row: (datetime.fromisoformat(row["predicted_at"]), row["booking_id"]))
    classes = Counter(row["completed_on_time"] for row in rows)
    readiness = {
        "rows": len(rows),
        "workers": len({r["worker_id"] for r in rows}),
        "onTime": classes[1],
        "late": classes[0],
        "minimumRows": CONTRACT["minimum_training_rows"],
        "minimumWorkers": CONTRACT["minimum_training_workers"],
        "minimumPerClass": CONTRACT["minimum_class_rows"],
    }
    readiness["readyForSplitCheck"] = (
        len(rows) >= readiness["minimumRows"]
        and readiness["workers"] >= readiness["minimumWorkers"]
        and min(classes[0], classes[1]) >= readiness["minimumPerClass"]
    )
    return {
        "featureVersion": FEATURE_VERSION,
        "target": CONTRACT["target"],
        "exportedAt": m.utcnow().isoformat(),
        "contract": CONTRACT,
        "readiness": readiness,
        "excluded": dict(excluded),
        "rows": rows,
    }


def main():
    from app.config import Settings
    from app.database import make_engine, session_factory

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    engine = make_engine(Settings())
    try:
        with session_factory(engine)() as db:
            result = dataset(db)
        # No accidental replacement of an earlier export.
        with args.output.open("x", encoding="utf-8") as handle:
            json.dump(result, handle, indent=2, allow_nan=False)
        print(
            json.dumps(
                {
                    "export": str(args.output),
                    "readiness": result["readiness"],
                    "excluded": result["excluded"],
                }
            )
        )
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
