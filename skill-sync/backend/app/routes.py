from typing import Annotated

from fastapi import APIRouter, Query, Request
from sqlalchemy import func, select

from app import models as m
from app import schemas as s
from app import serializers as out
from app import services
from app.auth import (
    CurrentUser,
    Db,
    issue_token,
    own_worker,
    password_hash,
    require_role,
    verify_password,
)
from app.errors import ApiError, conflict, missing

router = APIRouter(prefix="/api/v1")
PageNumber = Annotated[int, Query(ge=1, le=1000000)]
PageSize = Annotated[int, Query(ge=1, le=100, alias="perPage")]


@router.post(
    "/auth/register",
    response_model=s.Envelope[s.TokenResult],
    status_code=201,
    tags=["Authentication"],
)
def register(data: s.Register, db: Db, request: Request):
    if db.scalar(select(m.User.id).where(m.User.email == data.email)):
        conflict("An account already exists with that email address.")
    user = m.User(
        name=data.name,
        email=data.email,
        password_hash=password_hash.hash(data.password),
        role=data.role,
        town=data.town,
    )
    db.add(user)
    db.flush()
    if user.role == "worker":
        db.add(m.Worker(user_id=user.id))
        db.flush()
    result = issue_token(db, user, request.app.state.settings.token_ttl_minutes)
    db.commit()
    return {"data": result}


@router.post("/auth/login", response_model=s.Envelope[s.TokenResult], tags=["Authentication"])
def login(data: s.Login, db: Db, request: Request):
    user = db.scalar(select(m.User).where(m.User.email == data.email))
    if not verify_password(data.password, user):
        raise ApiError(401, "invalid_credentials", "Email or password is incorrect.")
    result = issue_token(db, user, request.app.state.settings.token_ttl_minutes)
    db.commit()
    return {"data": result}


@router.post("/auth/logout", response_model=s.Envelope[dict], tags=["Authentication"])
def logout(request: Request, user: CurrentUser, db: Db):
    token = db.get(m.AccessToken, request.state.token_digest)
    db.delete(token)
    db.commit()
    return {"data": {"message": "Signed out. This access token has been revoked."}}


@router.get("/me", response_model=s.Envelope[s.Identity], tags=["Profiles"])
def me(user: CurrentUser, db: Db):
    return {"data": out.identity(db, user)}


@router.patch("/me", response_model=s.Envelope[s.Identity], tags=["Profiles"])
def update_me(data: s.ProfilePatch, user: CurrentUser, db: Db):
    require_role(user, "customer")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(user, key, value)
    db.commit()
    return {"data": out.identity(db, user)}


@router.get("/categories", response_model=s.Envelope[list[s.CategoryView]], tags=["Categories"])
def categories(db: Db):
    return {
        "data": [
            out.category(record)
            for record in db.scalars(select(m.Category).order_by(m.Category.label))
        ]
    }


@router.get("/workers", response_model=s.Page[s.WorkerView], tags=["Workers"])
def workers(
    db: Db,
    page: PageNumber = 1,
    per_page: PageSize = 12,
    search: Annotated[str | None, Query(max_length=100)] = None,
    category: Annotated[str | None, Query(max_length=80)] = None,
    town: Annotated[str | None, Query(max_length=100)] = None,
    available: bool | None = None,
    max_rate: Annotated[float | None, Query(gt=0, le=9999999999, alias="maxRate")] = None,
):
    if category:
        services.category_by_label(db, category)
    query = services.worker_query(category, town, available, max_rate, search)
    return services.page_result(db, query, out.worker, page, per_page)


