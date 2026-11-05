from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import (
    AfterValidator,
    AwareDatetime,
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)
from pydantic.alias_generators import to_camel


class Schema(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid")


class Envelope[T](Schema):
    data: T


class PageMeta(Schema):
    page: int
    per_page: int
    total: int
    last_page: int


class Page[T](Envelope[list[T]]):
    meta: PageMeta


class ErrorDetail(Schema):
    code: str
    message: str
    fields: dict[str, list[str]] | None = None


class ErrorEnvelope(Schema):
    error: ErrorDetail


Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=100)]
Town = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=100)]
Money = Annotated[Decimal, Field(gt=0, le=9999999999, max_digits=12, decimal_places=2)]
Password = Annotated[str, Field(min_length=8, max_length=128)]
Latitude = Annotated[float, Field(ge=-90, le=90, allow_inf_nan=False)]
Longitude = Annotated[float, Field(ge=-180, le=180, allow_inf_nan=False)]
ServiceRadius = Annotated[float, Field(ge=0.1, le=500, allow_inf_nan=False)]


def validate_location_fields(value, fields):
    supplied = set(fields) & value.model_fields_set
    if supplied and supplied != set(fields):
        raise ValueError("Send all location fields together, or clear all of them.")
    populated = [getattr(value, field) is not None for field in fields]
    if any(populated) and not all(populated):
        raise ValueError("Provide all location fields, or leave all of them empty.")
    return value


def future(value: datetime) -> datetime:
    if value <= datetime.now(UTC):
        raise ValueError("Choose a future date and time, including a timezone offset.")
    return value


FutureTime = Annotated[AwareDatetime, AfterValidator(future)]


class Register(Schema):
    name: Name
    email: EmailStr
    password: Password
    role: Literal["customer", "worker"]
    town: Town

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.lower()


class Login(Schema):
    email: EmailStr
    password: Annotated[str, Field(min_length=1, max_length=128)]

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.lower()


class ProfilePatch(Schema):
    name: Name | None = None
    town: Town | None = None
    phone: Annotated[str, StringConstraints(strip_whitespace=True, max_length=30)] | None = None
    contact_preference: Literal["email", "phone"] | None = None

    @model_validator(mode="after")
    def reject_required_nulls(self):
        for field in self.model_fields_set - {
            "phone",
            "latitude",
            "longitude",
            "service_radius_km",
        }:
            if getattr(self, field) is None:
                raise ValueError(f"{to_camel(field)} cannot be null.")
        return self


class WorkerPatch(ProfilePatch):
    latitude: Latitude | None = None
    longitude: Longitude | None = None
    service_radius_km: ServiceRadius | None = None

    @model_validator(mode="after")
    def validate_location(self):
        return validate_location_fields(self, ("latitude", "longitude", "service_radius_km"))

    bio: (
        Annotated[str, StringConstraints(strip_whitespace=True, min_length=15, max_length=2000)]
        | None
    ) = None
    categories: Annotated[list[str], Field(min_length=1, max_length=4)] | None = None
    service_towns: Annotated[list[Town], Field(min_length=1, max_length=50)] | None = None
    years_experience: Annotated[int, Field(ge=0, le=60, strict=True)] | None = None
    rate_lkr: Money | None = None
    rate_unit: Literal["hour", "visit"] | None = None
    available: bool | None = None


class RequestCreate(Schema):
    latitude: Latitude | None = None
    longitude: Longitude | None = None

    @model_validator(mode="after")
    def validate_location(self):
        return validate_location_fields(self, ("latitude", "longitude"))

    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=5, max_length=120)]
    description: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=15, max_length=2000)
    ]
    town: Town
    address: Annotated[str, StringConstraints(strip_whitespace=True, max_length=250)] | None = None
    preferred_at: FutureTime
    budget_lkr: Money | None = None
    category: str | None = None


class RequestPatch(Schema):
    latitude: Latitude | None = None
    longitude: Longitude | None = None

    @model_validator(mode="after")
    def validate_location(self):
        return validate_location_fields(self, ("latitude", "longitude"))

    title: (
        Annotated[str, StringConstraints(strip_whitespace=True, min_length=5, max_length=120)]
        | None
    ) = None
    description: (
        Annotated[str, StringConstraints(strip_whitespace=True, min_length=15, max_length=2000)]
        | None
    ) = None
    town: Town | None = None
    address: Annotated[str, StringConstraints(strip_whitespace=True, max_length=250)] | None = None
    preferred_at: FutureTime | None = None
    budget_lkr: Money | None = None
    category: str | None = None

    @model_validator(mode="after")
    def reject_required_nulls(self):
        for field in self.model_fields_set - {
            "address",
            "budget_lkr",
            "category",
            "latitude",
            "longitude",
        }:
            if getattr(self, field) is None:
                raise ValueError(f"{to_camel(field)} cannot be null.")
        return self


class RecommendationFilters(Schema):
    available: bool = True
    max_rate: Money | None = None


