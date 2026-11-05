from collections.abc import Callable
from math import ceil

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app import evidence, location, profile_review
from app import models as m
from app import schemas as s
from app import serializers as out
from app.ai_client import AIServiceError, classify_text, recommend_workers
from app.auth import own_worker, require_role
from app.catalog import CATEGORY_LABELS
from app.config import Settings
from app.errors import ApiError, conflict, invalid, missing


def category_by_label(db: Session, label: str | None) -> m.Category | None:
    if label is None:
        return None
    record = db.scalar(select(m.Category).where(m.Category.label == label))
    if record is None or label not in CATEGORY_LABELS:
        invalid("category", "Select Plumbing, Electrical, Carpentry, or Welding.")
    return record


def page_result(db: Session, statement, serializer: Callable, page: int, per_page: int) -> dict:
    total = db.scalar(select(func.count()).select_from(statement.order_by(None).subquery())) or 0
    records = db.scalars(statement.offset((page - 1) * per_page).limit(per_page)).all()
    return {
        "data": [serializer(record) for record in records],
        "meta": {
            "page": page,
            "perPage": per_page,
            "total": total,
            "lastPage": max(1, ceil(total / per_page)),
        },
    }


def complete_worker_query():
    return (
        select(m.Worker)
        .join(m.User, m.User.id == m.Worker.user_id)
        .where(
            m.Worker.rate_lkr.is_not(None),
            m.Worker.services.any(),
            m.Worker.towns.any(),
            func.length(m.Worker.bio) >= 15,
        )
    )


def worker_query(
    category: str | None = None,
    town: str | None = None,
    available: bool | None = None,
    max_rate=None,
    search: str | None = None,
):
    statement = complete_worker_query().where(m.Worker.verified.is_(True))
    if category:
        statement = statement.where(
            m.Worker.services.any(m.WorkerCategory.category.has(m.Category.label == category))
        )
    if town:
        statement = statement.where(
            m.Worker.towns.any(m.WorkerTown.town_key == town.strip().casefold())
        )
    if available is not None:
        statement = statement.where(m.Worker.available == available)
    if max_rate is not None:
        statement = statement.where(m.Worker.rate_lkr <= max_rate)
    if search:
        needle = search.strip().casefold()
        statement = statement.where(
            func.lower(m.User.name).contains(needle, autoescape=True)
            | m.Worker.services.any(
                m.WorkerCategory.category.has(
                    func.lower(m.Category.label).contains(needle, autoescape=True)
                )
            )
        )
    return statement.order_by(func.lower(m.User.name), m.Worker.id)


def request_record(
    db: Session, user: m.User, record_id: str, lock: bool = False
) -> m.ServiceRequest:
    require_role(user, "customer", "admin")
    statement = select(m.ServiceRequest).where(m.ServiceRequest.id == record_id)
    if user.role == "customer":
        statement = statement.where(m.ServiceRequest.customer_id == user.id)
    if lock:
        statement = statement.with_for_update()
    record = db.scalar(statement)
    if record is None:
        missing()
    return record


def booking_query(user: m.User, db: Session):
    statement = select(m.Booking)
    if user.role == "customer":
        statement = statement.where(m.Booking.customer_id == user.id)
    elif user.role == "worker":
        worker = own_worker(db, user)
        statement = statement.where(m.Booking.worker_id == worker.id)
    return statement


