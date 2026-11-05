from sqlalchemy import func, select

from app.models import AuditEvent, User
from tests.helpers import account, worker


def test_health_documentation_and_catalog_are_public_but_admin_is_protected(api):
    assert api.get("/health").status_code == 200
    assert api.get("/health/ready").json()["data"]["database"] == "postgresql"
    assert api.get("/docs").status_code == 200
    spec = api.get("/openapi.json").json()
    assert spec["paths"]["/api/v1/bookings"]["post"]["security"]
    assert api.get("/api/v1/admin/dashboard").status_code == 401
    for role in ["customer", "worker"]:
        headers, _ = account(api, role)
        assert api.get("/api/v1/admin/dashboard", headers=headers).status_code == 403
        assert api.get("/api/v1/admin/customers", headers=headers).status_code == 403
    labels = [record["label"] for record in api.get("/api/v1/categories").json()["data"]]
    assert labels == [
        "Carpentry",
        "Electrical",
        "Plumbing",
        "Welding",
    ]


def test_admin_can_inspect_records_edit_category_and_audit_verification(api):
    admin, _ = account(api, "admin")
    _, professional, _ = worker(api)
    account(api)
    counts = api.get("/api/v1/admin/dashboard", headers=admin).json()["data"]["counts"]
    assert counts["workers"] == 1
    assert counts["customers"] == 1
    assert counts["bookings"] == 0
    for entity in ["customers", "workers", "categories", "requests", "bookings", "reviews"]:
        response = api.get(f"/api/v1/admin/{entity}", headers=admin)
        assert response.status_code == 200, response.text
        assert "password" not in response.text.lower()
    assert api.get(f"/api/v1/admin/workers/{professional['id']}", headers=admin).status_code == 200
    payload = {
        "description": "Updated plumbing category details.",
        "exampleRequest": "Repair the leaking pipe near the kitchen sink.",
    }
    assert (
        api.patch("/api/v1/admin/categories/cat08", headers=admin, json=payload).status_code == 200
    )
    assert (
        api.get("/api/v1/admin/categories/cat08", headers=admin).json()["data"]["description"]
        == payload["description"]
    )
    assert (
        api.patch(
            "/api/v1/admin/categories/cat08",
            headers=admin,
            json={**payload, "label": "Changed label"},
        ).status_code
        == 422
    )
    response = api.patch(
        f"/api/v1/admin/workers/{professional['id']}/verification",
        headers=admin,
        json={"verified": True, "note": "Documents checked by the administrator."},
    )
    assert response.status_code == 200
    assert api.get(f"/api/v1/workers/{professional['id']}").json()["data"]["verified"] is True
    with api.app.state.sessions() as db:
        assert db.scalar(select(func.count()).select_from(AuditEvent)) == 2


def test_malformed_and_forbidden_fields_do_not_echo_passwords(api):
    secret = "must-not-appear-in-error-response"
    response = api.post("/api/v1/auth/register", json={"password": secret, "role": "admin"})
    assert response.status_code == 422
    assert secret not in response.text
    with api.app.state.sessions() as db:
        assert db.scalar(select(func.count()).select_from(User)) == 0
    assert api.get("/unknown-api").json()["error"]["code"] == "http_error"
