from functools import wraps
from flask import session, redirect, url_for, flash, request, abort, jsonify
from bson import ObjectId


def login_required(f):
    """Ensure user is logged in before accessing protected routes."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please sign in to access this page.", "warning")
            return redirect(url_for("auth.login", next=request.url))
        return f(*args, **kwargs)
    return decorated_function


def role_required(*roles):
    """
    Enforce Role-Based Access Control (RBAC).
    Guarantees backend security enforcement regardless of frontend button visibility.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not session.get("user_id"):
                flash("Please sign in to access this page.", "warning")
                return redirect(url_for("auth.login", next=request.url))

            user_role = session.get("role")
            if user_role not in roles:
                flash("Access Denied: You do not have permission to view this resource.", "danger")
                if user_role == "admin":
                    return redirect(url_for("admin.dashboard"))
                elif user_role == "organizer":
                    return redirect(url_for("organizer.dashboard"))
                else:
                    return redirect(url_for("student.dashboard"))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def api_role_required(*roles):
    """RBAC decorator for JSON API endpoints."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not session.get("user_id"):
                return jsonify({"success": False, "message": "Authentication required."}), 401

            user_role = session.get("role")
            if user_role not in roles:
                return jsonify({"success": False, "message": "Forbidden: Insufficient privileges."}), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator
