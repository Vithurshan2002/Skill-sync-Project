import argparse
import getpass
import re

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError

from app.auth import password_hash
from app.catalog import seed_categories
from app.config import ROOT, Settings
from app.database import make_engine, session_factory
from app.models import User
from app.schemas import Register


def create_database(settings: Settings) -> None:
    url = make_url(settings.database_dsn())
    name = url.database
    if not name or not re.fullmatch(r"skillsync[a-z0-9_]{0,54}", name):
        raise ValueError(
            "create-db requires a database name beginning with skillsync, "
            "followed by letters, digits, or underscores."
        )
    engine = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    try:
        with engine.connect() as connection:
            exists = connection.scalar(
                text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": name}
            )
            if exists:
                print("Project database already exists; no data was changed.")
            else:
                quoted = engine.dialect.identifier_preparer.quote(name)
                connection.execute(text(f"CREATE DATABASE {quoted}"))
                print("Project database created.")
    finally:
        engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="SkillSync PostgreSQL administration")
    parser.add_argument(
        "command", choices=["check-db", "create-db", "init-db", "seed-categories", "create-admin"]
    )
    args = parser.parse_args()
    settings = Settings()
    try:
        if args.command in {"create-db", "init-db"}:
            create_database(settings)
        if args.command == "create-db":
            return
        if args.command == "init-db":
            config = Config(str(ROOT / "alembic.ini"))
            command.upgrade(config, "head")
        engine = make_engine(settings)
        try:
            with session_factory(engine)() as db:
                if args.command == "check-db":
                    db.execute(text("SELECT 1"))
                    print("PostgreSQL connection successful.")
                elif args.command in {"init-db", "seed-categories"}:
                    seed_categories(db)
                    print(
                        "Database migrated and category catalog ready. "
                        "No sample accounts or bookings added."
                    )
                elif args.command == "create-admin":
                    data = Register(
                        name=input("Admin name: "),
                        email=input("Admin email: "),
                        town=input("Town: "),
                        role="customer",
                        password=getpass.getpass("Password (at least 8 characters): "),
                    )
                    if db.scalar(select(User.id).where(User.email == data.email)):
                        raise ValueError(
                            "That email already belongs to an account. "
                            "Existing roles are never overwritten."
                        )
                    db.add(
                        User(
                            name=data.name,
                            email=data.email,
                            town=data.town,
                            password_hash=password_hash.hash(data.password),
                            role="admin",
                        )
                    )
                    db.commit()
                    print("Administrator created. Use /api/v1/auth/login to sign in.")
        finally:
            engine.dispose()
    except SQLAlchemyError:
        parser.exit(
            1,
            "Database operation failed. Check PostgreSQL, backend/.env, "
            "database permissions, and migrations. Credentials were not displayed.\n",
        )
    except ValueError as exception:
        # Pydantic validation can embed input values, including credentials.
        from pydantic import ValidationError

        if isinstance(exception, ValidationError):
            parser.exit(
                1,
                "Invalid admin details. Use a valid email, nonempty name/town, "
                "and password of 8–128 characters.\n",
            )
        parser.exit(1, f"{exception}\n")


if __name__ == "__main__":
    main()