@router.get("/workers/{worker_id}", response_model=s.Envelope[s.WorkerDetail], tags=["Workers"])
def worker_details(worker_id: str, db: Db, request: Request):
    record = db.scalar(services.worker_query().where(m.Worker.id == worker_id))
    if record is None:
        missing()
    reviews = db.execute(
        select(m.Review, m.User.name)
        .outerjoin(m.User, m.User.id == m.Review.customer_id)
        .join(m.Booking, m.Booking.id == m.Review.booking_id)
        .where(
            m.Review.worker_id == worker_id,
            m.Booking.data_source == record.user.data_source,
            m.Booking.status == "completed",
            m.Booking.confirmed_at.is_not(None),
        )
        .order_by(m.Review.created_at.desc(), m.Review.id)
        .limit(20)
    ).all()
    return {
        "data": {
            **services.predicted_profile(db, record, request.app.state.settings),
            "reviews": [
                {
                    "rating": review.rating,
                    "customerName": (customer_name or "").split()[0] if (customer_name or "").strip() else "Customer",
                    "comment": review.comment,
                    "createdAt": out.aware(review.created_at),
                }
                for review, customer_name in reviews
            ],
        }
    }


@router.get("/worker/profile", response_model=s.Envelope[s.WorkerView], tags=["Profiles"])
def worker_profile(user: CurrentUser, db: Db, request: Request):
    record = own_worker(db, user)
    return {
        "data": {
            **services.predicted_profile(db, record, request.app.state.settings),
            "reviewNote": record.review_note,
            "latitude": record.latitude,
            "longitude": record.longitude,
        }
    }


@router.patch("/worker/profile", response_model=s.Envelope[s.WorkerView], tags=["Profiles"])
def update_worker_profile(data: s.WorkerPatch, user: CurrentUser, db: Db):
    return {"data": out.worker(services.patch_worker(db, user, data), private=True)}


@router.get("/worker/performance", response_model=s.Envelope[dict], tags=["Workers"])
def worker_performance(user: CurrentUser, db: Db, request: Request):
    record = own_worker(db, user)
    profile = services.predicted_profile(db, record, request.app.state.settings)
    return {
        "data": {
            "workerId": record.id,
            "performance": profile["performance"],
            "completedJobs": profile["evidence"]["completedJobs"],
            "dataSource": profile["dataSource"],
            "evidence": profile["evidence"],
            "rating": profile["rating"],
            "reviewCount": profile["reviewCount"],
            "reliabilityProbability": profile["reliabilityProbability"],
            "modelStatus": profile["modelStatus"],
            "source": "model" if profile["modelStatus"] == "available" else "booking_history",
            "modelVersion": "reliability_rf" if profile["modelStatus"] == "available" else None,
            "coldStart": profile["coldStart"],
            "imputedFeatures": profile["imputedFeatures"],
            "missingScoringFeatures": profile["missingScoringFeatures"],
        }
    }


@router.get("/requests", response_model=s.Page[s.RequestView], tags=["Requests"])
def requests(user: CurrentUser, db: Db, page: PageNumber = 1, per_page: PageSize = 20):
    require_role(user, "customer", "admin")
    query = select(m.ServiceRequest)
    if user.role == "customer":
        query = query.where(m.ServiceRequest.customer_id == user.id)
    return services.page_result(
        db,
        query.order_by(m.ServiceRequest.created_at.desc(), m.ServiceRequest.id),
        out.service_request,
        page,
        per_page,
    )


@router.post(
    "/requests", response_model=s.Envelope[s.RequestView], status_code=201, tags=["Requests"]
)
def create_request(data: s.RequestCreate, user: CurrentUser, db: Db):
    return {"data": out.service_request(services.create_request(db, user, data))}


@router.get("/requests/{request_id}", response_model=s.Envelope[s.RequestView], tags=["Requests"])
def request_details(request_id: str, user: CurrentUser, db: Db):
    return {"data": out.service_request(services.request_record(db, user, request_id))}


@router.patch("/requests/{request_id}", response_model=s.Envelope[s.RequestView], tags=["Requests"])
def update_request(request_id: str, data: s.RequestPatch, user: CurrentUser, db: Db):
    return {"data": out.service_request(services.patch_request(db, user, request_id, data))}


@router.post("/requests/{request_id}/classify", response_model=s.Envelope[dict], tags=["Matching"])
def classify(request_id: str, user: CurrentUser, db: Db, request: Request):
    return {"data": services.classify_request(db, user, request_id, request.app.state.settings)}


