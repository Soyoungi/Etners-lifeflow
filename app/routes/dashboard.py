from flask import Blueprint, render_template, request
from flask_login import current_user, login_required

from app.models import Notification, ServiceCategory
from app.services import personalization

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
@login_required
def index():
    data = personalization.get_dashboard_data(current_user)
    categories = ServiceCategory.query.filter_by(is_active=True).order_by(
        ServiceCategory.sort_order
    ).all()
    return render_template(
        "dashboard/index.html",
        recommended=data["recommended"],
        by_category=data["by_category"],
        my_applications=data["my_applications"][:5],
        categories=categories,
    )


@dashboard_bp.route("/notifications")
@login_required
def notifications():
    items = (
        Notification.query.filter_by(user_id=current_user.id)
        .order_by(Notification.created_at.desc())
        .all()
    )
    unread_ids = [n.id for n in items if not n.is_read]
    if unread_ids:
        from app.extensions import db

        Notification.query.filter(Notification.id.in_(unread_ids)).update(
            {"is_read": True}, synchronize_session=False
        )
        db.session.commit()
    return render_template("dashboard/notifications.html", notifications=items)
