from datetime import datetime, time

from app.extensions import db
from app.models import ServiceApplication, User
from app.models.application import APPLICATION_STATUSES


def _parse_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def build_filtered_query(base_query, args, admin=False):
    """공용 필터(기간/서비스/상태, 관리자는 신청자 검색)를 적용한다.

    반환값: (상태까지 적용된 쿼리, 상태 필터만 제외한 쿼리) — 후자는 상태별 건수 집계에 사용.
    """
    query = base_query

    date_from = _parse_date(args.get("date_from"))
    date_to = _parse_date(args.get("date_to"))
    if date_from:
        query = query.filter(ServiceApplication.applied_at >= datetime.combine(date_from, time.min))
    if date_to:
        query = query.filter(ServiceApplication.applied_at <= datetime.combine(date_to, time.max))

    service_id = args.get("service_id", type=int)
    if service_id:
        query = query.filter(ServiceApplication.service_id == service_id)

    if admin:
        applicant = (args.get("applicant") or "").strip()
        if applicant:
            query = query.join(User, ServiceApplication.user_id == User.id).filter(
                db.or_(
                    User.name.ilike(f"%{applicant}%"),
                    User.employee_number.ilike(f"%{applicant}%"),
                )
            )

    query_without_status = query
    status = args.get("status")
    if status:
        query = query.filter(ServiceApplication.status == status)

    return query, query_without_status


def status_counts(query_without_status):
    rows = (
        query_without_status.with_entities(
            ServiceApplication.status, db.func.count(ServiceApplication.id)
        )
        .group_by(ServiceApplication.status)
        .all()
    )
    counts = {status: 0 for status in APPLICATION_STATUSES}
    for status, count in rows:
        counts[status] = count
    return counts
