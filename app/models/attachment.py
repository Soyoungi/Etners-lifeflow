from datetime import datetime

from app.extensions import db


class ApplicationAttachment(db.Model):
    __tablename__ = "application_attachments"

    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(
        db.Integer, db.ForeignKey("service_applications.id"), nullable=False
    )
    document_label = db.Column(db.String(120))  # 어떤 필요서류에 대한 첨부인지
    original_filename = db.Column(db.String(255), nullable=False)
    stored_path = db.Column(db.String(500), nullable=False)
    content_type = db.Column(db.String(120))
    size = db.Column(db.Integer, default=0)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
