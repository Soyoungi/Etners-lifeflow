from flask import Flask

from config import Config
from app.extensions import db, login_manager


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    login_manager.init_app(app)

    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    from app.routes.auth import auth_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.services import services_bp
    from app.routes.applications import applications_bp
    from app.routes.profile import profile_bp
    from app.routes.admin import admin_bp
    from app.routes.api import api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(services_bp)
    app.register_blueprint(applications_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)

    from app.services.service_rule_engine import STATUS_META

    @app.context_processor
    def inject_globals():
        from app.services.notification_service import unread_count
        from flask_login import current_user

        unread = unread_count(current_user.id) if current_user.is_authenticated else 0
        return {"STATUS_META": STATUS_META, "unread_notification_count": unread}

    return app
