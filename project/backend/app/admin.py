from typing import Literal

from fastapi import APIRouter, Request
from sqlalchemy import func, select

from app import models as m
from app import profile_review
from app import schemas as s
from app import serializers as out
from app.auth import Admin, Db
from app.errors import missing, conflict
from app.routes import PageNumber, PageSize
from app.services import page_result, notify, complete_worker_query
from app.ai_client import get_health
from app.outcomes import evaluation, resolve_complaint

router = APIRouter(prefix="/api/v1/admin", tags=["Administration"])
Entity = Literal[
    "workers", "customers", "categories", "requests", "bookings", "reviews", "complaints"
]
MODELS = {
    "complaints": m.Complaint,
    "workers": m.Worker,
    "customers": m.User,
    "categories": m.Category,
    "requests": m.ServiceRequest,
    "bookings": m.Booking,
    "reviews": m.Review,
}


def entity_query(entity: Entity):
    model = MODELS[entity]
    statement = select(model)
    if entity == "customers":
        statement = statement.where(m.User.role == "customer")
    return statement.order_by(model.id)


def serialize(entity: Entity, db: Db, record):
    serializers = {
        "complaints": out.complaint,
        "workers": lambda value: out.worker(value, private=True),
        "categories": out.category,
        "requests": out.service_request,
        "bookings": out.booking,
        "reviews": out.review,
        "customers": lambda value: out.identity(db, value),
    }
    return serializers[entity](record)


@router.get("/dashboard", response_model=s.Envelope[dict])
def dashboard(admin: Admin, db: Db, request: Request):
    settings = request.app.state.settings
    health = (
        get_health(settings.ai_base_url, min(settings.ai_timeout_seconds, 3))
        if settings.ai_enabled
        else {}
    )
    models = health.get("models", {})
    counts = {
        entity: db.scalar(select(func.count()).select_from(entity_query(entity).subquery()))
        for entity in MODELS
    }
    return {
        "data": {
            "counts": counts,
            "pendingApplications": db.scalar(
                select(func.count()).select_from(
                    complete_worker_query()
                    .where(m.Worker.verified.is_(False), m.Worker.review_note.is_(None))
                    .subquery()
                )
            ),
            "evaluation": evaluation(db),
            "models": {
                "trainingContract": health.get("training_contract_status", "unavailable"),
                "classification": "available" if models.get("classification") else "unavailable",
                "recommendations": "model" if models.get("reliability") else "rule_based",
                "performance": "available" if models.get("reliability") else "unavailable",
            },
        }
    }


@router.get("/model-evaluation", response_model=s.Envelope[dict])
def model_evaluation(admin: Admin, db: Db):
    return {"data": evaluation(db)}


@router.get("/training-dataset", response_model=s.Envelope[dict])
def training_dataset(admin: Admin, db: Db):
    from app.training_data import dataset

    return {"data": dataset(db)}


@router.patch("/complaints/{complaint_id}/resolution", response_model=s.Envelope[dict])
def review_complaint(complaint_id: str, data: s.ComplaintResolution, admin: Admin, db: Db):
    return {"data": out.complaint(resolve_complaint(db, admin, complaint_id, data))}


@router.patch("/data-sources/{entity}/{record_id}", response_model=s.Envelope[dict])
def data_source(
    entity: Literal["workers", "customers"],
    record_id: str,
    data: s.DataSourcePatch,
    admin: Admin,
    db: Db,
):
    record = db.scalar(entity_query(entity).where(MODELS[entity].id == record_id))
    if record is None:
        missing()
    user_id = record.user_id if entity == "workers" else record.id
    user = db.scalar(
        select(m.User)
        .where(m.User.id == user_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if user.data_source == "demo" and data.data_source != "demo":
        conflict("Demo identities cannot be promoted to real. Register a genuine account instead.")
    before = user.data_source
    user.data_source = data.data_source
    db.add(
        m.AuditEvent(
            actor_id=admin.id,
            action="account.data_source",
            record_id=user.id,
            details={
                "before": before,
                "after": data.data_source,
                "note": data.note,
                "scope": "Future bookings only; historical sources remain immutable.",
            },
        )
    )
    db.commit()
    db.refresh(record)
    return {"data": serialize(entity, db, record)}


@router.get("/{entity}", response_model=s.Page[dict])
def records(entity: Entity, admin: Admin, db: Db, page: PageNumber = 1, per_page: PageSize = 20):
    return page_result(
        db, entity_query(entity), lambda record: serialize(entity, db, record), page, per_page
    )


@router.get("/{entity}/{record_id}", response_model=s.Envelope[dict])
def details(entity: Entity, record_id: str, admin: Admin, db: Db):
    record = db.scalar(entity_query(entity).where(MODELS[entity].id == record_id))
    if record is None:
        missing()
    return {"data": serialize(entity, db, record)}


@router.patch("/categories/{category_id}", response_model=s.Envelope[s.CategoryView])
def update_category(category_id: str, data: s.CategoryPatch, admin: Admin, db: Db):
    record = db.scalar(select(m.Category).where(m.Category.id == category_id).with_for_update())
    if record is None:
        missing()
    before = out.category(record)
    record.description = data.description
    record.example_request = data.example_request
    db.add(
        m.AuditEvent(
            actor_id=admin.id,
            action="category.updated",
            record_id=record.id,
            details={"before": before, "after": out.category(record)},
        )
    )
    db.commit()
    return {"data": out.category(record)}


@router.patch("/workers/{worker_id}/verification", response_model=s.Envelope[s.WorkerView])
def verify_worker(worker_id: str, data: s.VerificationPatch, admin: Admin, db: Db):
    record = db.scalar(select(m.Worker).where(m.Worker.id == worker_id).with_for_update())
    if record is None:
        missing()
    before = record.verified
    if data.verified and not record.review_ready:
        conflict(
            "The worker must complete their biography, services, towns, and rate before approval."
        )
    reviewed_changes = profile_review.pending_changes(record)
    reviewed_profile = profile_review.snapshot(record)
    record.verified = data.verified
    record.review_note = data.note
    if data.verified:
        record.review_baseline = None
    db.add(
        m.AuditEvent(
            actor_id=admin.id,
            action="worker.verification",
            record_id=record.id,
            details={
                "before": before,
                "after": data.verified,
                "note": data.note,
                "profileChanges": reviewed_changes,
                "reviewedProfile": reviewed_profile,
            },
        )
    )
    notify(
        db,
        record.user_id,
        "Your profile is approved." if data.verified else "Profile changes requested: " + data.note,
        "/worker/profile",
    )
    db.commit()
    return {"data": out.worker(record, private=True)}
