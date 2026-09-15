"""데모 데이터 정의.

- 로컬 개발: `python seed.py`가 테이블을 초기화하고 이 데이터를 넣는다.
- 운영(Vercel+Supabase): `app.__init__.create_app()`이 시작 시 테이블이 비어 있으면
  자동으로 이 데이터를 채운다(이미 데이터가 있으면 건드리지 않는다).
"""

import json
from datetime import date, timedelta

from app.extensions import db
from app.models import (
    Company,
    Department,
    FamilyMember,
    Service,
    ServiceCategory,
    ServiceRule,
    User,
)


def populate():
    company = Company(name="이트너스", code="ETNERS")
    db.session.add(company)
    db.session.flush()

    dept_names = ["경영지원팀", "개발팀", "영업팀", "인사팀"]
    departments = {}
    for name in dept_names:
        dept = Department(company_id=company.id, name=name, code=name)
        db.session.add(dept)
        db.session.flush()
        departments[name] = dept

    users = {}

    def make_user(emp_no, name, dept, position, title, hire_date, password,
                  role="employee", employment_type="정규직", work_location="서울",
                  gender="M", email=None):
        user = User(
            employee_number=emp_no,
            name=name,
            email=email or f"{emp_no}@etners.com",
            company_id=company.id,
            department_id=departments[dept].id,
            position=position,
            title=title,
            role=role,
            gender=gender,
            hire_date=hire_date,
            employment_type=employment_type,
            work_location=work_location,
        )
        user.set_password(password)
        db.session.add(user)
        db.session.flush()
        users[emp_no] = user
        return user

    hong = make_user(
        "11111", "홍길동", "경영지원팀", "과장", "팀원",
        date(2019, 3, 2), "0000",
    )
    newbie = make_user(
        "22222", "김신입", "개발팀", "사원", "팀원",
        date.today() - timedelta(days=200), "0000",
    )
    leader = make_user(
        "33333", "이단단", "영업팀", "과장", "팀장",
        date(2016, 4, 1), "0000",
    )
    parent = make_user(
        "44444", "박지원", "인사팀", "차장", "실장",
        date(2010, 1, 1), "0000",
    )
    admin = make_user(
        "55555", "관리자", "인사팀", "부장", "실장",
        date(2005, 1, 1), "0000", role="admin",
    )

    db.session.add(FamilyMember(
        user_id=parent.id, relationship_type="배우자", name="박지원 배우자",
        birth_date=date(1980, 5, 1),
    ))
    db.session.add(FamilyMember(
        user_id=parent.id, relationship_type="자녀", name="박지원 자녀",
        birth_date=date.today().replace(year=date.today().year - 10),
    ))

    category_defs = [
        ("HR", "hr", "🧾"),
        ("복지", "welfare", "🎁"),
        ("교육", "education", "📚"),
        ("생활", "life", "🏠"),
        ("가족", "family", "👨‍👩‍👧"),
    ]
    categories = {}
    for idx, (name, slug, icon) in enumerate(category_defs):
        category = ServiceCategory(name=name, slug=slug, icon=icon, sort_order=idx)
        db.session.add(category)
        db.session.flush()
        categories[slug] = category

    today = date.today()

    def make_service(name, slug_category, description, thumbnail, priority=0,
                      target_audience=None, support_content=None, support_limit=None,
                      application_start=None, application_end=None,
                      rules=None, required_documents=None):
        service = Service(
            category_id=categories[slug_category].id,
            name=name,
            description=description,
            thumbnail=thumbnail,
            content=description,
            target_audience=target_audience,
            support_content=support_content,
            support_limit=support_limit,
            contact_department="경영지원팀",
            contact_phone="02-1234-5678",
            contact_email="hr@etners.com",
            application_start_date=application_start,
            application_end_date=application_end,
            priority=priority,
            status="active",
            required_documents=json.dumps(required_documents, ensure_ascii=False) if required_documents else None,
        )
        db.session.add(service)
        db.session.flush()
        for order, (field, operator, value, logical_operator) in enumerate(rules or []):
            db.session.add(ServiceRule(
                service_id=service.id,
                field=field,
                operator=operator,
                value=value,
                logical_operator=logical_operator,
                sort_order=order,
            ))
        return service

    make_service(
        "신입사원 지원", "hr", "입사 1년 미만 신입사원을 위한 온보딩 지원 서비스입니다.", "🌱",
        priority=5,
        target_audience="입사 1년 미만 임직원",
        support_content="온보딩 키트, 멘토링 프로그램, 정착지원금",
        support_limit="1인당 30만원",
        application_start=today - timedelta(days=30),
        application_end=today + timedelta(days=60),
        rules=[("tenure_years", "<", "1", "AND")],
        required_documents=["재직증명서"],
    )

    make_service(
        "장기근속 포상", "hr", "5년 이상 근속 임직원을 위한 포상 서비스입니다.", "🏆",
        priority=8,
        target_audience="근속 5년 이상 재직자",
        support_content="포상금 및 기념패, 특별 휴가 3일",
        support_limit="1회",
        application_start=today - timedelta(days=10),
        application_end=today + timedelta(days=90),
        rules=[("tenure_years", ">=", "5", "AND")],
    )

    make_service(
        "가족 건강검진", "family", "등록된 가족을 위한 건강검진 지원 서비스입니다.", "🩺",
        priority=4,
        target_audience="본인 및 등록 가족",
        support_content="기본 건강검진 + 선택검진",
        support_limit="가족 1인당 20만원",
        application_start=today - timedelta(days=5),
        application_end=today + timedelta(days=120),
        rules=[("has_family", "exists", "true", "AND")],
        required_documents=["가족관계증명서"],
    )

    make_service(
        "자녀 교육지원", "family", "만 18세 이하 자녀를 둔 임직원을 위한 교육비 지원입니다.", "🎒",
        priority=6,
        target_audience="자녀 등록자(만 18세 이하)",
        support_content="학자금 일부 지원",
        support_limit="자녀 1인당 연 100만원",
        application_start=today - timedelta(days=20),
        application_end=today + timedelta(days=100),
        rules=[
            ("has_children", "exists", "true", "AND"),
            ("max_child_age", "<=", "18", "AND"),
        ],
        required_documents=["가족관계증명서", "재학증명서"],
    )

    make_service(
        "관리자 교육", "education", "직책자를 위한 관리자 역량 교육 프로그램입니다.", "🧑‍💼",
        priority=3,
        target_audience="팀장/실장 등 직책자",
        support_content="관리자 필수 교육 과정 수강 지원",
        support_limit="1인당 1과정",
        application_start=today - timedelta(days=15),
        application_end=today + timedelta(days=45),
        rules=[("is_officer", "exists", "true", "AND")],
    )

    make_service(
        "리더십 교육", "education", "팀장급 이상을 위한 리더십 향상 교육입니다.", "🎯",
        priority=7,
        target_audience="팀장",
        support_content="리더십 워크숍 및 코칭",
        support_limit="1인당 1회",
        application_start=today - timedelta(days=15),
        application_end=today + timedelta(days=45),
        rules=[("is_team_leader", "exists", "true", "AND")],
    )

    make_service(
        "복지포인트", "welfare", "전 임직원 대상 연간 복지포인트입니다.", "💳",
        priority=9,
        target_audience="전체 임직원",
        support_content="연 100만 포인트 지급, 온라인몰에서 사용",
        support_limit="연 100만 포인트",
        application_start=today - timedelta(days=60),
        application_end=today + timedelta(days=200),
        rules=[],
    )

    make_service(
        "경조사 지원", "welfare", "결혼, 출산, 상조 등 경조사 발생 시 지원됩니다.", "💐",
        priority=2,
        target_audience="전체 임직원",
        support_content="경조금 및 화환, 경조휴가",
        support_limit="사유별 규정 지급",
        application_start=today - timedelta(days=60),
        application_end=today + timedelta(days=300),
        rules=[],
    )

    make_service(
        "자기계발비", "education", "어학, 자격증 등 자기계발을 위한 비용을 지원합니다.", "📖",
        priority=1,
        target_audience="전체 임직원",
        support_content="교육/도서/자격증 응시료 지원",
        support_limit="연 50만원",
        application_start=today - timedelta(days=60),
        application_end=today + timedelta(days=200),
        rules=[],
        required_documents=["수강증빙", "영수증"],
    )

    make_service(
        "이사비 지원", "life", "이사 발생 시 이사비 일부를 지원합니다.", "📦",
        priority=2,
        target_audience="전체 임직원",
        support_content="이사비 실비 지원",
        support_limit="1회 50만원 한도",
        application_start=today - timedelta(days=30),
        application_end=today + timedelta(days=150),
        rules=[],
        required_documents=["재직증명서"],
    )

    make_service(
        "통근버스 이용권", "life", "출퇴근 통근버스 이용을 지원합니다.", "🚌",
        priority=4,
        target_audience="전체 임직원",
        support_content="통근버스 정기 이용권",
        support_limit="월 1매",
        application_start=today - timedelta(days=60),
        application_end=today + timedelta(days=200),
        rules=[],
    )

    make_service(
        "제휴 피트니스 할인", "life", "제휴 피트니스 센터 할인 혜택입니다.", "🏋️",
        priority=3,
        target_audience="전체 임직원",
        support_content="제휴 헬스장 월 이용료 30% 할인",
        support_limit="1인 1개소",
        application_start=today - timedelta(days=60),
        application_end=today + timedelta(days=200),
        rules=[],
    )

    make_service(
        "주니어 성장지원금", "hr", "사원/대리급 임직원의 자기계발을 위한 성장지원금입니다.", "🚀",
        priority=6,
        target_audience="사원, 대리",
        support_content="어학·자격증·세미나 참가비 지원",
        support_limit="연 40만원",
        application_start=today - timedelta(days=30),
        application_end=today + timedelta(days=120),
        rules=[("position", "in", "사원,대리", "AND")],
    )

    make_service(
        "시니어 리더십 코칭", "education", "차장/부장급을 위한 1:1 리더십 코칭 프로그램입니다.", "🧭",
        priority=5,
        target_audience="차장, 부장",
        support_content="외부 전문 코치 1:1 코칭 6회",
        support_limit="1인 1과정",
        application_start=today - timedelta(days=20),
        application_end=today + timedelta(days=100),
        rules=[("position", "in", "차장,부장", "AND")],
    )
