from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from app.models import User

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    error = None
    if request.method == "POST":
        employee_number = request.form.get("employee_number", "").strip()
        password = request.form.get("password", "")

        user = User.query.filter_by(employee_number=employee_number).first()
        if user is None or not user.is_active or not user.check_password(password):
            error = "사번 또는 비밀번호가 올바르지 않습니다."
        else:
            login_user(user)
            return redirect(request.args.get("next") or url_for("dashboard.index"))

    return render_template("auth/login.html", error=error)


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("로그아웃되었습니다.")
    return redirect(url_for("auth.login"))
