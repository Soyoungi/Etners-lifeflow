from datetime import date, timedelta

from app.models import Notification, ServiceApplication
from tests.conftest import make_service, make_user


def login(client, employee_number, password):
    return client.post(
        "/login",
        data={"employee_number": employee_number, "password": password},
        follow_redirects=True,
    )


def test_apply_flow_creates_application_and_notification(app, db, base_data):
    user = make_user(
        db, base_data, employee_number="200001",
        hire_date=date.today() - timedelta(days=365 * 6),
    )
    user.set_password("pw1234")
    admin = make_user(
        db, base_data, employee_number="200099", role="admin", email="admin@etners.com",
    )
    admin.set_password("adminpw")
    service = make_service(
        db, base_data, name="장기근속 포상",
        rules=[("tenure_years", ">=", "5", "AND")],
    )
    db.session.commit()

    client = app.test_client()
    resp = login(client, "200001", "pw1234")
    assert resp.status_code == 200

    resp = client.post(
        f"/services/{service.id}/apply",
        data={f"note__{service.id}": "신청합니다"},
        follow_redirects=True,
    )
    assert resp.status_code == 200

    application = ServiceApplication.query.filter_by(user_id=user.id, service_id=service.id).first()
    assert application is not None
    assert application.status == "SUBMITTED"

    notif = Notification.query.filter_by(user_id=user.id).first()
    assert notif is not None

    resp = client.get("/applications/")
    assert "장기근속 포상".encode("utf-8") in resp.data

    client.get("/logout")
    login(client, "200099", "adminpw")

    resp = client.post(
        f"/admin/applications/{application.id}/status",
        data={"status": "APPROVED"},
        follow_redirects=True,
    )
    assert resp.status_code == 200

    updated = ServiceApplication.query.get(application.id)
    assert updated.status == "APPROVED"
    assert updated.processed_by == admin.id

    notif_count = Notification.query.filter_by(user_id=user.id).count()
    assert notif_count == 2


def test_cannot_apply_when_not_eligible(app, db, base_data):
    user = make_user(
        db, base_data, employee_number="200002",
        hire_date=date.today() - timedelta(days=200),
    )
    user.set_password("pw1234")
    service = make_service(
        db, base_data, name="장기근속 포상",
        rules=[("tenure_years", ">=", "5", "AND")],
    )
    db.session.commit()

    client = app.test_client()
    login(client, "200002", "pw1234")

    resp = client.post(f"/services/{service.id}/apply", data={f"note__{service.id}": ""}, follow_redirects=True)
    assert resp.status_code == 200

    application = ServiceApplication.query.filter_by(user_id=user.id, service_id=service.id).first()
    assert application is None
