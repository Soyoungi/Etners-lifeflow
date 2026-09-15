from datetime import datetime

from app.extensions import db


class ServiceRule(db.Model):
    """개인화 조건. field/operator/value를 personalization context와 비교한다.

    logical_operator는 "다음 규칙과 이 규칙을 어떻게 결합할지"를 나타낸다
    (AND | OR). 마지막 규칙의 logical_operator는 평가에 사용되지 않는다.
    """

    __tablename__ = "service_rules"

    id = db.Column(db.Integer, primary_key=True)
    service_id = db.Column(db.Integer, db.ForeignKey("services.id"), nullable=False)

    field = db.Column(db.String(60), nullable=False)
    operator = db.Column(db.String(20), nullable=False)  # =, !=, >=, <=, >, <, in, exists
    value = db.Column(db.String(255), nullable=False)
    logical_operator = db.Column(db.String(5), nullable=False, default="AND")  # AND | OR
    sort_order = db.Column(db.Integer, nullable=False, default=0)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
