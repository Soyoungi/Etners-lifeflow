"""사용자의 인사정보를 Rule Engine이 평가할 수 있는 context dict로 변환한다."""

from datetime import date

from app.models import Service, ServiceApplication
from app.services import service_rule_engine

# 카탈로그/대시보드에 노출해도 되는 서비스 상태(이용 불가는 어디서도 노출하지 않는다)
VISIBLE_STATUSES = {"AVAILABLE", "APPLY_AVAILABLE", "APPLIED", "IN_PROGRESS", "COMPLETED"}


def build_context(user):
    today = date.today()
    children = [f for f in user.family_members if f.relationship_type == "자녀"]
    child_ages = [c.age for c in children if c.age is not None]
    has_spouse = any(f.relationship_type == "배우자" for f in user.family_members)

    is_new_hire = user.tenure_years < 1

    return {
        "company_code": user.company.code if user.company else None,
        "department_name": user.department.name if user.department else None,
        "position": user.position,
        "title": user.title,
        "role": user.role,
        "gender": user.gender,
        "employment_type": user.employment_type,
        "work_location": user.work_location,
        "tenure_years": user.tenure_years,
        "is_new_hire": is_new_hire,
        "is_team_leader": user.title == "팀장",
        "is_officer": bool(user.title) and user.title != "팀원",
        "has_family": bool(user.family_members),
        "has_spouse": has_spouse,
        "has_children": bool(children),
        "children_count": len(children),
        "min_child_age": min(child_ages) if child_ages else None,
        "max_child_age": max(child_ages) if child_ages else None,
        "today": today,
    }


def get_personalized_services(user):
    """활성 서비스 전체에 대해 개인화 상태를 계산해 반환한다.

    반환값의 각 항목은 dict: {service, status, status_meta}
    """
    context = build_context(user)
    services = Service.query.filter_by(status="active").order_by(Service.priority.desc()).all()

    latest_applications = {}
    applications = (
        ServiceApplication.query.filter_by(user_id=user.id)
        .order_by(ServiceApplication.applied_at.desc())
        .all()
    )
    for application in applications:
        latest_applications.setdefault(application.service_id, application)

    results = []
    for service in services:
        latest_application = latest_applications.get(service.id)
        status = service_rule_engine.resolve_status(service, context, latest_application)
        results.append(
            {
                "service": service,
                "status": status,
                "status_meta": service_rule_engine.STATUS_META[status],
                "application": latest_application,
            }
        )
    return results


def get_visible_services(user):
    """이용 불가(NOT_AVAILABLE, EXPIRED) 서비스를 제외한 목록. 카탈로그/상세 접근 제어에 공용으로 사용."""
    personalized = get_personalized_services(user)
    return [item for item in personalized if item["status"] in VISIBLE_STATUSES]


def get_dashboard_data(user, recommend_limit=6):
    personalized = get_personalized_services(user)
    visible = [item for item in personalized if item["status"] in VISIBLE_STATUSES]

    recommend_priority = {"APPLY_AVAILABLE": 0, "AVAILABLE": 1}
    recommendable = [item for item in visible if item["status"] in recommend_priority]

    def rank_key(item):
        return (recommend_priority[item["status"]], -item["service"].priority)

    recommendable_sorted = sorted(recommendable, key=rank_key)

    # 1차: 카테고리별로 가장 우선순위 높은 서비스를 하나씩 우선 배정해 다양성을 확보한다.
    by_category = {}
    for item in recommendable_sorted:
        by_category.setdefault(item["service"].category_id, []).append(item)

    recommended = []
    for items in by_category.values():
        if len(recommended) >= recommend_limit:
            break
        recommended.append(items[0])

    # 2차: 남은 슬롯은 전체 우선순위 순으로 채운다.
    if len(recommended) < recommend_limit:
        picked_ids = {id(item) for item in recommended}
        for item in recommendable_sorted:
            if len(recommended) >= recommend_limit:
                break
            if id(item) not in picked_ids:
                recommended.append(item)
                picked_ids.add(id(item))

    recommended = sorted(recommended, key=rank_key)[:recommend_limit]

    by_category_visible = {}
    for item in visible:
        category = item["service"].category
        by_category_visible.setdefault(category, []).append(item)

    my_applications = [item for item in personalized if item["application"] is not None]

    return {
        "recommended": recommended,
        "visible": visible,
        "by_category": by_category_visible,
        "my_applications": my_applications,
    }