@router.post(
    "/requests/{request_id}/recommendations",
    response_model=s.Envelope[s.RecommendationResult],
    tags=["Matching"],
)
def recommendations(
    request_id: str, data: s.RecommendationFilters, user: CurrentUser, db: Db, request: Request
):
    return {
        "data": services.recommendations(db, user, request_id, data, request.app.state.settings)
    }


@router.get("/bookings", response_model=s.Page[s.BookingView], tags=["Bookings"])
def bookings(user: CurrentUser, db: Db, page: PageNumber = 1, per_page: PageSize = 20):
    query = services.booking_query(user, db).order_by(m.Booking.created_at.desc(), m.Booking.id)
    return services.page_result(db, query, out.booking, page, per_page)


@router.post(
    "/bookings", response_model=s.Envelope[s.BookingView], status_code=201, tags=["Bookings"]
)
def create_booking(data: s.BookingCreate, user: CurrentUser, db: Db, request: Request):
    return {
        "data": out.booking(services.create_booking(db, user, data, request.app.state.settings))
    }


@router.get("/bookings/{booking_id}", response_model=s.Envelope[s.BookingView], tags=["Bookings"])
def booking_details(booking_id: str, user: CurrentUser, db: Db):
    return {"data": out.booking(services.booking_record(db, user, booking_id))}


@router.patch(
    "/bookings/{booking_id}/status", response_model=s.Envelope[s.BookingView], tags=["Bookings"]
)
def booking_status(booking_id: str, data: s.BookingTransition, user: CurrentUser, db: Db):
    return {"data": out.booking(services.transition_booking(db, user, booking_id, data))}


@router.post(
    "/bookings/{booking_id}/review",
    response_model=s.Envelope[s.ReviewView],
    status_code=201,
    tags=["Reviews"],
)
def create_review(booking_id: str, data: s.ReviewCreate, user: CurrentUser, db: Db):
    return {"data": out.review(services.review_booking(db, user, booking_id, data))}


@router.post(
    "/bookings/{booking_id}/complaint",
    response_model=s.Envelope[dict],
    status_code=201,
    tags=["Complaints"],
)
def complaint(booking_id: str, data: s.ComplaintCreate, user: CurrentUser, db: Db):
    from app.outcomes import create_complaint

    return {"data": out.complaint(create_complaint(db, user, booking_id, data))}


@router.get("/notifications", response_model=s.Page[s.NotificationView], tags=["Notifications"])
def notifications(
    user: CurrentUser, db: Db, page: PageNumber = 1, per_page: PageSize = 20, unread: bool = False
):
    query = select(m.Notification).where(m.Notification.user_id == user.id)
    if unread:
        query = query.where(m.Notification.read_at.is_(None))
    return services.page_result(
        db,
        query.order_by(m.Notification.created_at.desc(), m.Notification.id),
        out.notification,
        page,
        per_page,
    )


@router.patch(
    "/notifications/{notification_id}",
    response_model=s.Envelope[s.NotificationView],
    tags=["Notifications"],
)
def read_notification(notification_id: str, data: s.NotificationRead, user: CurrentUser, db: Db):
    record = db.scalar(
        select(m.Notification)
        .where(m.Notification.id == notification_id, m.Notification.user_id == user.id)
        .with_for_update()
    )
    if record is None:
        missing()
    if record.read_at is None:
        record.read_at = m.utcnow()
    db.commit()
    return {"data": out.notification(record)}


@router.get("/dashboard", response_model=s.Envelope[dict], tags=["Dashboard"])
def dashboard(user: CurrentUser, db: Db):
    query = services.booking_query(user, db).with_only_columns(m.Booking.status, func.count())
    counts = dict(db.execute(query.group_by(m.Booking.status)).all())
    request_query = select(func.count()).select_from(m.ServiceRequest)
    if user.role == "customer":
        request_query = request_query.where(m.ServiceRequest.customer_id == user.id)
    return {
        "data": {
            "role": user.role,
            "bookingsByStatus": counts,
            "bookings": sum(counts.values()),
            "requests": db.scalar(request_query) if user.role != "worker" else None,
            "unreadNotifications": db.scalar(
                select(func.count())
                .select_from(m.Notification)
                .where(m.Notification.user_id == user.id, m.Notification.read_at.is_(None))
            ),
        }
    }
