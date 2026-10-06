import os
import logging
from datetime import datetime
from bson import ObjectId
from flask import Flask, render_template, session, jsonify

from config import config_by_name
from database import get_db, init_indexes
from routes.auth_routes import auth_bp
from routes.main_routes import main_bp
from routes.student_routes import student_bp
from routes.organizer_routes import organizer_bp
from routes.admin_routes import admin_bp
from routes.api_routes import api_bp

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


def create_app(config_name=None):
    """Application factory for College Event Management System."""
    if config_name is None:
        config_name = os.getenv("FLASK_ENV", "development")

    app = Flask(__name__)
    config_obj = config_by_name.get(config_name, config_by_name["default"])
    app.config.from_object(config_obj)

    # Initialize Database Connection
    db = get_db(app.config["MONGODB_URI"], app.config["DATABASE_NAME"])
    app.config["DB"] = db
    
    # Ensure MongoDB Indexes
    try:
        init_indexes(db)
    except Exception as e:
        logger.warning(f"Index initialization warning: {e}")

    # Ensure upload directory exists
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # Register Blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(organizer_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)

    # Global Context Processor for Navbar Badges & Helper Utilities
    @app.context_processor
    def inject_global_data():
        user_id = session.get("user_id")
        unread_count = 0
        is_verified_organizer = False

        if user_id:
            try:
                unread_count = db.notifications.count_documents({
                    "user_id": ObjectId(user_id),
                    "is_read": False,
                    "is_archived": False
                })
                if session.get("role") == "organizer":
                    verif = db.organizer_verifications.find_one({"user_id": ObjectId(user_id)})
                    is_verified_organizer = (verif.get("status") == "verified") if verif else False
            except Exception:
                pass

        return {
            "current_user_id": user_id,
            "current_user_name": session.get("full_name"),
            "current_user_role": session.get("role"),
            "unread_notifications_count": unread_count,
            "is_verified_organizer": is_verified_organizer,
            "now": datetime.utcnow()
        }

    # Custom Jinja Filters
    @app.template_filter("datetime_format")
    def format_datetime(value, format="%d %b %Y, %I:%M %p"):
        if not value:
            return ""
        if isinstance(value, str):
            try:
                value = datetime.fromisoformat(value)
            except ValueError:
                return value
        return value.strftime(format)

    @app.template_filter("date_format")
    def format_date(value, format="%d %b %Y"):
        if not value:
            return ""
        if isinstance(value, str):
            try:
                value = datetime.fromisoformat(value)
            except ValueError:
                return value
        return value.strftime(format)

    # Error Handlers
    @app.errorhandler(403)
    def forbidden(e):
        return render_template("public/error.html", code=403, message="Access Forbidden: You lack required permissions."), 403

    @app.errorhandler(404)
    def page_not_found(e):
        return render_template("public/error.html", code=404, message="The requested page could not be found."), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        logger.error(f"Internal server error: {e}")
        return render_template("public/error.html", code=500, message="An internal server error occurred. Please try again later."), 500

    return app


app = create_app()

if __name__ == "__main__":
    print("\n* Starting College Event Management System (ADBMS Project)...")
    print("* Listening on http://127.0.0.1:5000\n")
    app.run(host="127.0.0.1", port=5000, debug=True)
