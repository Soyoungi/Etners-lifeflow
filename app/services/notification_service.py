from app.extensions import db
from app.models import Notification


def notify(user_id, title, message, type_="ANNOUNCEMENT"):
    notification = Notification(user_id=user_id, title=title, message=message, type=type_)
    db.session.add(notification)
    return notification


def unread_count(user_id):
    return Notification.query.filter_by(user_id=user_id, is_read=False).count()
