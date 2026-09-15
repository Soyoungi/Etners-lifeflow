from flask import Blueprint, render_template
from flask_login import current_user, login_required

profile_bp = Blueprint("profile", __name__, url_prefix="/profile")


@profile_bp.route("/")
@login_required
def index():
    return render_template("profile/index.html", user=current_user)
