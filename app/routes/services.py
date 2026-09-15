from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.models import Service, ServiceApplication, ServiceCategory
from app.services import application_service, personalization, service_rule_engine

services_bp = Blueprint("services", __name__, url_prefix="/services")


def _parse_apply_fields(service, form, files):
    """단일/배치 신청 폼에서 서비스별 필드를 파싱한다. 필드명은 <name>__<service_id> 규칙."""
    sid = service.id

    is_urgent = form.get(f"urgent__{sid}") == "on"
    urgent_date = None
    if is_urgent:
        raw = (form.get(f"urgent_date__{sid}") or "").strip()
        if not raw:
            y = (form.get(f"urgent_year__{sid}") or "").strip()
            m = (form.get(f"urgent_month__{sid}") or "").strip()
            d = (form.get(f"urgent_day__{sid}") or "").strip()
            if y and m and d:
                try:
                    raw = f"{int(y):04d}-{int(m):02d}-{int(d):02d}"
                except ValueError:
                    raw = ""
        if raw:
            try:
                urgent_date = datetime.strptime(raw, "%Y-%m-%d").date()
            except ValueError:
                urgent_date = None

    note = (form.get(f"note__{sid}") or "").strip() or None

    documents = []
    for idx, doc_label in enumerate(service.required_documents_list):
        file_obj = files.get(f"document__{sid}__{idx}")
        if file_obj and file_obj.filename:
            documents.append((doc_label, file_obj))
    extra_file = files.get(f"document__{sid}__extra")
    if extra_file and extra_file.filename:
        documents.append(("기타 첨부파일", extra_file))

    return {
        "note": note,
        "is_urgent": is_urgent,
        "urgent_date": urgent_date,
        "documents": documents,
    }


@services_bp.route("/")
@login_required
def list_services():
    keyword = request.args.get("q", "").strip()
    category_id = request.args.get("category", type=int)

    items = personalization.get_visible_services(current_user)

    if keyword:
        items = [
            item
            for item in items
            if keyword in item["service"].name
            or (item["service"].description and keyword in item["service"].description)
            or keyword in item["service"].category.name
        ]
    if category_id:
        items = [item for item in items if item["service"].category_id == category_id]

    categories = ServiceCategory.query.filter_by(is_active=True).order_by(
        ServiceCategory.sort_order
    ).all()

    return render_template(
        "services/list.html",
        items=items,
        categories=categories,
        keyword=keyword,
        selected_category=category_id,
    )


@services_bp.route("/<int:service_id>")
@login_required
def detail(service_id):
    service = Service.query.get_or_404(service_id)
    context = personalization.build_context(current_user)
    latest_application = (
        ServiceApplication.query.filter_by(user_id=current_user.id, service_id=service.id)
        .order_by(ServiceApplication.applied_at.desc())
        .first()
    )
    status = service_rule_engine.resolve_status(service, context, latest_application)
    status_meta = service_rule_engine.STATUS_META[status]

    return render_template(
        "services/detail.html",
        service=service,
        status=status,
        status_meta=status_meta,
        latest_application=latest_application,
    )


@services_bp.route("/<int:service_id>/apply", methods=["POST"])
@login_required
def apply(service_id):
    service = Service.query.get_or_404(service_id)
    fields = _parse_apply_fields(service, request.form, request.files)

    try:
        application_service.apply(current_user, service, **fields)
        flash(f"'{service.name}' 서비스 신청이 접수되었습니다.")
    except application_service.ApplicationError as exc:
        flash(str(exc))

    return redirect(url_for("services.detail", service_id=service.id))


@services_bp.route("/review-apply")
@login_required
def review_apply():
    service_ids = request.args.getlist("service_ids", type=int)
    if not service_ids:
        flash("선택된 서비스가 없습니다.")
        return redirect(url_for("services.list_services"))

    context = personalization.build_context(current_user)
    services = []
    skipped = []
    for sid in service_ids:
        service = Service.query.get(sid)
        if not service:
            continue
        latest_application = (
            ServiceApplication.query.filter_by(user_id=current_user.id, service_id=service.id)
            .order_by(ServiceApplication.applied_at.desc())
            .first()
        )
        status = service_rule_engine.resolve_status(service, context, latest_application)
        if status == "APPLY_AVAILABLE":
            services.append(service)
        else:
            skipped.append(service.name)

    if skipped:
        flash("다음 서비스는 현재 신청할 수 없어 제외되었습니다: " + ", ".join(skipped))
    if not services:
        flash("신청 가능한 서비스가 없습니다.")
        return redirect(url_for("services.list_services"))

    return render_template("services/review_apply.html", services=services)


@services_bp.route("/apply-batch", methods=["POST"])
@login_required
def apply_batch_route():
    service_ids = request.form.getlist("service_ids", type=int)
    services = Service.query.filter(Service.id.in_(service_ids)).all() if service_ids else []

    items = []
    for service in services:
        fields = _parse_apply_fields(service, request.form, request.files)
        items.append({"service": service, **fields})

    results = application_service.apply_batch(current_user, items)
    success = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]

    if success:
        flash(f"{len(success)}건 신청이 접수되었습니다: " + ", ".join(r["service"].name for r in success))
    if failed:
        flash(
            f"{len(failed)}건은 신청에 실패했습니다: "
            + ", ".join(f"{r['service'].name}({r['error']})" for r in failed)
        )

    return redirect(url_for("applications.my_applications"))
