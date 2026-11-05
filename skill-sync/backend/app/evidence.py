"""Recorded features shared by serving and immutable prospective training snapshots."""

import json
from datetime import UTC
from pathlib import Path

CONTRACT = json.loads(
    (Path(__file__).resolve().parents[3] / "skillsync-ai-model/feature_contract.json").read_text()
)
FEATURE_VERSION = CONTRACT["version"]
FEATURES = CONTRACT["features"]


def aware(value):
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


def cohort(worker):
    return [b for b in worker.bookings if b.data_source == worker.user.data_source]


def confirmed(bookings):
    return [
        b
        for b in bookings
        if b.status == "completed" and b.confirmed_at and b.reported_completed_at
    ]


def summary(bookings):
    done = confirmed(bookings)
    timed = [b for b in done if b.deadline_at]
    terminal = done + [
        b for b in bookings if b.status == "cancelled" and b.cancelled_by_role == "worker"
    ]
    adjudicated = [b for b in terminal if not b.complaint or b.complaint.status != "pending"]
    reviews = [b.review.rating for b in done if b.review]
    times = []
    for b in bookings:
        event = next((e for e in b.history if e.status in {"accepted", "rejected"}), None)
        if event:
            minutes = (aware(event.at) - aware(b.created_at)).total_seconds() / 60
            if minutes >= 0:
                times.append(minutes)
    late = sum(aware(b.reported_completed_at) > aware(b.deadline_at) for b in timed)
    cancelled = sum(b.status == "cancelled" for b in terminal)
    upheld = sum(bool(b.complaint and b.complaint.status == "upheld") for b in adjudicated)
    return {
        "completedJobs": len(done),
        "reviewCount": len(reviews),
        "rating": sum(reviews) / len(reviews) if reviews else None,
        "timedJobs": len(timed),
        "onTimeJobs": len(timed) - late,
        "workerCancellations": cancelled,
        "terminalJobs": len(terminal),
        "upheldComplaints": upheld,
        "adjudicatedJobs": len(adjudicated),
        "pendingComplaints": sum(
            bool(b.complaint and b.complaint.status == "pending") for b in terminal
        ),
        "features": {
            "completed_jobs_before": len(done),
            "cancellation_rate_before": cancelled / len(terminal) if terminal else None,
            "late_rate_before": late / len(timed) if timed else None,
            "avg_response_minutes_before": sum(times) / len(times) if times else None,
            "avg_rating_before": sum(reviews) / len(reviews) if reviews else None,
            "complaint_rate_before": upheld / len(adjudicated) if adjudicated else None,
        },
    }


def category_summary(worker, category_id):
    return summary(
        [b for b in cohort(worker) if category_id is None or b.request.category_id == category_id]
    )


def inputs(worker, category_id):
    overall = summary(cohort(worker))
    category = category_summary(worker, category_id)
    return {
        "worker_id": worker.id,
        "name": worker.user.name,
        "experience_years": worker.years_experience,
        "completed_jobs": category["completedJobs"],
        "rating": category["rating"],
        "complaint_rate": category["features"]["complaint_rate_before"],
        "certified": None,
        "available": worker.available,
        "distance_km": None,
        **overall["features"],
    }


def reasons(worker, category_id, label, town, location_reason=None):
    evidence = category_summary(worker, category_id)
    rows = [
        f"Offers {label}",
        location_reason or f"Serves {town}",
        "Available for new jobs" if worker.available else "Currently unavailable",
        f"{evidence['completedJobs']} customer-confirmed {label} jobs in {worker.user.data_source} history.",
    ]
    if evidence["reviewCount"]:
        rows.append(
            f"{label} rating {evidence['rating']:.2f}/5 from {evidence['reviewCount']} recorded reviews."
        )
    else:
        rows.append(f"No recorded {label} reviews yet; category quality is not established.")
    if evidence["timedJobs"]:
        rows.append(
            f"{evidence['onTimeJobs']} of {evidence['timedJobs']} confirmed {label} jobs reported on time."
        )
    if evidence["adjudicatedJobs"]:
        rows.append(
            f"{evidence['upheldComplaints']} upheld complaints across {evidence['adjudicatedJobs']} eligible {label} outcomes; pending complaints excluded."
        )
    rows.append(
        "Skill score is a weighted formula; experience is self-reported. These records explain the match, not individual model feature contributions."
    )
    if worker.user.data_source != "real":
        rows.append(
            "Demo/test history: this is a testing estimate, not verified real-world performance."
        )
    return rows
