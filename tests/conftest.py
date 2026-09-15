import tempfile
from datetime import date, timedelta

import pytest

from app import create_app
from app.extensions import db as _db
from app.models import Company, Department, Service, ServiceCategory, ServiceRule, User


class TestConfig:
    SECRET_KEY = "test-secret"
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = False
    TESTING = True
    UPLOAD_DIR = tempfile.mkdtemp(prefix="lifeflow-test-uploads-")
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024


@pytest.fixture
def app():
    application = create_app(TestConfig)
    with application.app_context():
        _db.create_all()
        yield application
        _db.session.remove()
        _db.drop_all()


@pytest.fixture
def db(app):
    return _db


@pytest.fixture
def base_data(db):
    company = Company(name="이트너스", code="ETNERS")
    db.session.add(company)
    db.session.flush()

    department = Department(company_id=company.id, name="경영지원팀", code="경영지원팀")
    db.session.add(department)
    db.session.flush()

    category = ServiceCategory(name="HR", slug="hr", icon="🧾", sort_order=0)
    db.session.add(category)
    db.session.flush()

    db.session.commit()
    return {"company": company, "department": department, "category": category}


def make_user(db, base_data, **overrides):
    defaults = dict(
        employee_number="100000",
        name="테스트유저",
        email="test@etners.com",
        company_id=base_data["company"].id,
        department_id=base_data["department"].id,
        position="사원",
        title="팀원",
        hire_date=date.today() - timedelta(days=365 * 3),
    )
    defaults.update(overrides)
    user = User(**defaults)
    user.set_password("pw")
    db.session.add(user)
    db.session.flush()
    return user


def make_service(db, base_data, rules=None, **overrides):
    defaults = dict(
        category_id=base_data["category"].id,
        name="테스트서비스",
        description="테스트",
        status="active",
        priority=0,
        application_start_date=date.today() - timedelta(days=1),
        application_end_date=date.today() + timedelta(days=30),
    )
    defaults.update(overrides)
    service = Service(**defaults)
    db.session.add(service)
    db.session.flush()
    for order, (field, operator, value, logical_operator) in enumerate(rules or []):
        db.session.add(ServiceRule(
            service_id=service.id, field=field, operator=operator,
            value=value, logical_operator=logical_operator, sort_order=order,
        ))
    db.session.flush()
    return service
