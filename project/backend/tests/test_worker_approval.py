from datetime import datetime, timedelta

from sqlalchemy import select

from app.models import AuditEvent, Notification
from tests.helpers import account, booking, complete, service_request, worker


def decide(api, admin, professional, approved, note="Profile details checked by administrator."):
    return api.patch(
        f"/api/v1/admin/workers/{professional['id']}/verification",
        headers=admin,
        json={"verified": approved, "note": note},
    )


def test_admin_notifications_for_ready_applications_and_resubmissions_are_not_duplicated(api):
    admin, _ = account(api, "admin")
    second_admin, _ = account(api, "admin")
    owner, user = account(api, "worker")
    customer, _ = account(api)
    professional = {"id": user["workerId"]}

    def notices(headers):
        return api.get("/api/v1/notifications", headers=headers).json()["data"]

    def pending():
        return api.get("/api/v1/admin/dashboard", headers=admin).json()["data"][
            "pendingApplications"
        ]

    assert notices(admin) == [] and pending() == 0
    assert (
        api.patch(
            "/api/v1/worker/profile", headers=owner, json={"bio": "Household tap and pipe repairs."}
        ).status_code
        == 200
    )
    assert notices(admin) == [] and pending() == 0
    ready = {"categories": ["Plumbing"], "serviceTowns": ["Colombo"], "rateLkr": 2500}
    assert (
        api.patch("/api/v1/worker/profile", headers=owner, json=ready).json()["data"]["reviewReady"]
        is True
    )
    assert pending() == 1
    for headers in (admin, second_admin):
        notification = notices(headers)[0]
        assert len(notices(headers)) == 1
        assert notification["message"].startswith(
            "Worker application ready for review: " + user["name"]
        )
        assert "Changed: Biography, Service categories, Service towns" in notification["message"]
        assert (
            notification["targetPath"]
            == f"/admin/records?entity=workers&recordId={professional['id']}&detailTab=changes"
        )
        assert notification["readAt"] is None
    assert notices(customer) == [] and notices(owner) == []
    notification_id = notices(admin)[0]["id"]
    # Notifications created before tabs existed must still open the change request.
    with api.app.state.sessions() as db:
        legacy = db.get(Notification, notification_id)
        legacy.target_path = legacy.target_path.split("&detailTab=")[0]
        db.commit()
    assert notices(admin)[0]["targetPath"].endswith("&detailTab=changes")
    for headers in (owner, customer, second_admin):
        assert (
            api.patch(
                f"/api/v1/notifications/{notification_id}", headers=headers, json={"read": True}
            ).status_code
            == 404
        )
    assert (
        api.patch(
            f"/api/v1/notifications/{notification_id}", headers=admin, json={"read": True}
        ).status_code
        == 200
    )
    for payload in (ready, {"phone": "0771234567"}, {"rateLkr": 2600}):
        assert api.patch("/api/v1/worker/profile", headers=owner, json=payload).status_code == 200
    assert len(notices(admin)) == 1 and pending() == 1

    assert (
        decide(
            api, admin, professional, False, "Please expand your description of plumbing services."
        ).status_code
        == 200
    )
    assert pending() == 0
    # Invalid corrections must not clear feedback or notify admins prematurely.
    response = api.patch("/api/v1/worker/profile", headers=owner, json={"bio": ""})
    assert response.status_code == 422, response.text
    assert (
        api.get("/api/v1/worker/profile", headers=owner).json()["data"]["approvalStatus"]
        == "changes_requested"
    )
    assert len(notices(admin)) == 1 and pending() == 0
    corrected = {"bio": "I fix leaking pipes, taps and damaged plumbing fittings."}
    assert api.patch("/api/v1/worker/profile", headers=owner, json=corrected).status_code == 200
    assert pending() == 1
    assert len(notices(admin)) == 2 and len(notices(second_admin)) == 2
    assert notices(admin)[0]["message"].startswith("Worker application resubmitted:")
    assert api.patch("/api/v1/worker/profile", headers=owner, json=corrected).status_code == 200
    assert len(notices(admin)) == 2
    assert decide(api, admin, professional, True).status_code == 200
    assert pending() == 0
    assert (
        api.patch("/api/v1/worker/profile", headers=owner, json={"available": True}).status_code
        == 200
    )
    assert len(notices(admin)) == 2
    assert (
        api.patch("/api/v1/worker/profile", headers=owner, json={"yearsExperience": 8}).status_code
        == 200
    )
    assert len(notices(admin)) == 3 and pending() == 1