class BookingCreate(Schema):
    request_id: str
    worker_id: str
    scheduled_at: FutureTime
    scheduled_end_at: FutureTime
    deadline_at: FutureTime

    @model_validator(mode="after")
    def deadline_after_start(self):
        if self.scheduled_end_at <= self.scheduled_at:
            raise ValueError("Expected end time must be after the appointment time.")
        if self.deadline_at < self.scheduled_end_at:
            raise ValueError("Completion deadline must be at or after the expected end time.")
        return self


class BookingTransition(Schema):
    status: Literal[
        "accepted", "rejected", "cancelled", "in_progress", "awaiting_confirmation", "completed"
    ]
    note: Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)] | None = None


class ReviewCreate(Schema):
    rating: Annotated[int, Field(ge=1, le=5, strict=True)]
    comment: Annotated[str, StringConstraints(strip_whitespace=True, min_length=5, max_length=1000)]


class ComplaintCreate(Schema):
    reason: Annotated[str, StringConstraints(strip_whitespace=True, min_length=10, max_length=2000)]


class ComplaintResolution(Schema):
    status: Literal["upheld", "dismissed"]
    resolution: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=10, max_length=2000)
    ]


class NotificationRead(Schema):
    read: Literal[True] = True


class CategoryPatch(Schema):
    description: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=10, max_length=300)
    ]
    example_request: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=15, max_length=2000)
    ]


class VerificationPatch(Schema):
    verified: bool
    note: Annotated[str, StringConstraints(strip_whitespace=True, min_length=5, max_length=500)]


class DataSourcePatch(Schema):
    data_source: Literal["demo", "test", "real"]
    note: Annotated[str, StringConstraints(strip_whitespace=True, min_length=10, max_length=500)]


class Identity(Schema):
    data_source: str = "test"
    id: str
    name: str
    email: str
    role: Literal["customer", "worker", "admin"]
    worker_id: str | None
    town: str
    phone: str | None
    contact_preference: str


class TokenResult(Schema):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_at: datetime
    user: Identity


class CategoryView(Schema):
    id: str
    label: str
    slug: str
    icon: str
    description: str
    example_request: str


class PerformanceMetric(Schema):
    evidence: dict = Field(default_factory=dict)
    category: str
    completed_jobs: int
    skill_score: float | None = None


class WorkerView(Schema):
    latitude: float | None = None
    longitude: float | None = None
    service_radius_km: float | None = None
    data_source: str = "test"
    evidence: dict = Field(default_factory=dict)
    id: str
    name: str
    town: str
    service_towns: list[str]
    categories: list[str]
    bio: str
    years_experience: int
    rate_lkr: float | None
    rate_unit: str
    available: bool
    rating: float | None
    review_count: int
    performance: list[PerformanceMetric]
    reliability_probability: float | None = None
    verified: bool
    model_status: str = "not_requested"
    approval_status: Literal["pending", "approved", "changes_requested"] = "pending"
    review_note: str | None = None
    review_ready: bool = False
    profile_changes: list[dict] = Field(default_factory=list)
    cold_start: bool = False
    imputed_features: list[str] = Field(default_factory=list)
    missing_scoring_features: list[str] = Field(default_factory=list)


class ReviewView(Schema):
    id: str
    booking_id: str
    customer_id: str
    worker_id: str
    rating: int
    comment: str
    created_at: datetime


class PublicReview(Schema):
    customer_name: str = "Customer"
    rating: int
    comment: str
    created_at: datetime


class WorkerDetail(WorkerView):
    reviews: list[PublicReview]


class RequestView(Schema):
    latitude: float | None = None
    longitude: float | None = None
    id: str
    customer_id: str
    title: str
    description: str
    town: str
    address: str | None
    preferred_at: datetime
    budget_lkr: float | None
    category: str | None
    status: str
    created_at: datetime


class HistoryEvent(Schema):
    status: str
    at: datetime
    note: str | None


class BookingView(Schema):
    data_source: str = "test"
    id: str
    request_id: str
    customer_id: str
    worker_id: str
    scheduled_at: datetime
    scheduled_end_at: datetime | None = None
    deadline_at: datetime | None
    reported_completed_at: datetime | None
    confirmed_at: datetime | None
    cancelled_by_role: str | None
    complaint: dict | None
    status: str
    quoted_rate_lkr: float
    rate_unit: str
    history: list[HistoryEvent]
    request: RequestView
    worker: WorkerView
    review: ReviewView | None


class NotificationView(Schema):
    id: str
    user_id: str
    message: str
    target_path: str
    created_at: datetime
    read_at: datetime | None


class Recommendation(Schema):
    distance_km: float | None = None
    location_match: Literal["gps", "town"] = "town"
    data_source: str = "test"
    feature_version: str | None = None
    evidence: dict = Field(default_factory=dict)
    worker_id: str
    rank: int
    match_score: float | None = None
    category_skill_score: float | None = None
    reliability_probability: float | None = None
    reliability_percentage: float | None = None
    cold_start: bool = False
    imputed_features: list[str] = Field(default_factory=list)
    missing_scoring_features: list[str] = Field(default_factory=list)
    reasons: list[str]
    source: Literal["rule_based", "model"] = "rule_based"
    worker: WorkerView


class RecommendationResult(Schema):
    request_id: str
    category: str
    source: Literal["rule_based", "model"] = "rule_based"
    fallback_reason: str | None = None
    recommendations: list[Recommendation]
