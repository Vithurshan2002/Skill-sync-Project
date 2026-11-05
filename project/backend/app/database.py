from collections.abc import Generator

from fastapi import Request
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings


def make_engine(settings: Settings) -> Engine:
    dsn = settings.database_dsn()
    if not str(dsn).startswith("postgresql+psycopg"):
        raise ValueError("The backend requires a postgresql+psycopg database URL.")
    return create_engine(dsn, pool_pre_ping=True, isolation_level="READ COMMITTED")


def session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(engine, expire_on_commit=False)


def get_db(request: Request) -> Generator[Session, None, None]:
    with request.app.state.sessions() as session:
        yield session
