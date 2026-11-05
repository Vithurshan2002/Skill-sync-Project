from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def new_id() -> str:
    return str(uuid4())


def utcnow() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    __table_args__ = (CheckConstraint("role IN ('customer','worker','admin')", name="user_role"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), index=True)
    data_source: Mapped[str] = mapped_column(String(10), default="test", server_default="test")
    town: Mapped[str] = mapped_column(String(100))
    phone: Mapped[str | None] = mapped_column(String(30))
    contact_preference: Mapped[str] = mapped_column(String(10), default="email")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AccessToken(Base):
    __tablename__ = "access_tokens"

    digest: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    label: Mapped[str] = mapped_column(String(80), unique=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True)
    icon: Mapped[str] = mapped_column(String(80))
    description: Mapped[str] = mapped_column(String(300))
    example_request: Mapped[str] = mapped_column(String(2000))


class Worker(Base):
    __tablename__ = "workers"
    __table_args__ = (
        CheckConstraint("rate_lkr IS NULL OR rate_lkr > 0", name="worker_positive_rate"),
        CheckConstraint("years_experience BETWEEN 0 AND 60", name="worker_experience"),
        CheckConstraint("rate_unit IN ('hour','visit')", name="worker_rate_unit"),
        CheckConstraint(
            "(latitude IS NULL AND longitude IS NULL AND service_radius_km IS NULL) OR (latitude IS NOT NULL AND longitude IS NOT NULL AND service_radius_km IS NOT NULL AND latitude BETWEEN -90 AND 90 AND longitude BETWEEN -180 AND 180 AND service_radius_km BETWEEN 0.1 AND 500)",
            name="worker_location",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), unique=True)
    bio: Mapped[str] = mapped_column(Text, default="")
    years_experience: Mapped[int] = mapped_column(Integer, default=0)
    rate_lkr: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    rate_unit: Mapped[str] = mapped_column(String(10), default="visit")
    available: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    review_note: Mapped[str | None] = mapped_column(String(500))
    review_baseline: Mapped[dict | None] = mapped_column(JSON)
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    service_radius_km: Mapped[float | None] = mapped_column(Float)
    review_count: Mapped[int] = mapped_column(Integer, default=0)
    rating_total: Mapped[int] = mapped_column(Integer, default=0)
    user: Mapped[User] = relationship(lazy="selectin")
    services: Mapped[list["WorkerCategory"]] = relationship(
        cascade="all, delete-orphan", lazy="selectin"
    )
    towns: Mapped[list["WorkerTown"]] = relationship(cascade="all, delete-orphan", lazy="selectin")
    metrics: Mapped[list["WorkerMetric"]] = relationship(lazy="selectin")
    bookings: Mapped[list["Booking"]] = relationship(lazy="selectin", back_populates="worker")

    @property
    def review_ready(self) -> bool:
        return bool(self.services and self.towns and self.rate_lkr and len(self.bio) >= 15)


class WorkerCategory(Base):
    __tablename__ = "worker_categories"

    worker_id: Mapped[str] = mapped_column(ForeignKey("workers.id"), primary_key=True)
    category_id: Mapped[str] = mapped_column(ForeignKey("categories.id"), primary_key=True)
    category: Mapped[Category] = relationship(lazy="joined")


class WorkerTown(Base):
    __tablename__ = "worker_towns"

    worker_id: Mapped[str] = mapped_column(ForeignKey("workers.id"), primary_key=True)
    town_key: Mapped[str] = mapped_column(String(100), primary_key=True)
    town: Mapped[str] = mapped_column(String(100))


class WorkerMetric(Base):
    __tablename__ = "worker_metrics"

    worker_id: Mapped[str] = mapped_column(ForeignKey("workers.id"), primary_key=True)
    category_id: Mapped[str] = mapped_column(ForeignKey("categories.id"), primary_key=True)
    completed_jobs: Mapped[int] = mapped_column(Integer, default=0)
    category: Mapped[Category] = relationship(lazy="joined")


