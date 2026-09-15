from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.models import Inquiry, Service, ServiceApplication
from app.models.application import APPLICATION_STATUS_LABELS, APPLICATION_STATUSES
from app.routes.decorators import admin_required
from app.services import application_filters, application_service

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/applications")
@login_required
@admin_required
def applications():
    query, query_without_status = application_filters.build_filtered_query(
        ServiceApplication.query, request.args, admin=True
    )
    items = query.order_by(ServiceApplication.applied_at.desc()).all()
    counts = application_filters.status_counts(query_without_status)

    all_services = Service.query.order_by(Service.name).all()

    return render_template(
        "admin/applications.html",
        applications=items,
        counts=counts,
        statuses=APPLICATION_STATUSES,
        status_labels=APPLICATION_STATUS_LABELS,
        all_services=all_services,
        filters=request.args,
    )


@admin_bp.route("/applications/<int:application_id>/status", methods=["POST"])
@login_required
@admin_required
def update_status(application_id):
    application = ServiceApplication.query.get_or_404(application_id)
    new_status = request.form.get("status")
    if new_status not in APPLICATION_STATUSES:
        flash("잘못된 상태값입니다.")
    else:
        application_service.change_status(application, new_status, current_user)
        flash(f"{application.applicant.name}님의 신청 상태를 변경했습니다.")
    return redirect(url_for("admin.applications", **request.args))


@admin_bp.route("/inquiries/<int:inquiry_id>/reply", methods=["POST"])
@login_required
@admin_required
def reply_inquiry(inquiry_id):
    inquiry = Inquiry.query.get_or_404(inquiry_id)
    answer_text = (request.form.get("answer") or "").strip()
    if not answer_text:
        flash("답변 내용을 입력해주세요.")
    else:
        application_service.answer_inquiry(inquiry, answer_text, current_user)
        flash("답변이 등록되었습니다.")
    return redirect(url_for("admin.applications", **request.args))
