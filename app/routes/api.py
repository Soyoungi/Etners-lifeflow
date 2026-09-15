from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required, login_user, logout_user

from app.extensions import db
from app.models import Notification, Service, ServiceApplication
from app.models.application import APPLICATION_STATUSES
from app.models.user import User
from app.routes.decorators import admin_required
from app.services import application_service, personalization, service_rule_engine

api_bp = Blueprint("api", __name__, url_prefix="/api")


def ok(data=None, **extra):
    payload = {"success": True, "data": data}
    payload.update(extra)
    return jsonify(payload)


def fail(message, status_code=400):
    response = jsonify({"success": False, "error": message})
    response.status_code = status_code
    return response


def serialize_user(user):
    return {
        "id": user.id,
        "employee_number": user.employee_number,
        "name": user.name,
        "company": user.company.name if user.company else None,
        "department": user.department.name if user.department else None,
        "position": user.position,
        "title": user.title,
        "role": user.role,
        "hire_date": user.hire_date.isoformat(),
        "tenure_label": user.tenure_label,
        "employment_type": user.employment_type,
        "work_location": user.work_location,
    }


def serialize_service(service, status=None):
    payload = {
        "id": service.id,
        "name": service.name,
        "category": service.category.name,
        "description": service.description,
        "thumbnail": service.thumbnail,
        "application_start_date": service.application_start_date.isoformat()
        if service.application_start_date
        else None,
        "application_end_date": service.application_end_date.isoformat()
        if service.application_end_date
        else None,
    }
    if status:
        payload["status"] = status
    return payload


def serialize_application(application):
    return {
        "id": application.id,
        "service_id": application.service_id,
        "service_name": application.service.name,
        "status": application.status,
        "status_label": application.status_label,
        "status_color": application.status_color,
        "is_urgent": application.is_urgent,
        "urgent_date": application.urgent_date.isoformat() if application.urgent_date else None,
        "cancel_reason": application.cancel_reason,
        "applied_at": application.applied_at.isoformat() if application.applied_at else None,
        "processed_at": application.processed_at.isoformat() if application.processed_at else None,
    }


# ---- 인증 ----


@api_bp.route("/auth/login", methods=["POST"])
def auth_login():
    body = request.get_json(silent=True) or {}
    employee_number = body.get("employee_number", "")
    password = body.get("password", "")

    user = User.query.filter_by(employee_number=employee_number).first()
    if user is None or not user.is_active or not user.check_password(password):
        return fail("사번 또는 비밀번호가 올바르지 않습니다.", 401)

    login_user(user)
    return ok(serialize_user(user))


@api_bp.route("/auth/logout", methods=["POST"])
@login_required
def auth_logout():
    logout_user()
    return ok()


@api_bp.route("/auth/me")
@login_required
def auth_me():
    return ok(serialize_user(current_user))


# ---- 사용자 ----


@api_bp.route("/me")
@login_required
def me():
    return ok(serialize_user(current_user))


@api_bp.route("/me/services")
@login_required
def me_services():
    items = personalization.get_visible_services(current_user)
    return ok([serialize_service(item["service"], item["status"]) for item in items])


@api_bp.route("/me/personalized-services")
@login_required
def me_personalized_services():
    data = personalization.get_dashboard_data(current_user)
    return ok(
        {
            "recommended": [
                {**serialize_service(item["service"]), "status": item["status"]}
                for item in data["recommended"]
            ],
            "available": [
                {**serialize_service(item["service"]), "status": item["status"]}
                for item in data["visible"]
            ],
        }
    )


@api_bp.route("/me/applications")
@login_required
def me_applications():
    items = (
        ServiceApplication.query.filter_by(user_id=current_user.id)
        .order_by(ServiceApplication.applied_at.desc())
        .all()
    )
    return ok([serialize_application(a) for a in items])


@api_bp.route("/me/notifications")
@login_required
def me_notifications():
    items = (
        Notification.query.filter_by(user_id=current_user.id)
        .order_by(Notification.created_at.desc())
        .all()
    )
    return ok(
        [
            {
                "id": n.id,
                "title": n.title,
                "message": n.message,
                "type": n.type,
                "is_read": n.is_read,
                "created_at": n.created_at.isoformat(),
            }
            for n in items
        ]
    )


@api_bp.route("/me/notifications/mark-read", methods=["POST"])
@login_required
def me_notifications_mark_read():
    unread = Notification.query.filter_by(user_id=current_user.id, is_read=False).all()
    for n in unread:
        n.is_read = True
    db.session.commit()
    return ok({"marked": len(unread)})


# ---- 서비스 ----


@api_bp.route("/services")
@login_required
def list_services():
    items = personalization.get_visible_services(current_user)
    return ok([serialize_service(item["service"], item["status"]) for item in items])


@api_bp.route("/services/<int:service_id>")
@login_required
def get_service(service_id):
    service = Service.query.get_or_404(service_id)
    context = personalization.build_context(current_user)
    latest_application = (
        ServiceApplication.query.filter_by(user_id=current_user.id, service_id=service.id)
        .order_by(ServiceApplication.applied_at.desc())
        .first()
    )
    status = service_rule_engine.resolve_status(service, context, latest_application)
    return ok(serialize_service(service, status))


@api_bp.route("/services/<int:service_id>/availability")
@login_required
def service_availability(service_id):
    service = Service.query.get_or_404(service_id)
    context = personalization.build_context(current_user)
    latest_application = (
        ServiceApplication.query.filter_by(user_id=current_user.id, service_id=service.id)
        .order_by(ServiceApplication.applied_at.desc())
        .first()
    )
    status = service_rule_engine.resolve_status(service, context, latest_application)
    return ok({"service_id": service.id, "status": status})


# ---- 서비스 신청 ----


@api_bp.route("/services/<int:service_id>/apply", methods=["POST"])
@login_required
def api_apply(service_id):
    service = Service.query.get_or_404(service_id)
    body = request.get_json(silent=True) or {}
    try:
        application = application_service.apply(current_user, service, note=body.get("note"))
    except application_service.ApplicationError as exc:
        return fail(str(exc), 409)
    return ok(serialize_application(application))


@api_bp.route("/applications")
@login_required
def api_applications():
    items = (
        ServiceApplication.query.filter_by(user_id=current_user.id)
        .order_by(ServiceApplication.applied_at.desc())
        .all()
    )
    return ok([serialize_application(a) for a in items])


@api_bp.route("/applications/<int:application_id>")
@login_required
def api_application_detail(application_id):
    application = ServiceApplication.query.get_or_404(application_id)
    if application.user_id != current_user.id and not current_user.is_admin:
        return fail("접근 권한이 없습니다.", 403)
    return ok(serialize_application(application))


# ---- 관리자 (Phase 4 범위: 신청 상태 변경만) ----


@api_bp.route("/admin/applications")
@login_required
@admin_required
def admin_applications():
    status_filter = request.args.get("status")
    query = ServiceApplication.query
    if status_filter:
        query = query.filter_by(status=status_filter)
    items = query.order_by(ServiceApplication.applied_at.desc()).all()
    return ok([serialize_application(a) for a in items])


@api_bp.route("/admin/applications/<int:application_id>", methods=["PUT"])
@login_required
@admin_required
def admin_update_application(application_id):
    application = ServiceApplication.query.get_or_404(application_id)
    body = request.get_json(silent=True) or {}
    new_status = body.get("status")
    if new_status not in APPLICATION_STATUSES:
        return fail("잘못된 상태값입니다.")
    application_service.change_status(application, new_status, current_user)
    return ok(serialize_application(application))
