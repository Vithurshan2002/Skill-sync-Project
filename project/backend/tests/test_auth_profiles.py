from datetime import timedelta

import pytest
from sqlalchemy import select

from app.models import AccessToken, User, utcnow
from tests.helpers import PASSWORD, account, worker


def test_registration_login_logout_and_secret_storage(api):
    headers, user = account(api, "worker")
    assert user["workerId"] is not None
    profile = api.get("/api/v1/worker/profile", headers=headers).json()["data"]
    assert profile["available"] is False
    assert profile["reliabilityProbability"] is None
    assert profile["rateLkr"] is None
    assert api.get("/api/v1/workers").json()["meta"]["total"] == 0
    with api.app.state.sessions() as db:
        stored = db.get(User, user["id"])
        assert stored.password_hash.startswith("$argon2")
        assert stored.password_hash != PASSWORD
        token = db.scalar(select(AccessToken))
        assert token.digest not in headers["Authorization"]
    login = api.post(
        "/api/v1/auth/login", json={"email": user["email"].upper(), "password": PASSWORD}
    )
    assert login.status_code == 200
    assert "password" not in login.text.lower()
    assert api.post("/api/v1/auth/logout", headers=headers).status_code == 200
    assert api.get("/api/v1/me", headers=headers).status_code == 401
    assert (
        api.get(
            "/api/v1/me", headers={"Authorization": f"Bearer {login.json()['data']['accessToken']}"}
        ).status_code
        == 200
    )


def test_registration_cannot_create_admin_or_duplicate_case_variant_email(api):
    _, user = account(api)
    payload = {
        "name": "Other Test",
        "email": user["email"].upper(),
        "town": "Galle",
        "role": "customer",
        "password": PASSWORD,
    }
    assert api.post("/api/v1/auth/register", json=payload).status_code == 409
    payload.update(email="admin@example.com", role="admin")
    assert api.post("/api/v1/auth/register", json=payload).status_code == 422


def test_expired_invalid_and_missing_tokens_are_unauthorized(api):
    headers, _ = account(api)
    with api.app.state.sessions() as db:
        token = db.scalar(select(AccessToken))
        token.expires_at = utcnow() - timedelta(minutes=1)
        db.commit()
    for auth in [{}, {"Authorization": "Bearer invalid"}, headers]:
        response = api.get("/api/v1/me", headers=auth)
        assert response.status_code == 401
        assert response.headers["www-authenticate"] == "Bearer"
    response = api.post(
        "/api/v1/auth/login", json={"email": "unknown@example.com", "password": "wrong"}
    )
    assert response.status_code == 401


@pytest.mark.parametrize(
    "field,value", [("role", "admin"), ("email", "changed@example.com"), ("workerId", "forged")]
)
def test_profile_rejects_privilege_and_identity_changes(api, field, value):
    headers, user = account(api)
    response = api.patch("/api/v1/me", headers=headers, json={field: value})
    assert response.status_code == 422
    assert api.get("/api/v1/me", headers=headers).json()["data"] == user


def test_customer_and_worker_profiles_persist_with_required_availability_fields(api):
    customer, _ = account(api)
    assert (
        api.patch(
            "/api/v1/me", headers=customer, json={"name": "Changed Name", "phone": "0000000000"}
        ).status_code
        == 200
    )
    assert api.get("/api/v1/me", headers=customer).json()["data"]["name"] == "Changed Name"
    headers, user = account(api, "worker")
    assert (
        api.patch("/api/v1/worker/profile", headers=headers, json={"available": True}).status_code
        == 422
    )
    assert (
        api.patch(
            "/api/v1/worker/profile", headers=headers, json={"categories": [], "serviceTowns": []}
        ).status_code
        == 422
    )
    assert (
        api.patch("/api/v1/worker/profile", headers=headers, json={"available": None}).status_code
        == 422
    )
    headers, profile, _ = worker(api)
    update = {
        "categories": ["Plumbing", "Electrical"],
        "serviceTowns": ["Colombo", "colombo", "Kandy"],
    }
    assert api.patch("/api/v1/worker/profile", headers=headers, json=update).status_code == 200
    saved = api.get("/api/v1/worker/profile", headers=headers).json()["data"]
    assert saved["categories"] == ["Electrical", "Plumbing"]
    assert len(saved["serviceTowns"]) == 2
    assert (
        api.patch("/api/v1/worker/profile", headers=headers, json={"verified": True}).status_code
        == 422
    )
    assert (
        api.patch("/api/v1/worker/profile", headers=customer, json={"available": True}).status_code
        == 403
    )
