import json
from datetime import datetime

from app.extensions import db


class Service(db.Model):
    __tablename__ = "services"

    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey("service_categories.id"), nullable=False)

    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.String(255))
    thumbnail = db.Column(db.String(10))  # 이모지 아이콘 (프로토타입의 event-icon 대체)
    content = db.Column(db.Text)  # 상세 설명(HTML/텍스트)

    target_audience = db.Column(db.String(255))
    support_content = db.Column(db.String(255))
    support_limit = db.Column(db.String(120))
    contact_department = db.Column(db.String(80))
    contact_phone = db.Column(db.String(40))
    contact_email = db.Column(db.String(120))

    start_date = db.Column(db.Date, nullable=True)  # 이용 기간 시작
    end_date = db.Column(db.Date, nullable=True)  # 이용 기간 종료
    application_start_date = db.Column(db.Date, nullable=True)
    application_end_date = db.Column(db.Date, nullable=True)

    status = db.Column(db.String(20), nullable=False, default="active")  # active | inactive
    priority = db.Column(db.Integer, nullable=False, default=0)  # 높을수록 추천 우선순위 높음
    required_documents = db.Column(db.Text)  # JSON 문자열 리스트, 예: ["재직증명서", "가족관계증명서"]

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    rules = db.relationship(
        "ServiceRule", backref="service", lazy=True, order_by="ServiceRule.sort_order"
    )
    applications = db.relationship("ServiceApplication", backref="service", lazy=True)

    @property
    def is_active(self):
        return self.status == "active"

    @property
    def required_documents_list(self):
        if not self.required_documents:
            return []
        try:
            return json.loads(self.required_documents)
        except (TypeError, ValueError):
            return []

    def application_window_open(self, today=None):
        from datetime import date as _date

        today = today or _date.today()
        if self.application_start_date and today < self.application_start_date:
            return False
        if self.application_end_date and today > self.application_end_date:
            return False
        return True

    def application_expired(self, today=None):
        from datetime import date as _date

        today = today or _date.today()
        return bool(self.application_end_date and today > self.application_end_date)
