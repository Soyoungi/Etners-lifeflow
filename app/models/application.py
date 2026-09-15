from datetime import datetime

from app.extensions import db

# 신청서 자체의 처리 상태(작업지시서 12번 섹션: 신청 -> 접수 -> 검토 -> 승인/반려 -> 완료)
APPLICATION_STATUSES = [
    "SUBMITTED",
    "RECEIVED",
    "REVIEWING",
    "SUPPLEMENT_REQUIRED",
    "APPROVED",
    "REJECTED",
    "COMPLETED",
    "CANCELLED",
]

APPLICATION_STATUS_LABELS = {
    "SUBMITTED": "신청 접수",
    "RECEIVED": "접수 완료",
    "REVIEWING": "검토 중",
    "SUPPLEMENT_REQUIRED": "서류 보완 요청",
    "APPROVED": "승인",
    "REJECTED": "반려",
    "COMPLETED": "완료",
    "CANCELLED": "신청 취소",
}

# 신청 상태별 배지 색상 클래스 (app/static/css/style.css의 .app-status-* 와 매칭)
APPLICATION_STATUS_COLORS = {
    "SUBMITTED": "app-status-gray",
    "RECEIVED": "app-status-gray",
    "REVIEWING": "app-status-blue",
    "SUPPLEMENT_REQUIRED": "app-status-orange",
    "APPROVED": "app-status-green",
    "REJECTED": "app-status-red",
    "COMPLETED": "app-status-navy",
    "CANCELLED": "app-status-muted",
}


class ServiceApplication(db.Model):
    __tablename__ = "service_applications"

    id = db.Column(db.Integer, primary_key=True)
    service_id = db.Column(db.Integer, db.ForeignKey("services.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    status = db.Column(db.String(30), nullable=False, default="SUBMITTED")
    application_data = db.Column(db.Text)  # 신청서 입력값(JSON 문자열)

    is_urgent = db.Column(db.Boolean, nullable=False, default=False)
    urgent_date = db.Column(db.Date, nullable=True)
    cancel_reason = db.Column(db.String(255), nullable=True)

    applied_at = db.Column(db.DateTime, default=datetime.utcnow)
    processed_at = db.Column(db.DateTime, nullable=True)
    processed_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    processor = db.relationship("User", foreign_keys=[processed_by])
    attachments = db.relationship(
        "ApplicationAttachment", backref="application", lazy=True,
        order_by="ApplicationAttachment.uploaded_at",
    )
    status_history = db.relationship(
        "ApplicationStatusHistory", backref="application", lazy=True,
        order_by="ApplicationStatusHistory.created_at",
    )
    inquiries = db.relationship(
        "Inquiry", backref="application", lazy=True,
        order_by="Inquiry.created_at",
    )

    @property
    def status_label(self):
        return APPLICATION_STATUS_LABELS.get(self.status, self.status)

    @property
    def status_color(self):
        return APPLICATION_STATUS_COLORS.get(self.status, "app-status-gray")
