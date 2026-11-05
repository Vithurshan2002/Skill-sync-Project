from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Category

# Only the four categories supported by the trained classifier.
# Explicit IDs preserve the original database identifiers:
# Carpentry cat03, Electrical cat04, Plumbing cat08, Welding cat10.
CATALOG = [
    (
        "cat03",
        "Carpentry",
        "square-3-stack-3d",
        "Repairs and custom work in wood.",
        "I need a wooden wardrobe door repaired.",
    ),
    (
        "cat04",
        "Electrical",
        "bolt",
        "Help with wiring, lighting and electrical faults.",
        "The bedroom ceiling fan does not turn on.",
    ),
    (
        "cat08",
        "Plumbing",
        "wrench-screwdriver",
        "Repairs for taps, pipes and household plumbing.",
        "My kitchen tap keeps leaking even when it is closed.",
    ),
    (
        "cat10",
        "Welding",
        "fire",
        "Metal repairs, fabrication and finishing work.",
        "The metal hinge on my front gate has broken.",
    ),
]

CATEGORY_LABELS = frozenset(label for _, label, *_ in CATALOG)


def seed_categories(db: Session) -> None:
    existing = set(db.scalars(select(Category.id)).all())
    for category_id, label, icon, description, example in CATALOG:
        if category_id not in existing:
            db.add(
                Category(
                    id=category_id,
                    label=label,
                    slug=label.lower().replace(" ", "-"),
                    icon=f"heroicon-o-{icon}",
                    description=description,
                    example_request=example,
                )
            )
    db.commit()