def test_failed_profile_update_does_not_notify_admins(api):
    admin, _ = account(api, "admin")
    owner, _ = account(api, "worker")
    response = api.patch("/api/v1/worker/profile", headers=owner, json={"available": True})
    assert response.status_code == 422
    assert api.get("/api/v1/notifications", headers=admin).json()["data"] == []
    assert (
        api.get("/api/v1/admin/dashboard", headers=admin).json()["data"]["pendingApplications"] == 0
    )


def test_pending_worker_hidden_until_admin_approval_and_cannot_bypass_booking(api):
    owner, professional, _ = worker(api, approved=False)
    customer, _ = account(api)
    admin, _ = account(api, "admin")
    request = service_request(api, customer)
    path = f"/api/v1/workers/{professional['id']}"
    matches = f"/api/v1/requests/{request['id']}/recommendations"
    assert professional["approvalStatus"] == "pending"
    assert api.get("/api/v1/workers").json()["data"] == []
    assert api.get(path).status_code == 404
    assert api.post(matches, headers=customer, json={}).json()["data"]["recommendations"] == []
    payload = {
        "requestId": request["id"],
        "workerId": professional["id"],
        "scheduledAt": request["preferredAt"],
        "scheduledEndAt": (
            datetime.fromisoformat(request["preferredAt"]) + timedelta(hours=4)
        ).isoformat(),
        "deadlineAt": (
            datetime.fromisoformat(request["preferredAt"]) + timedelta(hours=4)
        ).isoformat(),
    }
    assert api.post("/api/v1/bookings", headers=customer, json=payload).status_code == 409
    for headers in (owner, customer):
        assert decide(api, headers, professional, True).status_code == 403
    for field in ("verified", "approvalStatus", "reviewNote"):
        assert (
            api.patch("/api/v1/worker/profile", headers=owner, json={field: True}).status_code
            == 422
        )
    assert api.get(f"/api/v1/admin/workers/{professional['id']}", headers=admin).status_code == 200
    assert decide(api, admin, professional, True).json()["data"]["approvalStatus"] == "approved"
    public = api.get(path).json()["data"]
    assert public["verified"] is True and public["reviewNote"] is None
    assert api.get("/api/v1/workers").json()["data"][0]["id"] == professional["id"]
    assert (
        api.post(matches, headers=customer, json={}).json()["data"]["recommendations"][0][
            "workerId"
        ]
        == professional["id"]
    )
    assert api.post("/api/v1/bookings", headers=customer, json=payload).status_code == 201


def test_corrections_resubmission_revocation_and_existing_jobs(api):
    owner, professional, user = worker(api, approved=False)
    admin, _ = account(api, "admin")
    customer, _ = account(api)
    note = "Please clarify which plumbing repairs you offer."
    assert decide(api, admin, professional, False, note).status_code == 200
    profile = api.get("/api/v1/worker/profile", headers=owner).json()["data"]
    assert profile["approvalStatus"] == "changes_requested"
    assert profile["reviewNote"] == note
    notices = api.get("/api/v1/notifications", headers=owner).json()["data"]
    assert note in notices[0]["message"]
    response = api.patch(
        "/api/v1/worker/profile",
        headers=owner,
        json={"bio": "I repair household taps, drains and leaking pipes."},
    )
    assert response.json()["data"]["approvalStatus"] == "pending"
    assert response.json()["data"]["reviewNote"] is None
    assert decide(api, admin, professional, True).status_code == 200
    first = booking(api, customer, service_request(api, customer), professional)
    assert (
        decide(
            api, admin, professional, False, "Please correct your listed service details."
        ).status_code
        == 200
    )
    assert api.get(f"/api/v1/workers/{professional['id']}").status_code == 404
    # Withdrawing listing approval must not strand existing customers or lose outcomes.
    complete(api, owner, first["id"], customer)
    request = service_request(api, customer)
    assert (
        api.post(
            f"/api/v1/requests/{request['id']}/recommendations", headers=customer, json={}
        ).json()["data"]["recommendations"]
        == []
    )
    with api.app.state.sessions() as db:
        events = db.scalars(
            select(AuditEvent).where(AuditEvent.record_id == professional["id"])
        ).all()
        assert sum(event.action == "worker.verification" for event in events) == 3
        assert any(
            event.action == "worker.review_resubmitted" and event.actor_id == user["id"]
            for event in events
        )


