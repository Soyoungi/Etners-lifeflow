import json
from datetime import datetime

from app.extensions import db
from app.models import Inquiry, ServiceApplication
from app.models.application import APPLICATION_STATUS_LABELS
from app.services import file_storage, notification_service, personalization, service_rule_engine


class ApplicationError(Exception):
    pass


def _record_history(application, from_status, to_status, actor=None, note=None):
    from app.models import ApplicationStatusHistory

    history = ApplicationStatusHistory(
        application_id=application.id,
        from_status=from_status,
        to_status=to_status,
        changed_by=actor.id if actor else None,
        note=note,
    )
    db.session.add(history)
    return history


def apply(user, service, *, note=None, is_urgent=False, urgent_date=None, documents=None):
    """서비스 1건 신청. documents는 [(label, FileStorage), ...]."""
    context = personalization.build_context(user)
    existing = (
        ServiceApplication.query.filter_by(user_id=user.id, service_id=service.id)
        .order_by(ServiceApplication.applied_at.desc())
        .first()
    )
    status = service_rule_engine.resolve_status(service, context, existing)
    if status != "APPLY_AVAILABLE":
        raise ApplicationError(f"'{service.name}' 서비스는 현재 신청할 수 없습니다.")

    application = ServiceApplication(
        service_id=service.id,
        user_id=user.id,
        status="SUBMITTED",
        application_data=json.dumps({"note": note or ""}, ensure_ascii=False),
        is_urgent=bool(is_urgent),
        urgent_date=urgent_date,
    )
    db.session.add(application)
    db.session.flush()  # application.id 확보

    for label, file_storage_obj in documents or []:
        if file_storage_obj and file_storage_obj.filename:
            file_storage.save_upload(application.id, label, file_storage_obj)

    if note:
        db.session.add(Inquiry(application_id=application.id, user_id=user.id, question=note))

    _record_history(application, None, "SUBMITTED", actor=user)

    notification_service.notify(
        user.id,
        f"{service.name} 신청이 접수되었습니다",
        f"{service.name} 서비스 신청이 정상적으로 접수되었습니다. 처리 상태는 '나의 신청 내역'에서 확인하실 수 있습니다.",
        type_="STATUS_CHANGED",
    )
    db.session.commit()
    return application


def apply_batch(user, items):
    """items: [{"service": Service, "note":.., "is_urgent":.., "urgent_date":.., "documents":[..]}]"""
    results = []
    for item in items:
        service = item["service"]
        try:
            application = apply(
                user,
                service,
                note=item.get("note"),
                is_urgent=item.get("is_urgent", False),
                urgent_date=item.get("urgent_date"),
                documents=item.get("documents"),
            )
            results.append({"service": service, "success": True, "application": application, "error": None})
        except ApplicationError as exc:
            db.session.rollback()
            results.append({"service": service, "success": False, "application": None, "error": str(exc)})
    return results


def change_status(application, new_status, processed_by_user, note=None):
    previous_status = application.status
    application.status = new_status
    application.processed_at = datetime.utcnow()
    application.processed_by = processed_by_user.id

    _record_history(application, previous_status, new_status, actor=processed_by_user, note=note)

    label = APPLICATION_STATUS_LABELS.get(new_status, new_status)
    notif_type = "APPROVED" if new_status == "APPROVED" else (
        "REJECTED" if new_status == "REJECTED" else "STATUS_CHANGED"
    )
    notification_service.notify(
        application.user_id,
        f"{application.service.name} 신청 상태가 변경되었습니다",
        f"신청하신 '{application.service.name}' 서비스가 '{label}' 상태로 변경되었습니다.",
        type_=notif_type,
    )
    db.session.commit()
    return application


def cancel(application, reason, actor):
    previous_status = application.status
    application.status = "CANCELLED"
    application.cancel_reason = reason
    application.processed_at = datetime.utcnow()
    application.processed_by = actor.id

    _record_history(application, previous_status, "CANCELLED", actor=actor, note=reason)

    notification_service.notify(
        application.user_id,
        f"{application.service.name} 신청이 취소되었습니다",
        f"'{application.service.name}' 신청이 취소되었습니다. 사유: {reason}",
        type_="STATUS_CHANGED",
    )
    db.session.commit()
    return application


def answer_inquiry(inquiry, answer_text, admin_user):
    inquiry.answer = answer_text
    inquiry.answered_at = datetime.utcnow()
    inquiry.answered_by = admin_user.id

    notification_service.notify(
        inquiry.user_id,
        f"{inquiry.application.service.name} 문의에 답변이 등록되었습니다",
        answer_text,
        type_="STATUS_CHANGED",
    )
    db.session.commit()
    return inquiry
