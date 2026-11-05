from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import evidence, profile_review
from app import models as m


def aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def identity(db: Session, user: m.User) -> dict:
    worker_id = db.scalar(select(m.Worker.id).where(m.Worker.user_id == user.id))
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "workerId": worker_id,
        "town": user.town,
        "phone": user.phone,
        "contactPreference": user.contact_preference,
        "dataSource": user.data_source,
    }


def category(value: m.Category) -> dict:
    return {
        "id": value.id,
        "label": value.label,
        "slug": value.slug,
        "icon": value.icon,
        "description": value.description,
        "exampleRequest": value.example_request,
    }


def worker(value: m.Worker, *, private: bool = False) -> dict:
    observed = evidence.summary(evidence.cohort(value))
    metrics = {
        service.category.label: evidence.category_summary(value, service.category_id)[
            "completedJobs"
        ]
        for service in value.services
    }
    labels = sorted(service.category.label for service in value.services)
    return {
        "id": value.id,
        "name": value.user.name,
        "town": value.user.town,
        "serviceTowns": sorted(town.town for town in value.towns),
        "latitude": value.latitude if private else None,
        "longitude": value.longitude if private else None,
        "serviceRadiusKm": value.service_radius_km,
        "categories": labels,
        "bio": value.bio,
        "yearsExperience": value.years_experience,
        "rateLkr": float(value.rate_lkr) if value.rate_lkr is not None else None,
        "rateUnit": value.rate_unit,
        "available": value.available,
        "rating": round(observed["rating"], 2) if observed["rating"] is not None else None,
        "reviewCount": observed["reviewCount"],
        "dataSource": value.user.data_source,
        "evidence": observed,
        "reliabilityProbability": None,
        "verified": value.verified,
        "approvalStatus": "approved"
        if value.verified
        else ("changes_requested" if value.review_note else "pending"),
        "reviewNote": value.review_note if private else None,
        "reviewReady": value.review_ready,
        "profileChanges": profile_review.pending_changes(value) if private else [],
        "performance": [
            {
                "category": label,
                "skillScore": None,
                "completedJobs": metrics.get(label, 0),
                "evidence": evidence.category_summary(
                    value,
                    next(
                        (x.category_id for x in value.services if x.category.label == label), None
                    ),
                ),
            }
            for label in sorted(set(labels) | metrics.keys())
        ],
    }


def service_request(value: m.ServiceRequest) -> dict:
    return {
        "id": value.id,
        "customerId": value.customer_id,
        "title": value.title,
        "description": value.description,
        "town": value.town,
        "address": value.address,
        "latitude": value.latitude,
        "longitude": value.longitude,
        "preferredAt": aware(value.preferred_at),
        "budgetLkr": float(value.budget_lkr) if value.budget_lkr is not None else None,
        "category": value.category.label if value.category else None,
        "status": value.status,
        "createdAt": aware(value.created_at),
    }


def review(value: m.Review) -> dict:
    return {
        "id": value.id,
        "bookingId": value.booking_id,
        "customerId": value.customer_id,
        "workerId": value.worker_id,
        "rating": value.rating,
        "comment": value.comment,
        "createdAt": aware(value.created_at),
    }


def booking(value: m.Booking) -> dict:
    return {
        "id": value.id,
        "requestId": value.request_id,
        "customerId": value.customer_id,
        "workerId": value.worker_id,
        "scheduledAt": aware(value.scheduled_at),
        "scheduledEndAt": aware(value.scheduled_end_at),
        "dataSource": value.data_source,
        "deadlineAt": aware(value.deadline_at),
        "reportedCompletedAt": aware(value.reported_completed_at),
        "confirmedAt": aware(value.confirmed_at),
        "cancelledByRole": value.cancelled_by_role,
        "complaint": complaint(value.complaint) if value.complaint else None,
        "status": value.status,
        "quotedRateLkr": float(value.quoted_rate_lkr),
        "rateUnit": value.rate_unit,
        "history": [
            {"status": event.status, "at": aware(event.at), "note": event.note}
            for event in value.history
        ],
        "request": service_request(value.request),
        "worker": worker(value.worker),
        "review": review(value.review) if value.review else None,
    }


def complaint(value: m.Complaint) -> dict:
    return {
        "id": value.id,
        "bookingId": value.booking_id,
        "reason": value.reason,
        "status": value.status,
        "resolution": value.resolution,
        "reviewedBy": value.reviewed_by,
        "reviewedAt": aware(value.reviewed_at),
        "createdAt": aware(value.created_at),
    }


def notification(value: m.Notification) -> dict:
    target = value.target_path
    if target.startswith("/admin/records?entity=workers&recordId=") and "&detailTab=" not in target:
        target += "&detailTab=changes"
    return {
        "id": value.id,
        "userId": value.user_id,
        "message": value.message,
        "targetPath": target,
        "createdAt": aware(value.created_at),
        "readAt": aware(value.read_at),
    }
