"""Seed sample testing workers across all 4 categories and major Sri Lankan towns.

Ensures that customer requests for Plumbing, Electrical, Carpentry, or Welding
in any common town (Colombo, Jaffna, Kandy, Galle, Gampaha, Negombo) will find
available, qualified workers to match and rank with AI.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT / "skill-sync" / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import select
from app.auth import password_hash
from app.config import INTEGRATION_DATABASE, Settings
from app.database import make_engine, session_factory
from app.models import Category, User, Worker, WorkerCategory, WorkerMetric, WorkerTown

MAJOR_TOWNS = ["Colombo", "Jaffna", "Kandy", "Galle", "Gampaha", "Negombo"]

DEMO_WORKERS = [
    {
        "name": "Arul Selvan",
        "email": "arul.plumber@example.com",
        "town": "Colombo",
        "category": "Plumbing",
        "years_experience": 10,
        "rate_lkr": 2800.0,
        "rate_unit": "visit",
        "bio": "Experienced licensed plumber specializing in leak detection, bathroom plumbing, and pipe fittings.",
        "completed_jobs": 15,
        "rating_total": 72,
        "review_count": 15,
    },
    {
        "name": "Dinesh Kumar",
        "email": "dinesh.electric@example.com",
        "town": "Jaffna",
        "category": "Electrical",
        "years_experience": 8,
        "rate_lkr": 3200.0,
        "rate_unit": "visit",
        "bio": "Certified residential electrician for wiring, ceiling fans, breakers, and electrical safety inspections.",
        "completed_jobs": 22,
        "rating_total": 105,
        "review_count": 22,
    },
    {
        "name": "Nihal Jayasinghe",
        "email": "nihal.carpenter@example.com",
        "town": "Kandy",
        "category": "Carpentry",
        "years_experience": 12,
        "rate_lkr": 2500.0,
        "rate_unit": "visit",
        "bio": "Master carpenter skilled in wooden furniture repairs, custom cupboards, doors, and timber restoration.",
        "completed_jobs": 18,
        "rating_total": 86,
        "review_count": 18,
    },
    {
        "name": "Samantha Perera",
        "email": "samantha.welder@example.com",
        "town": "Galle",
        "category": "Welding",
        "years_experience": 9,
        "rate_lkr": 3500.0,
        "rate_unit": "visit",
        "bio": "Expert metal fabricator and welder for broken gate hinges, iron grills, steel railings, and structure repairs.",
        "completed_jobs": 12,
        "rating_total": 58,
        "review_count": 12,
    },
]


def seed_workers():
    settings = Settings()
    assert settings.db_name == INTEGRATION_DATABASE, f"Blocked unsafe DB: {settings.db_name}"
    engine = make_engine(settings)

    try:
        with session_factory(engine)() as db:
            categories_by_label = {c.label: c for c in db.scalars(select(Category)).all()}

            # Seed demo workers for each category
            for data in DEMO_WORKERS:
                user = db.scalar(select(User).where(User.email == data["email"]))
                if user is None:
                    user = User(
                        name=data["name"],
                        email=data["email"],
                        password_hash=password_hash.hash("WorkerPass123!"),
                        role="worker",
                        data_source="demo",
                        town=data["town"],
                        phone="0771234567",
                        contact_preference="phone",
                    )
                    db.add(user)
                    db.flush()

                worker = db.scalar(select(Worker).where(Worker.user_id == user.id))
                if worker is None:
                    worker = Worker(
                        user_id=user.id,
                        bio=data["bio"],
                        years_experience=data["years_experience"],
                        rate_lkr=data["rate_lkr"],
                        rate_unit=data["rate_unit"],
                        available=True,
                        verified=False,
                        review_count=data["review_count"],
                        rating_total=data["rating_total"],
                    )
                    db.add(worker)
                    db.flush()

                    # Add category
                    cat = categories_by_label.get(data["category"])
                    if cat:
                        worker.services.append(WorkerCategory(category=cat))
                        worker.metrics.append(
                            WorkerMetric(
                                category=cat,
                                completed_jobs=data["completed_jobs"],
                            )
                        )

                    # Add towns
                    for town in MAJOR_TOWNS:
                        worker.towns.append(WorkerTown(town_key=town.casefold(), town=town))

                    print(f"Created worker: {data['name']} ({data['category']} in {', '.join(MAJOR_TOWNS)})")
                else:
                    print("Existing demo worker preserved: " + data["name"])

            db.commit()
            print("Successfully seeded demo workers across all 4 categories and towns!")

    finally:
        engine.dispose()


if __name__ == "__main__":
    seed_workers()
