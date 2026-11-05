"""Observed booking evidence and prospective evaluation; never backfill predictions."""

from collections import Counter, defaultdict
from sqlalchemy import select
from app import models as m, serializers as out
from app.auth import require_role
from app.errors import conflict, missing


def create_complaint(db, user, booking_id, data):
    from app.services import booking_record, notify

    require_role(user, "customer")
    booking = booking_record(db, user, booking_id, lock=True)
    if booking.status not in {"in_progress", "awaiting_confirmation", "completed", "cancelled"}:
        conflict("A complaint requires work to have started or a cancelled booking.")
    if booking.complaint:
        conflict("This booking already has a complaint.")
    record = m.Complaint(booking_id=booking.id, reason=data.reason)
    db.add(record)
    db.flush()
    db.add(
        m.AuditEvent(
            actor_id=user.id,
            action="complaint.created",
            record_id=record.id,
            details={"bookingId": booking.id, "reason": data.reason},
        )
    )
    notify(
        db,
        booking.worker.user_id,
        "A customer submitted a complaint for review.",
        f"/worker/jobs/{booking.id}",
    )
    for admin_id in db.scalars(select(m.User.id).where(m.User.role == "admin")):
        notify(
            db,
            admin_id,
            "A complaint needs review.",
            f"/admin/records?entity=complaints&recordId={record.id}",
        )
    db.commit()
    db.refresh(record)
    return record


def resolve_complaint(db, user, complaint_id, data):
    from app.services import booking_record, notify

    require_role(user, "admin")
    record = db.get(m.Complaint, complaint_id)
    if record is None:
        missing()
    booking = booking_record(db, user, record.booking_id, lock=True)
    db.refresh(record, with_for_update=True)
    if record.status != "pending":
        conflict("This complaint has already been reviewed.")
    if user.id in {booking.customer_id, booking.worker.user_id}:
        conflict("A booking participant cannot adjudicate this complaint.")
    record.status, record.resolution = data.status, data.resolution
    record.reviewed_by, record.reviewed_at = user.id, m.utcnow()
    db.add(
        m.AuditEvent(
            actor_id=user.id,
            action="complaint.reviewed",
            record_id=record.id,
            details={"status": data.status, "resolution": data.resolution},
        )
    )
    for recipient, area in (
        (booking.customer_id, "customer/bookings"),
        (booking.worker.user_id, "worker/jobs"),
    ):
        notify(
            db,
            recipient,
            f"Complaint {data.status}: {data.resolution[:350]}",
            f"/{area}/{booking.id}",
        )
    db.commit()
    return record


def history_features(bookings):
    from app.evidence import summary

    features = summary(bookings)["features"]
    return {
        key: features[key]
        for key in ("late_rate_before", "cancellation_rate_before", "complaint_rate_before")
    }


def evaluation(db):
    from app.training_data import dataset

    exported = dataset(db)
    groups = defaultdict(list)
    excluded = Counter(exported["excluded"])
    for row in exported["rows"]:
        if row["probability"] is None or not row["model_version"]:
            excluded["noVersionedPrediction"] += 1
            continue
        groups[row["model_version"]].append((row["probability"], row["completed_on_time"]))
    results = []
    for version, rows in sorted(groups.items()):
        n = len(rows)
        results.append(
            {
                "modelVersion": version,
                "sampleCount": n,
                "onTimeRate": sum(y for _, y in rows) / n,
                "accuracyAtHalf": sum((p >= 0.5) == bool(y) for p, y in rows) / n,
                "brierScore": sum((p - y) ** 2 for p, y in rows) / n,
                "calibration": [
                    {
                        "lower": lo / 5,
                        "upper": (lo + 1) / 5,
                        "count": len(bucket),
                        "meanPrediction": sum(p for p, _ in bucket) / len(bucket)
                        if bucket
                        else None,
                        "observedOnTimeRate": sum(y for _, y in bucket) / len(bucket)
                        if bucket
                        else None,
                    }
                    for lo in range(5)
                    for bucket in [[(p, y) for p, y in rows if min(int(p * 5), 4) == lo]]
                ],
            }
        )
    return {
        "target": "Customer-confirmed completion reported on or before the agreed deadline",
        "featureVersion": exported["featureVersion"],
        "trainingReadiness": exported["readiness"],
        "sampleCount": sum(len(rows) for rows in groups.values()),
        "models": results,
        "excluded": dict(excluded),
        "limitations": "Only prospectively enrolled real bookings with compatible original snapshots are evaluated. Demo/test records and cancellations are excluded. Small samples and completed-job selection limit conclusions. Retraining creates a separate candidate; it never automatically replaces the active model.",
    }
