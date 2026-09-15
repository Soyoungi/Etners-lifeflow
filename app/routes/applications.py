import os

from flask import Blueprint, abort, flash, redirect, render_template, request, send_file, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.models import ApplicationAttachment, Inquiry, Service, ServiceApplication
from app.models.application import APPLICATION_STATUS_LABELS
from app.services import application_filters, application_service, file_storage

applications_bp = Blueprint("applications", __name__, url_prefix="/applications")


@applications_bp.route("/")
@login_required
def my_applications():
    base_query = ServiceApplication.query.filter_by(user_id=current_user.id)
    query, query_without_status = application_filters.build_filtered_query(base_query, request.args)

    items = query.order_by(ServiceApplication.applied_at.desc()).all()
    counts = application_filters.status_counts(query_without_status)

    services_for_filter = (
        Service.query.join(ServiceApplication)
        .filter(ServiceApplication.user_id == current_user.id)
        .distinct()
        .order_by(Service.name)
        .all()
    )

    return render_template(
        "applications/list.html",
        applications=items,
        counts=counts,
        status_labels=APPLICATION_STATUS_LABELS,
        services_for_filter=services_for_filter,
        filters=request.args,
    )


@applications_bp.route("/<int:application_id>/cancel", methods=["POST"])
@login_required
def cancel(application_id):
    application = ServiceApplication.query.get_or_404(application_id)
    if application.user_id != current_user.id:
        abort(403)
    if application.status not in ("SUBMITTED", "RECEIVED", "REVIEWING", "SUPPLEMENT_REQUIRED"):
        flash("이미 처리가 진행되어 취소할 수 없습니다.")
        return redirect(url_for("applications.my_applications"))

    reason = (request.form.get("reason") or "").strip()
    if not reason:
        flash("취소 사유를 입력해주세요.")
        return redirect(url_for("applications.my_applications"))

    application_service.cancel(application, reason, current_user)
    flash("신청이 취소되었습니다.")
    return redirect(url_for("applications.my_applications"))


@applications_bp.route("/<int:application_id>/inquiries", methods=["POST"])
@login_required
def ask(application_id):
    application = ServiceApplication.query.get_or_404(application_id)
    if application.user_id != current_user.id:
        abort(403)

    question = (request.form.get("question") or "").strip()
    if not question:
        flash("문의 내용을 입력해주세요.")
        return redirect(url_for("applications.my_applications"))

    db.session.add(Inquiry(application_id=application.id, user_id=current_user.id, question=question))
    db.session.commit()
    flash("문의가 등록되었습니다.")
    return redirect(url_for("applications.my_applications"))


@applications_bp.route("/<int:application_id>/attachments/<int:attachment_id>")
@login_required
def download_attachment(application_id, attachment_id):
    application = ServiceApplication.query.get_or_404(application_id)
    if application.user_id != current_user.id and not current_user.is_admin:
        abort(403)

    attachment = ApplicationAttachment.query.get_or_404(attachment_id)
    if attachment.application_id != application.id:
        abort(404)

    kind, value = file_storage.resolve_download(attachment)
    if kind == "url":
        return redirect(value)

    if not os.path.exists(value):
        abort(404)
    return send_file(value, as_attachment=True, download_name=attachment.original_filename)
