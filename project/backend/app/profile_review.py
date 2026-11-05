"""Private, cumulative changes to the profile fields reviewed by administrators."""

LABELS = {
    "name": "Name",
    "town": "Home town",
    "bio": "Biography",
    "yearsExperience": "Experience",
    "categories": "Service categories",
    "serviceTowns": "Service towns",
    "serviceLocation": "Service location",
    "serviceRadiusKm": "Service radius (km)",
}


def snapshot(worker) -> dict:
    return {
        "name": worker.user.name,
        "town": worker.user.town,
        "bio": worker.bio,
        "yearsExperience": worker.years_experience,
        "categories": sorted(item.category.label for item in worker.services),
        "serviceTowns": sorted(item.town for item in worker.towns),
        "serviceLocation": [worker.latitude, worker.longitude]
        if worker.latitude is not None
        else None,
        "serviceRadiusKm": worker.service_radius_km,
    }


def changes(before: dict | None, after: dict) -> list[dict]:
    if before is None:
        return []
    return [
        {"field": key, "label": label, "before": before.get(key), "after": after[key]}
        for key, label in LABELS.items()
        if before.get(key) != after[key]
    ]


def pending_changes(worker) -> list[dict]:
    return changes(worker.review_baseline, snapshot(worker))
