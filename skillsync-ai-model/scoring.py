def clamp(value, minimum=0.0, maximum=100.0):
    return max(minimum, min(value, maximum))


def calculate_skill_score(
    experience_years: float,
    completed_jobs: int,
    rating: float | None,
    certified: bool | None,
    complaint_rate: float | None,
):
    # Starter normalization rules. These should be justified/tuned in the research.
    experience_score = clamp((experience_years / 10.0) * 100.0)
    job_score = clamp((completed_jobs / 100.0) * 100.0)
    # Missing evidence is excluded, then known weights are normalized.
    components = [(experience_score, 0.20), (job_score, 0.25)]
    if rating is not None:
        components.append((clamp((rating / 5.0) * 100.0), 0.30))
    if certified is not None:
        components.append((100.0 if certified else 0.0, 0.15))
    if complaint_rate is not None:
        complaint_score = clamp((1.0 - min(max(0.0, complaint_rate), 0.20) / 0.20) * 100.0)
        components.append((complaint_score, 0.10))
    skill_score = sum(score * weight for score, weight in components) / sum(weight for _, weight in components)

    if skill_score >= 80:
        level = "Highly Skilled"
    elif skill_score >= 65:
        level = "Skilled"
    elif skill_score >= 50:
        level = "Moderately Skilled"
    else:
        level = "Needs Verification"

    return {
        "skill_score": round(skill_score, 2),
        "level": level,
    }


def calculate_recommendation_score(
    skill_score: float,
    reliability_probability: float,
    rating: float | None,
    available: bool,
    distance_km: float | None,
):
    reliability_score = clamp(reliability_probability * 100.0)
    availability_score = 100.0 if available else 0.0
    components = [(skill_score, 0.30), (reliability_score, 0.30), (availability_score, 0.10)]
    if rating is not None:
        components.append((clamp((rating / 5.0) * 100.0), 0.15))
    if distance_km is not None:
        distance_score = max(0.0, 100.0 - (min(max(0.0, distance_km), 20.0) / 20.0) * 100.0)
        components.append((distance_score, 0.15))
    final_score = sum(score * weight for score, weight in components) / sum(weight for _, weight in components)

    return round(final_score, 2)


def generate_explanation(
    skill_score: float,
    reliability: float,
    rating: float | None,
    distance_km: float | None,
):
    reasons = []

    if skill_score >= 80:
        reasons.append("high skill competency")

    if reliability >= 0.85:
        reasons.append("strong predicted reliability")

    if rating is not None and rating >= 4.5:
        reasons.append("high customer rating")

    if distance_km is not None and distance_km <= 5:
        reasons.append("nearby location")

    if not reasons:
        reasons.append("balanced overall performance")

    return "Recommended because of " + ", ".join(reasons) + "."