class ServiceRequest(Base):
    __tablename__ = "service_requests"
    __table_args__ = (
        CheckConstraint("status IN ('submitted','booked','closed')", name="request_status"),
        CheckConstraint("budget_lkr IS NULL OR budget_lkr > 0", name="request_positive_budget"),
        CheckConstraint(
            "(latitude IS NULL AND longitude IS NULL) OR (latitude IS NOT NULL AND longitude IS NOT NULL AND latitude BETWEEN -90 AND 90 AND longitude BETWEEN -180 AND 180)",
            name="request_location",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    customer_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(String(2000))
    town: Mapped[str] = mapped_column(String(100))
    address: Mapped[str | None] = mapped_column(String(250))
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    preferred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    budget_lkr: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    category_id: Mapped[str | None] = mapped_column(ForeignKey("categories.id"))
    status: Mapped[str] = mapped_column(String(20), default="submitted")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    category: Mapped[Category | None] = relationship(lazy="selectin")


class Booking(Base):
    __tablename__ = "bookings"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','accepted','in_progress','awaiting_confirmation','completed','rejected','cancelled')",
            name="booking_status",
        ),
        CheckConstraint(
            "deadline_at IS NULL OR deadline_at > scheduled_at", name="booking_deadline"
        ),
        CheckConstraint(
            "scheduled_end_at IS NULL OR (scheduled_end_at > scheduled_at "
            "AND (deadline_at IS NULL OR scheduled_end_at <= deadline_at))",
            name="booking_time_window",
        ),
        Index(
            "uq_active_booking_request",
            "request_id",
            unique=True,
            postgresql_where=text(
                "status IN ('pending','accepted','in_progress','awaiting_confirmation')"
            ),
            sqlite_where=text(
                "status IN ('pending','accepted','in_progress','awaiting_confirmation')"
            ),
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    request_id: Mapped[str] = mapped_column(ForeignKey("service_requests.id"), index=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    worker_id: Mapped[str] = mapped_column(ForeignKey("workers.id"), index=True)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    scheduled_end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deadline_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reported_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_by_role: Mapped[str | None] = mapped_column(String(20))
    prediction: Mapped[dict | None] = mapped_column(JSON)
    data_source: Mapped[str] = mapped_column(String(10), default="test", server_default="test")
    status: Mapped[str] = mapped_column(String(30), default="pending")
    quoted_rate_lkr: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    rate_unit: Mapped[str] = mapped_column(String(10))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    worker: Mapped[Worker] = relationship(lazy="selectin", back_populates="bookings")
    request: Mapped[ServiceRequest] = relationship(lazy="selectin")
    history: Mapped[list["BookingEvent"]] = relationship(
        lazy="selectin", order_by="BookingEvent.at, BookingEvent.id"
    )
    review: Mapped["Review | None"] = relationship(lazy="selectin", uselist=False)
    complaint: Mapped["Complaint | None"] = relationship(lazy="selectin", uselist=False)


class BookingEvent(Base):
    __tablename__ = "booking_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    booking_id: Mapped[str] = mapped_column(ForeignKey("bookings.id"), index=True)
    actor_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(30))
    note: Mapped[str | None] = mapped_column(String(500))
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Review(Base):
    __tablename__ = "reviews"
    __table_args__ = (CheckConstraint("rating BETWEEN 1 AND 5", name="review_rating"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    booking_id: Mapped[str] = mapped_column(ForeignKey("bookings.id"), unique=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    worker_id: Mapped[str] = mapped_column(ForeignKey("workers.id"), index=True)
    rating: Mapped[int] = mapped_column(Integer)
    comment: Mapped[str] = mapped_column(String(1000))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Complaint(Base):
    __tablename__ = "complaints"
    __table_args__ = (
        CheckConstraint("status IN ('pending','upheld','dismissed')", name="complaint_status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    booking_id: Mapped[str] = mapped_column(ForeignKey("bookings.id"), unique=True)
    reason: Mapped[str] = mapped_column(String(2000))
    status: Mapped[str] = mapped_column(String(20), default="pending")
    resolution: Mapped[str | None] = mapped_column(String(2000))
    reviewed_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    message: Mapped[str] = mapped_column(String(500))
    target_path: Mapped[str] = mapped_column(String(250))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    actor_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    action: Mapped[str] = mapped_column(String(80))
    record_id: Mapped[str] = mapped_column(String(36))
    details: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