def test_incomplete_profile_cannot_be_approved_and_material_edits_need_reapproval(api):
    owner, user = account(api, "worker")
    admin, _ = account(api, "admin")
    assert decide(api, admin, {"id": user["workerId"]}, True).status_code == 409
    owner, professional, _ = worker(api, approved=False)
    assert decide(api, admin, professional, True).status_code == 200
    # Routine updates and an unchanged full-form save retain approval.
    for payload in (
        {"available": False},
        {"available": True, "rateLkr": 2700},
        {
            "name": professional["name"],
            "bio": professional["bio"],
            "categories": professional["categories"],
            "serviceTowns": professional["serviceTowns"],
        },
    ):
        assert (
            api.patch("/api/v1/worker/profile", headers=owner, json=payload).json()["data"][
                "verified"
            ]
            is True
        )
    for payload in (
        {"categories": ["Electrical"]},
        {"bio": "A corrected description of my electrical work."},
        {"yearsExperience": 6},
        {"name": "Changed Professional"},
        {"serviceTowns": ["Colombo", "Kandy"]},
        {"town": "Kandy"},
    ):
        response = api.patch("/api/v1/worker/profile", headers=owner, json=payload)
        assert response.status_code == 200, response.text
        assert response.json()["data"]["approvalStatus"] == "pending"
        assert api.get(f"/api/v1/workers/{professional['id']}").status_code == 404
        assert decide(api, admin, professional, True).status_code == 200


def test_profile_change_history_survives_pending_edits_and_is_private(api):
    admin, _ = account(api, "admin")
    owner, professional, _ = worker(api, approved=False)
    assert decide(api, admin, professional, True).status_code == 200
    path = f"/api/v1/admin/workers/{professional['id']}"

    def changes():
        result = api.get(path, headers=admin).json()["data"]["profileChanges"]
        return {item["field"]: item for item in result}

    first = {
        "yearsExperience": 8,
        "bio": "I repair household pipes and electrical fittings safely.",
    }
    response = api.patch("/api/v1/worker/profile", headers=owner, json=first)
    assert response.status_code == 200
    assert response.json()["data"]["approvalStatus"] == "pending"
    assert changes()["yearsExperience"]["before"] == 5
    assert changes()["yearsExperience"]["after"] == 8
    assert changes()["bio"]["before"] == professional["bio"]
    assert changes()["bio"]["after"] == first["bio"]
    assert api.get(path).status_code == 401
    assert api.get(path, headers=owner).status_code == 403
    notifications = api.get("/api/v1/notifications", headers=admin).json()["data"]
    assert "Changed: Biography, Experience" in notifications[0]["message"]
    before_count = len(notifications)
    assert api.patch("/api/v1/worker/profile", headers=owner, json=first).status_code == 200
    assert len(api.get("/api/v1/notifications", headers=admin).json()["data"]) == before_count
    assert (
        api.patch("/api/v1/worker/profile", headers=owner, json={"yearsExperience": 9}).status_code
        == 200
    )
    assert changes()["yearsExperience"]["before"] == 5
    assert changes()["yearsExperience"]["after"] == 9
    notifications = api.get("/api/v1/notifications", headers=admin).json()["data"]
    assert len(notifications) == before_count + 1
    assert "Worker application updated:" in notifications[0]["message"]
    assert "Changed: Experience" in notifications[0]["message"]
    assert (
        decide(api, admin, professional, False, "Please correct the biography details.").status_code
        == 200
    )
    assert (
        api.patch(
            "/api/v1/worker/profile", headers=owner, json={"bio": professional["bio"]}
        ).status_code
        == 200
    )
    assert set(changes()) == {"yearsExperience"}
    assert decide(api, admin, professional, True).status_code == 200
    assert changes() == {}
    public = api.get(f"/api/v1/workers/{professional['id']}").json()["data"]
    assert public["profileChanges"] == []
    with api.app.state.sessions() as db:
        decisions = db.scalars(
            select(AuditEvent)
            .where(
                AuditEvent.record_id == professional["id"],
                AuditEvent.action == "worker.verification",
            )
            .order_by(AuditEvent.created_at)
        ).all()
        reviewed = decisions[-1].details
        assert reviewed["profileChanges"][0]["before"] == 5
        assert reviewed["profileChanges"][0]["after"] == 9
        assert reviewed["reviewedProfile"]["yearsExperience"] == 9
    assert (
        api.patch("/api/v1/worker/profile", headers=owner, json={"yearsExperience": 10}).status_code
        == 200
    )
    assert changes()["yearsExperience"]["before"] == 9
