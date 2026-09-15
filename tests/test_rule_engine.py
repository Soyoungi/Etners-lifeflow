from datetime import date, timedelta

from app.models import FamilyMember
from app.services import personalization, service_rule_engine
from tests.conftest import make_service, make_user


def test_tenure_rule_blocks_short_tenure(db, base_data):
    user = make_user(db, base_data, hire_date=date.today() - timedelta(days=200))
    service = make_service(
        db, base_data, name="장기근속 포상",
        rules=[("tenure_years", ">=", "5", "AND")],
    )
    db.session.commit()

    context = personalization.build_context(user)
    assert service_rule_engine.evaluate(service, context) is False
    assert service_rule_engine.resolve_status(service, context) == "NOT_AVAILABLE"


def test_tenure_rule_allows_long_tenure(db, base_data):
    user = make_user(db, base_data, hire_date=date.today() - timedelta(days=365 * 6))
    service = make_service(
        db, base_data, name="장기근속 포상",
        rules=[("tenure_years", ">=", "5", "AND")],
    )
    db.session.commit()

    context = personalization.build_context(user)
    assert service_rule_engine.evaluate(service, context) is True
    assert service_rule_engine.resolve_status(service, context) == "APPLY_AVAILABLE"


def test_children_age_rule(db, base_data):
    user = make_user(db, base_data, employee_number="100010")
    db.session.add(FamilyMember(
        user_id=user.id, relationship_type="자녀", name="아이",
        birth_date=date.today().replace(year=date.today().year - 10),
    ))
    db.session.commit()

    service = make_service(
        db, base_data, name="자녀 교육지원",
        rules=[
            ("has_children", "exists", "true", "AND"),
            ("max_child_age", "<=", "18", "AND"),
        ],
    )
    db.session.commit()

    context = personalization.build_context(user)
    assert service_rule_engine.evaluate(service, context) is True


def test_children_age_rule_blocks_users_without_children(db, base_data):
    user = make_user(db, base_data, employee_number="100011")
    db.session.commit()

    service = make_service(
        db, base_data, name="자녀 교육지원",
        rules=[
            ("has_children", "exists", "true", "AND"),
            ("max_child_age", "<=", "18", "AND"),
        ],
    )
    db.session.commit()

    context = personalization.build_context(user)
    assert service_rule_engine.evaluate(service, context) is False


def test_team_leader_rule(db, base_data):
    leader = make_user(db, base_data, employee_number="100020", title="팀장", email="leader@etners.com")
    member = make_user(db, base_data, employee_number="100021", title="팀원", email="member@etners.com")
    service = make_service(
        db, base_data, name="리더십 교육",
        rules=[("is_team_leader", "exists", "true", "AND")],
    )
    db.session.commit()

    leader_ctx = personalization.build_context(leader)
    member_ctx = personalization.build_context(member)
    assert service_rule_engine.evaluate(service, leader_ctx) is True
    assert service_rule_engine.evaluate(service, member_ctx) is False


def test_service_without_rules_is_open_to_everyone(db, base_data):
    user = make_user(db, base_data, employee_number="100030")
    service = make_service(db, base_data, name="복지포인트", rules=[])
    db.session.commit()

    context = personalization.build_context(user)
    assert service_rule_engine.evaluate(service, context) is True


def test_expired_application_window(db, base_data):
    user = make_user(db, base_data, employee_number="100040", hire_date=date.today() - timedelta(days=365 * 6))
    service = make_service(
        db, base_data, name="장기근속 포상",
        rules=[("tenure_years", ">=", "5", "AND")],
        application_start_date=date.today() - timedelta(days=60),
        application_end_date=date.today() - timedelta(days=1),
    )
    db.session.commit()

    context = personalization.build_context(user)
    assert service_rule_engine.resolve_status(service, context) == "EXPIRED"