def booking_record(db: Session, user: m.User, record_id: str, lock: bool = False) -> m.Booking:
    statement = booking_query(user, db).where(m.Booking.id == record_id)
    record = db.scalar(statement)
    if record is None:
        missing()
    if lock:
        # Every booking write locks the request first, then booking, then worker.
        db.scalar(
            select(m.ServiceRequest)
            .where(m.ServiceRequest.id == record.request_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        record = db.scalar(statement.with_for_update().execution_options(populate_existing=True))
    return record


def review_fields(worker: m.Worker) -> dict:
    return profile_review.snapshot(worker)


def patch_worker(db: Session, user: m.User, data: s.WorkerPatch) -> m.Worker:
    record = own_worker(db, user, lock=True)
    before = review_fields(record)
    was_ready = record.review_ready
    was_approved = record.verified
    corrections_requested = not record.verified and bool(record.review_note)
    values = data.model_dump(exclude_unset=True)
    if "categories" in values:
        labels = list(dict.fromkeys(values.pop("categories")))
        categories = [category_by_label(db, label) for label in labels]
        existing = {entry.category_id: entry for entry in record.services}
        record.services = [
            existing.get(category.id) or m.WorkerCategory(category=category)
            for category in categories
        ]
    if "service_towns" in values:
        towns = {town.casefold(): town for town in values.pop("service_towns")}
        existing = {entry.town_key: entry for entry in record.towns}
        record.towns = [
            existing.get(key) or m.WorkerTown(town_key=key, town=town)
            for key, town in towns.items()
        ]
    for key, value in values.items():
        setattr(
            user if key in {"name", "town", "phone", "contact_preference"} else record, key, value
        )
    if record.available and not record.review_ready:
        invalid(
            "available",
            "Complete your biography, services, service towns, and rate before becoming available.",
        )
    changed = profile_review.changes(before, review_fields(record))
    if changed and record.review_baseline is None:
        record.review_baseline = before
    if (record.verified and changed) or (corrections_requested and record.review_ready):
        record.verified = False
        record.review_note = None
        db.add(
            m.AuditEvent(
                actor_id=user.id,
                action="worker.review_resubmitted",
                record_id=record.id,
                details={"reason": "Profile saved for administrator review."},
            )
        )
    if (
        record.review_ready
        and not record.verified
        and (not was_ready or corrections_requested or was_approved or changed)
    ):
        prefix = (
            "Worker application resubmitted: "
            if corrections_requested or was_approved
            else (
                "Worker application updated: "
                if was_ready
                else "Worker application ready for review: "
            )
        )
        fields = changed if was_ready else profile_review.pending_changes(record)
        summary = (
            "Changed: " + ", ".join(item["label"] for item in fields)
            if fields
            else "No approval fields changed."
        )
        message = prefix + user.name + ". " + summary
        for admin_id in db.scalars(select(m.User.id).where(m.User.role == "admin")):
            notify(
                db,
                admin_id,
                message,
                f"/admin/records?entity=workers&recordId={record.id}&detailTab=changes",
            )
    db.commit()
    db.refresh(record)
    return record


def create_request(db: Session, user: m.User, data: s.RequestCreate) -> m.ServiceRequest:
    require_role(user, "customer")
    values = data.model_dump(exclude={"category"})
    record = m.ServiceRequest(
        **values, customer_id=user.id, category=category_by_label(db, data.category)
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def patch_request(
    db: Session, user: m.User, record_id: str, data: s.RequestPatch
) -> m.ServiceRequest:
    require_role(user, "customer")
    record = request_record(db, user, record_id, lock=True)
    if record.status != "submitted":
        conflict("Only an unbooked request can be edited.")
    values = data.model_dump(exclude_unset=True)
    if any(
        key in values and values[key] != getattr(record, key)
        for key in ("title", "description")
    ):
        values["category"] = None
    if "category" in values:
        record.category = category_by_label(db, values.pop("category"))
    for key, value in values.items():
        setattr(record, key, value)
    db.commit()
    db.refresh(record)
    return record


def notify(db: Session, user_id: str, message: str, path: str) -> None:
    db.add(m.Notification(user_id=user_id, message=message, target_path=path))


def ensure_worker_time_available(
    db, worker_id, start, end, exclude_id=None, error_field="scheduledAt"
):
    # Call only while holding this worker's row lock, so concurrent requests serialize.
    existing_end = func.coalesce(m.Booking.scheduled_end_at, m.Booking.deadline_at)
    statement = select(m.Booking.id).where(
        m.Booking.worker_id == worker_id,
        m.Booking.status.in_(("pending", "accepted", "in_progress", "awaiting_confirmation")),
        or_(existing_end.is_(None), existing_end > start),
    )
    if end is not None:
        statement = statement.where(m.Booking.scheduled_at < end)
    if exclude_id is not None:
        statement = statement.where(m.Booking.id != exclude_id)
    if db.scalar(statement.limit(1)) is not None:
        message = (
            "This worker already has a booking during this time. "
            "Choose another start/end time or another professional."
        )
        raise ApiError(409, "booking_time_conflict", message, {error_field: [message]})


def create_booking(
    db: Session, user: m.User, data: s.BookingCreate, settings: Settings
) -> m.Booking:
    require_role(user, "customer")
    request = request_record(db, user, data.request_id, lock=True)
    if request.status != "submitted":
        conflict("This request already has an active or completed booking.")
    if request.category_id is None:
        invalid("requestId", "Select a service category before booking.")
    worker = db.scalar(select(m.Worker).where(m.Worker.id == data.worker_id).with_for_update())
    if worker is None:
        missing()
    if not worker.verified:
        conflict("This worker is awaiting administrator approval and cannot receive new bookings.")
    if (
        not worker.available
        or worker.rate_lkr is None
        or not any(service.category_id == request.category_id for service in worker.services)
        or not location.match(worker, request)[0]
    ):
        invalid(
            "workerId",
            "This worker must be available, offer the category, and cover your job location.",
        )
    ensure_worker_time_available(db, worker.id, data.scheduled_at, data.scheduled_end_at)
    record = m.Booking(
        request_id=request.id,
        customer_id=user.id,
        worker_id=worker.id,
        scheduled_at=data.scheduled_at,
        scheduled_end_at=data.scheduled_end_at,
        deadline_at=data.deadline_at,
        quoted_rate_lkr=worker.rate_lkr,
        rate_unit=worker.rate_unit,
    )
    sources = set(
        db.scalars(
            select(m.User.data_source)
            .where(m.User.id.in_([user.id, worker.user_id]))
            .order_by(m.User.id)
            .with_for_update()
        )
    )
    db.refresh(worker.user)
    db.refresh(user)
    db.expire(worker, ["bookings"])
    record.data_source = (
        "demo" if "demo" in sources else ("real" if sources == {"real"} else "test")
    )
    inputs = worker_features(db, [worker], request.category_id, request)
    snapshot = {
        "inputs": inputs[0],
        "featureVersion": evidence.FEATURE_VERSION,
        "dataSource": record.data_source,
        "predictedAt": m.utcnow().isoformat(),
        "probability": None,
        "modelVersion": None,
    }
    if settings.ai_enabled:
        try:
            result = recommend_workers(
                settings.ai_base_url, settings.ai_timeout_seconds, inputs, top_k=1
            )
            snapshot.update(
                probability=result.recommendations[0].reliability_probability,
                modelVersion=result.model_version,
            )
        except AIServiceError:
            pass
    record.prediction = snapshot
    db.add(record)
    db.flush()
    db.add(m.BookingEvent(booking_id=record.id, actor_id=user.id, status="pending"))
    request.status = "booked"
    notify(db, worker.user_id, f"New booking: {request.title}", f"/worker/jobs/{record.id}")
    db.commit()
    db.refresh(record)
    return record


def transition_booking(
    db: Session, user: m.User, record_id: str, data: s.BookingTransition
) -> m.Booking:
    require_role(user, "customer", "worker")
    record = booking_record(db, user, record_id, lock=True)
    allowed = (
        {
            "pending": {"cancelled"},
            "accepted": {"cancelled"},
            "in_progress": {"cancelled"},
            "awaiting_confirmation": {"completed", "in_progress"},
        }
        if user.role == "customer"
        else {
            "pending": {"accepted", "rejected"},
            "accepted": {"in_progress", "cancelled"},
            "in_progress": {"awaiting_confirmation", "cancelled"},
        }
    )
    if data.status not in allowed.get(record.status, set()):
        conflict("This booking transition is not allowed for its current status and your role.")
    if (
        data.status == "cancelled"
        or (record.status == "awaiting_confirmation" and data.status == "in_progress")
    ) and (not data.note or len(data.note) < 5):
        invalid("note", "Provide a reason of at least five characters.")
    if data.status in {"accepted", "in_progress"}:
        db.scalar(select(m.Worker.id).where(m.Worker.id == record.worker_id).with_for_update())
        ensure_worker_time_available(
            db,
            record.worker_id,
            record.scheduled_at,
            record.scheduled_end_at or record.deadline_at,
            exclude_id=record.id,
            error_field="note",
        )
    if data.status == "awaiting_confirmation":
        record.reported_completed_at = m.utcnow()
    if record.status == "awaiting_confirmation" and data.status == "in_progress":
        record.reported_completed_at = None
    if data.status == "completed":
        record.confirmed_at = m.utcnow()
    if data.status == "cancelled":
        record.cancelled_by_role = user.role
    record.status = data.status
    db.add(
        m.BookingEvent(booking_id=record.id, actor_id=user.id, status=data.status, note=data.note)
    )
    if data.status in {"rejected", "cancelled"}:
        record.request.status = "submitted"
    elif data.status == "completed":
        record.request.status = "closed"
        db.scalar(select(m.Worker).where(m.Worker.id == record.worker_id).with_for_update())
        metric = db.scalar(
            select(m.WorkerMetric)
            .where(
                m.WorkerMetric.worker_id == record.worker_id,
                m.WorkerMetric.category_id == record.request.category_id,
            )
            .with_for_update(of=m.WorkerMetric)
            .execution_options(populate_existing=True)
        )
        if metric is None:
            metric = m.WorkerMetric(
                worker_id=record.worker_id, category_id=record.request.category_id, completed_jobs=0
            )
            db.add(metric)
        metric.completed_jobs += 1
    recipient = record.worker.user_id if user.role == "customer" else record.customer_id
    path = (
        f"/worker/jobs/{record.id}"
        if user.role == "customer"
        else f"/customer/bookings/{record.id}"
    )
    notify(db, recipient, f"Booking {data.status.replace('_', ' ')}: {record.request.title}", path)
    db.commit()
    db.refresh(record)
    return record


def review_booking(db: Session, user: m.User, record_id: str, data: s.ReviewCreate) -> m.Review:
    require_role(user, "customer")
    booking = booking_record(db, user, record_id, lock=True)
    if booking.status != "completed":
        conflict("You can review only a completed booking.")
    if booking.review is not None:
        conflict("This booking already has a review.")
    worker = db.scalar(
        select(m.Worker)
        .where(m.Worker.id == booking.worker_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    record = m.Review(
        booking_id=booking.id,
        customer_id=user.id,
        worker_id=worker.id,
        rating=data.rating,
        comment=data.comment,
    )
    db.add(record)
    worker.review_count += 1
    worker.rating_total += data.rating
    notify(
        db, worker.user_id, f"New review for: {booking.request.title}", f"/worker/jobs/{booking.id}"
    )
    db.commit()
    db.refresh(record)
    return record


def recommendations(
    db: Session,
    user: m.User,
    record_id: str,
    filters: s.RecommendationFilters,
    settings: Settings,
) -> dict:
    require_role(user, "customer")
    request = request_record(db, user, record_id, lock=True)
    if request.status != "submitted":
        conflict("Recommendations are available only for an unbooked request.")
    if request.category is None:
        invalid("category", "Choose a category or request automatic classification first.")
    statement = worker_query(request.category.label, None, filters.available, filters.max_rate)
    workers = [
        worker for worker in db.scalars(statement).all() if location.match(worker, request)[0]
    ]
    workers.sort(
        key=lambda worker: (
            location.match(worker, request)[1] is None,
            location.match(worker, request)[1] or 0,
            worker.user.name.casefold(),
            worker.id,
        )
    )
    workers = workers[:50]
    fallback_reason = "AI ranking is disabled." if not settings.ai_enabled else None
    if settings.ai_enabled and workers:
        inputs = worker_features(db, workers, request.category_id, request)
        try:
            prediction = recommend_workers(
                settings.ai_base_url, settings.ai_timeout_seconds, inputs, top_k=len(workers)
            )
        except AIServiceError:
            fallback_reason = "AI ranking is temporarily unavailable; showing service matches."
        else:
            by_id = {worker.id: worker for worker in workers}
            result = {
                "requestId": request.id,
                "category": request.category.label,
                "source": "model",
                "recommendations": [],
            }
            for rank, entry in enumerate(prediction.recommendations, start=1):
                worker = by_id[entry.worker_id]
                result["recommendations"].append(
                    {
                        "workerId": worker.id,
                        **location.details(worker, request),
                        "rank": rank,
                        "source": "model",
                        "matchScore": entry.recommendation_score,
                        "categorySkillScore": entry.skill_score,
                        "reliabilityProbability": entry.reliability_probability,
                        "reliabilityPercentage": entry.reliability_percentage,
                        "coldStart": entry.cold_start,
                        "imputedFeatures": entry.imputed_features,
                        "missingScoringFeatures": entry.missing_scoring_features,
                        "reasons": evidence.reasons(
                            worker,
                            request.category_id,
                            request.category.label,
                            request.town,
                            location.explanation(worker, request),
                        ),
                        "evidence": evidence.category_summary(worker, request.category_id),
                        "dataSource": worker.user.data_source,
                        "featureVersion": evidence.FEATURE_VERSION,
                        "worker": out.worker(worker),
                    }
                )
            db.add(
                m.AuditEvent(
                    actor_id=user.id,
                    action="request.recommendations",
                    record_id=request.id,
                    details={
                        "source": "model",
                        "candidates": len(workers),
                        "model_type": "reliability_rf",
                        "scoring_version": "weighted-v2",
                        "category": request.category.label,
                        "town": request.town,
                        "filters": filters.model_dump(mode="json"),
                        "inputs": inputs,
                        "result": result,
                    },
                )
            )
            db.commit()
            return result
    result = {
        "requestId": request.id,
        "category": request.category.label,
        "source": "rule_based",
        "fallbackReason": fallback_reason,
        "recommendations": [
            {
                "workerId": worker.id,
                **location.details(worker, request),
                "rank": rank,
                "source": "rule_based",
                "matchScore": None,
                "categorySkillScore": None,
                "reliabilityProbability": None,
                "dataSource": worker.user.data_source,
                "evidence": evidence.category_summary(worker, request.category_id),
                "reasons": evidence.reasons(
                    worker,
                    request.category_id,
                    request.category.label,
                    request.town,
                    location.explanation(worker, request),
                )
                + [
                    "Nearest known locations first, then town-only matches; not an AI ranking"
                    if request.latitude is not None
                    else "Alphabetical order among eligible workers; not an AI ranking",
                ],
                "worker": out.worker(worker),
            }
            for rank, worker in enumerate(workers, start=1)
        ],
    }
    db.add(
        m.AuditEvent(
            actor_id=user.id,
            action="request.recommendations",
            record_id=request.id,
            details={
                "source": "rule_based",
                "candidates": len(workers),
                "reason": fallback_reason,
                "category": request.category.label,
                "town": request.town,
                "result": result,
            },
        )
    )
    db.commit()
    return result


def unavailable_classifier() -> None:
    raise ApiError(
        503,
        "model_unavailable",
        "Automatic classification is unavailable. Select a service category manually.",
    )


def classify_request(db: Session, user: m.User, record_id: str, settings: Settings) -> dict:
    require_role(user, "customer")
    record = request_record(db, user, record_id, lock=True)
    if record.status != "submitted":
        conflict("Only an unbooked request can be classified.")
    if record.category is not None:
        return {"category": record.category.label, "source": "existing", "classified": False}
    if not settings.ai_enabled:
        unavailable_classifier()
    try:
        prediction = classify_text(
            settings.ai_base_url,
            settings.ai_timeout_seconds,
            f"{record.title}\n{record.description}",
        )
    except AIServiceError:
        unavailable_classifier()
    record.category = category_by_label(db, prediction.category)
    db.add(
        m.AuditEvent(
            actor_id=user.id,
            action="request.classified",
            record_id=record.id,
            details={
                "predicted_category": prediction.category,
                "model_type": "nlp_svm",
                "title": record.title,
                "description": record.description,
                "source": "model",
                "confidence": None,
            },
        )
    )
    db.commit()
    return {
        "category": prediction.category,
        "source": "model",
        "classified": True,
        "modelType": "nlp_svm",
        "confidence": None,
    }


def worker_features(
    db: Session,
    workers: list[m.Worker],
    category_id: str | None,
    request: m.ServiceRequest | None = None,
) -> list[dict]:
    return [
        {
            **evidence.inputs(worker, category_id),
            "distance_km": location.match(worker, request)[1] if request is not None else None,
        }
        for worker in workers
    ]


def predicted_profile(db: Session, worker: m.Worker, settings: Settings) -> dict:
    profile = out.worker(worker)
    profile.update(
        modelStatus="disabled" if not settings.ai_enabled else "unavailable",
        coldStart=not evidence.summary(evidence.cohort(worker))["completedJobs"],
        imputedFeatures=[],
        missingScoringFeatures=[],
    )
    if not settings.ai_enabled or not worker.services:
        return profile
    inputs = []
    metrics = {
        service.category.label: evidence.category_summary(worker, service.category_id)[
            "completedJobs"
        ]
        for service in worker.services
    }
    for service in worker.services:
        inputs.append(
            {
                **evidence.inputs(worker, service.category_id),
                "worker_id": service.category_id,
                "completed_jobs": metrics.get(service.category.label, 0),
            }
        )
    try:
        prediction = recommend_workers(
            settings.ai_base_url, settings.ai_timeout_seconds, inputs, top_k=len(inputs)
        )
    except AIServiceError:
        return profile
    by_id = {entry.worker_id: entry for entry in prediction.recommendations}
    first = prediction.recommendations[0]
    profile.update(
        modelStatus="available",
        reliabilityProbability=first.reliability_probability,
        coldStart=first.cold_start,
        imputedFeatures=first.imputed_features,
        missingScoringFeatures=first.missing_scoring_features,
    )
    profile["performance"] = [
        {
            "category": service.category.label,
            "completedJobs": metrics.get(service.category.label, 0),
            "skillScore": by_id[service.category_id].skill_score,
            "evidence": evidence.category_summary(worker, service.category_id),
        }
        for service in worker.services
    ]
    return profile
