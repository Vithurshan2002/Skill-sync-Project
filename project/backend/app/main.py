import logging
from collections import defaultdict
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from starlette.exceptions import HTTPException

from app import admin, models, routes
from app.config import Settings
from app.database import make_engine, session_factory
from app.errors import ApiError
from app.schemas import ErrorEnvelope

logger = logging.getLogger("skillsync")


def create_app(settings: Settings | None = None, engine=None) -> FastAPI:
    settings = settings or Settings()
    engine = engine or make_engine(settings)

    @asynccontextmanager
    async def lifespan(_app):
        yield
        engine.dispose()

    app = FastAPI(
        title="SkillSync Backend API",
        version="0.1.0",
        lifespan=lifespan,
        description=(
            "PostgreSQL backend for the connected Laravel frontend. "
            "Register or log in, then paste accessToken into Authorize. "
            "All appointment timestamps require timezone offsets. "
            "Classification and reliability use the separate SkillSync inference service. "
            "Service matching remains available when inference is unavailable."
        ),
        responses={code: {"model": ErrorEnvelope} for code in [401, 403, 404, 409, 422, 503]},
    )
    app.state.settings = settings
    app.state.engine = engine
    app.state.sessions = session_factory(engine)

    @app.exception_handler(ApiError)
    async def api_error(_request: Request, exception: ApiError):
        headers = {"WWW-Authenticate": "Bearer"} if exception.status == 401 else None
        return JSONResponse(
            status_code=exception.status,
            headers=headers,
            content={
                "error": {
                    "code": exception.code,
                    "message": exception.message,
                    "fields": exception.fields,
                }
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(_request: Request, exception: RequestValidationError):
        fields = defaultdict(list)
        for error in exception.errors():
            key = (
                ".".join(
                    str(part) for part in error["loc"] if part not in {"body", "query", "path"}
                )
                or "body"
            )
            fields[key].append(error["msg"])
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "validation_error",
                    "message": "Please check your input.",
                    "fields": dict(fields),
                }
            },
        )

    @app.exception_handler(IntegrityError)
    async def integrity_error(_request: Request, _exception: IntegrityError):
        return JSONResponse(
            status_code=409,
            content={
                "error": {
                    "code": "conflict",
                    "message": "This operation conflicts with an existing record. "
                    "Refresh and check its current state.",
                }
            },
        )

    @app.exception_handler(SQLAlchemyError)
    async def database_error(_request: Request, _exception: SQLAlchemyError):
        logger.error("Database operation failed; verify PostgreSQL connectivity and migrations.")
        return JSONResponse(
            status_code=503,
            content={
                "error": {
                    "code": "database_unavailable",
                    "message": "The database is unavailable. Verify its connection and migrations.",
                }
            },
        )

    @app.exception_handler(HTTPException)
    async def http_error(_request: Request, exception: HTTPException):
        return JSONResponse(
            status_code=exception.status_code,
            headers=exception.headers,
            content={"error": {"code": "http_error", "message": str(exception.detail)}},
        )

    @app.exception_handler(Exception)
    async def unexpected_error(_request: Request, _exception: Exception):
        logger.error("Unexpected API error.")
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "internal_error",
                    "message": "An unexpected server error occurred.",
                }
            },
        )

    @app.get("/health", tags=["Health"])
    def health():
        return {"data": {"status": "ok", "service": "skillsync-backend"}}

    @app.get("/health/ready", tags=["Health"])
    def readiness():
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            connection.execute(select(models.Category.id).limit(1))
        return {"data": {"status": "ready", "database": "postgresql"}}

    app.include_router(routes.router)
    app.include_router(admin.router)
    return app


app = create_app()
