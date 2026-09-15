from datetime import datetime

from app.extensions import db


class Inquiry(db.Model):
    __tablename__ = "inquiries"

    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(
        db.Integer, db.ForeignKey("service_applications.id"), nullable=False
    )
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    question = db.Column(db.Text, nullable=False)
    answer = db.Column(db.Text, nullable=True)
    answered_at = db.Column(db.DateTime, nullable=True)
    answered_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    asker = db.relationship("User", foreign_keys=[user_id])
    responder = db.relationship("User", foreign_keys=[answered_by])

    @property
    def is_answered(self):
        return self.answer is not None
