from datetime import datetime

from app.extensions import db

NOTIFICATION_TYPES = {
    "NEW_SERVICE": "신규 서비스",
    "STATUS_CHANGED": "신청 상태 변경",
    "APPROVED": "승인",
    "REJECTED": "반려",
    "APPLICATION_OPEN": "신청 기간 시작",
    "DEADLINE_SOON": "신청 마감 임박",
    "EXPIRING_SOON": "이용 기간 만료 예정",
    "ANNOUNCEMENT": "관리자 공지",
}


class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    title = db.Column(db.String(120), nullable=False)
    message = db.Column(db.String(500), nullable=False)
    type = db.Column(db.String(30), nullable=False, default="ANNOUNCEMENT")
    is_read = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def type_label(self):
        return NOTIFICATION_TYPES.get(self.type, self.type)
