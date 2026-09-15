from datetime import date, datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    employee_number = db.Column(db.String(30), unique=True, nullable=False)
    name = db.Column(db.String(60), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey("departments.id"), nullable=False)

    position = db.Column(db.String(40))  # 직급: 사원/대리/과장/차장/부장 등
    title = db.Column(db.String(40))  # 직책: 팀원/팀장/실장 등
    role = db.Column(db.String(20), nullable=False, default="employee")  # employee | admin
    gender = db.Column(db.String(10))

    hire_date = db.Column(db.Date, nullable=False)
    employment_type = db.Column(db.String(30), default="정규직")
    work_location = db.Column(db.String(60))

    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    family_members = db.relationship("FamilyMember", backref="user", lazy=True)
    applications = db.relationship(
        "ServiceApplication",
        foreign_keys="ServiceApplication.user_id",
        backref="applicant",
        lazy=True,
    )
    notifications = db.relationship("Notification", backref="user", lazy=True)

    def set_password(self, raw_password):
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        return check_password_hash(self.password_hash, raw_password)

    @property
    def is_admin(self):
        return self.role == "admin"

    @property
    def tenure_years(self):
        today = date.today()
        delta_days = (today - self.hire_date).days
        return round(delta_days / 365.25, 2)

    @property
    def tenure_label(self):
        today = date.today()
        years = today.year - self.hire_date.year
        months = today.month - self.hire_date.month
        if today.day < self.hire_date.day:
            months -= 1
        if months < 0:
            years -= 1
            months += 12
        return f"{years}년 {months}개월"

    def masked_employee_number(self):
        digits = self.employee_number
        if len(digits) <= 3:
            return digits
        return digits[:3] + "*" * (len(digits) - 3)
