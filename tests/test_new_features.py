import io
from datetime import date, timedelta

from app.models import (
    ApplicationAttachment,
    ApplicationStatusHistory,
    Inquiry,
    Notification,
    Service,
    ServiceApplication,
)
from tests.conftest import make_service, make_user


def login(client, employee_number, password):
    return client.post(
        "/login",
        data={"employee_number": employee_number, "password": password},
        follow_redirects=True,
    )


def test_not_available_service_hidden_from_list(app, db, base_data):
    user = make_user(db, base_data, employee_number="300001", hire_date=date.today() - timedelta(days=200))
    user.set_password("pw")
    make_service(
        db, base_data, name="장기근속 전용 서비스",
        rules=[("tenure_years", ">=", "5", "AND")],
    )
    db.session.commit()

    client = app.test_client()
    login(client, "300001", "pw")
    resp = client.get("/services/")
    assert "장기근속 전용 서비스".encode("utf-8") not in resp.data


def test_batch_apply_with_urgent_and_attachment(app, db, base_data):
    user = make_user(
        db, base_data, employee_number="300002",
        hire_date=date.today() - timedelta(days=365 * 6),
    )
    user.set_password("pw")
    service_a = make_service(
        db, base_data, name="배치서비스A", required_documents='["증빙서류"]',
    )
    service_b = make_service(db, base_data, name="배치서비스B")
    db.session.commit()

    client = app.test_client()
    login(client, "300002", "pw")

    data = {
        "service_ids": [str(service_a.id), str(service_b.id)],
        f"urgent__{service_a.id}": "on",
        f"urgent_date__{service_a.id}": "2026-12-25",
        f"note__{service_b.id}": "문의합니다",
    }
    data[f"document__{service_a.id}__0"] = (io.BytesIO(b"dummy file content"), "test.txt")

    resp = client.post(
        "/services/apply-batch",
        data=data,
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert resp.status_code == 200

    app_a = ServiceApplication.query.filter_by(user_id=user.id, service_id=service_a.id).first()
    app_b = ServiceApplication.query.filter_by(user_id=user.id, service_id=service_b.id).first()
    assert app_a is not None and app_b is not None
    assert app_a.is_urgent is True
    assert app_a.urgent_date == date(2026, 12, 25)

    attachments = ApplicationAttachment.query.filter_by(application_id=app_a.id).all()
    assert len(attachments) == 1
    assert attachments[0].original_filename == "test.txt"

    inquiries = Inquiry.query.filter_by(application_id=app_b.id).all()
    assert len(inquiries) == 1
    assert inquiries[0].question == "문의합니다"

    history_a = ApplicationStatusHistory.query.filter_by(application_id=app_a.id).all()
    assert len(history_a) == 1
    assert history_a[0].to_status == "SUBMITTED"


def test_cancel_requires_reason_and_preserves_record(app, db, base_data):
    user = make_user(db, base_data, employee_number="300003")
    user.set_password("pw")
    service = make_service(db, base_data, name="취소테스트서비스")
    db.session.commit()

    client = app.test_client()
    login(client, "300003", "pw")
    client.post(f"/services/{service.id}/apply", data={f"note__{service.id}": ""}, follow_redirects=True)
    application = ServiceApplication.query.filter_by(user_id=user.id, service_id=service.id).first()

    # 사유 없이 취소 시도 -> 취소되지 않음
    resp = client.post(f"/applications/{application.id}/cancel", data={"reason": ""}, follow_redirects=True)
    assert resp.status_code == 200
    refreshed = ServiceApplication.query.get(application.id)
    assert refreshed.status != "CANCELLED"

    resp = client.post(
        f"/applications/{application.id}/cancel", data={"reason": "일정 변경으로 취소"}, follow_redirects=True
    )
    assert resp.status_code == 200
    refreshed = ServiceApplication.query.get(application.id)
    assert refreshed.status == "CANCELLED"
    assert refreshed.cancel_reason == "일정 변경으로 취소"

    history = ApplicationStatusHistory.query.filter_by(application_id=application.id).order_by(
        ApplicationStatusHistory.created_at.desc()
    ).first()
    assert history.to_status == "CANCELLED"


def test_inquiry_ask_and_admin_reply(app, db, base_data):
    user = make_user(db, base_data, employee_number="300004")
    user.set_password("pw")
    admin = make_user(db, base_data, employee_number="300099", role="admin", email="admin2@etners.com")
    admin.set_password("adminpw")
    service = make_service(db, base_data, name="문의테스트서비스")
    db.session.commit()

    client = app.test_client()
    login(client, "300004", "pw")
    client.post(f"/services/{service.id}/apply", data={f"note__{service.id}": ""}, follow_redirects=True)
    application = ServiceApplication.query.filter_by(user_id=user.id, service_id=service.id).first()

    client.post(
        f"/applications/{application.id}/inquiries",
        data={"question": "처리 기간이 얼마나 걸리나요?"},
        follow_redirects=True,
    )
    inquiry = Inquiry.query.filter_by(application_id=application.id).first()
    assert inquiry is not None
    assert inquiry.answer is None

    client.get("/logout")
    login(client, "300099", "adminpw")
    client.post(
        f"/admin/inquiries/{inquiry.id}/reply",
        data={"answer": "영업일 기준 3일 소요됩니다."},
        follow_redirects=True,
    )

    refreshed = Inquiry.query.get(inquiry.id)
    assert refreshed.answer == "영업일 기준 3일 소요됩니다."
    assert refreshed.answered_by == admin.id

    notif = Notification.query.filter_by(user_id=user.id).order_by(Notification.id.desc()).first()
    assert "영업일" in notif.message


def test_applications_filter_by_status_and_service(app, db, base_data):
    user = make_user(db, base_data, employee_number="300005")
    user.set_password("pw")
    service_a = make_service(db, base_data, name="필터서비스A")
    service_b = make_service(db, base_data, name="필터서비스B")
    db.session.commit()

    client = app.test_client()
    login(client, "300005", "pw")
    client.post(f"/services/{service_a.id}/apply", data={f"note__{service_a.id}": ""}, follow_redirects=True)
    client.post(f"/services/{service_b.id}/apply", data={f"note__{service_b.id}": ""}, follow_redirects=True)

    resp = client.get(f"/applications/?service_id={service_a.id}")
    body = resp.get_data(as_text=True)
    assert "<strong>필터서비스A</strong>" in body
    assert "<strong>필터서비스B</strong>" not in body

    resp = client.get("/applications/?status=SUBMITTED")
    body = resp.get_data(as_text=True)
    assert "<strong>필터서비스A</strong>" in body and "<strong>필터서비스B</strong>" in body

    resp = client.get("/applications/?status=APPROVED")
    body = resp.get_data(as_text=True)
    assert "<strong>필터서비스A</strong>" not in body and "<strong>필터서비스B</strong>" not in body


def test_admin_applicant_search_filter(app, db, base_data):
    alice = make_user(db, base_data, employee_number="300006", name="앨리스", email="alice@etners.com")
    alice.set_password("pw")
    bob = make_user(db, base_data, employee_number="300007", name="밥", email="bob@etners.com")
    bob.set_password("pw")
    admin = make_user(db, base_data, employee_number="300098", role="admin", email="admin3@etners.com")
    admin.set_password("adminpw")
    service = make_service(db, base_data, name="검색테스트서비스")
    db.session.commit()

    client = app.test_client()
    login(client, "300006", "pw")
    client.post(f"/services/{service.id}/apply", data={f"note__{service.id}": ""}, follow_redirects=True)
    client.get("/logout")

    login(client, "300007", "pw")
    client.post(f"/services/{service.id}/apply", data={f"note__{service.id}": ""}, follow_redirects=True)
    client.get("/logout")

    login(client, "300098", "adminpw")
    resp = client.get("/admin/applications?applicant=앨리스")
    body = resp.get_data(as_text=True)
    assert "앨리스" in body
    assert "밥" not in body
