"""Server-computed straight-line distance; coordinates never go to the AI service."""

from math import asin, cos, radians, sin, sqrt


def distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    dlat, dlon = radians(lat2 - lat1), radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return 6371.0088 * 2 * asin(sqrt(min(1.0, max(0.0, a))))


def match(worker, request) -> tuple[bool, float | None]:
    if request.latitude is not None and worker.latitude is not None:
        distance = distance_km(
            worker.latitude, worker.longitude, request.latitude, request.longitude
        )
        return distance <= worker.service_radius_km, distance
    return any(t.town_key == request.town.strip().casefold() for t in worker.towns), None


def details(worker, request) -> dict:
    _, distance = match(worker, request)
    return {
        "distanceKm": round(distance, 2) if distance is not None else None,
        "locationMatch": "gps" if distance is not None else "town",
    }


def explanation(worker, request) -> str:
    _, distance = match(worker, request)
    if distance is None:
        return f"Serves {request.town}; town match only because a saved GPS location is missing."
    return f"About {distance:.1f} km away in a straight line, within this worker's {worker.service_radius_km:g} km service radius."
