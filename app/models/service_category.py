from app.extensions import db


class ServiceCategory(db.Model):
    __tablename__ = "service_categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(60), nullable=False)
    description = db.Column(db.String(255))
    icon = db.Column(db.String(10))
    slug = db.Column(db.String(30), unique=True, nullable=False)
    sort_order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    services = db.relationship("Service", backref="category", lazy=True)
