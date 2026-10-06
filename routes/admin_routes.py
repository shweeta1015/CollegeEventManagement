from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app
from bson import ObjectId
from datetime import datetime

from routes.decorators import login_required, role_required
from services.report_service import get_admin_dashboard_metrics
from services.event_service import (
    get_all_venues, create_venue, update_venue, toggle_venue_status,
    approve_event, archive_or_delete_event
)
from services.auth_service import deactivate_user_account
from database import create_audit_log

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/dashboard")
@login_required
@role_required("admin")
def dashboard():
    db = current_app.config["DB"]
    metrics = get_admin_dashboard_metrics(db)

    # Pending items requiring admin attention
    pending_orgs = list(db.organizer_verifications.find({"status": "pending"}))
    pending_events = list(db.events.find({"status": "pending_approval"}))

    return render_template(
        "admin/dashboard.html",
        metrics=metrics,
        pending_orgs_count=len(pending_orgs),
        pending_events_count=len(pending_events)
    )


@admin_bp.route("/events")
@login_required
@role_required("admin")
def events_list():
    db = current_app.config["DB"]
    status_filter = request.args.get("status", "")

    match_stage = {}
    if status_filter:
        match_stage["status"] = status_filter

    pipeline = [
        {"$match": match_stage},
        {"$lookup": {
            "from": "users",
            "localField": "organizer_id",
            "foreignField": "_id",
            "as": "organizer"
        }},
        {"$unwind": {"path": "$organizer", "preserveNullAndEmptyArrays": True}},
        {"$lookup": {
            "from": "venues",
            "localField": "venue_id",
            "foreignField": "_id",
            "as": "venue"
        }},
        {"$unwind": {"path": "$venue", "preserveNullAndEmptyArrays": True}},
        {"$sort": {"created_at": -1}}
    ]
    events = list(db.events.aggregate(pipeline))

    return render_template("admin/events.html", events=events, current_filter=status_filter)


@admin_bp.route("/events/<event_id>/approve", methods=["POST"])
@login_required
@role_required("admin")
def approve_event_action(event_id):
    db = current_app.config["DB"]
    admin_id = session.get("user_id")

    success, message = approve_event(db, event_id, admin_id, approved=True, notes="Approved by administrator.")
    if success:
        flash(message, "success")
    else:
        flash(message, "danger")

    return redirect(url_for("admin.events_list"))


@admin_bp.route("/events/<event_id>/reject", methods=["POST"])
@login_required
@role_required("admin")
def reject_event_action(event_id):
    db = current_app.config["DB"]
    admin_id = session.get("user_id")
    notes = request.form.get("notes", "Rejected by administrator.")

    success, message = approve_event(db, event_id, admin_id, approved=False, notes=notes)
    if success:
        flash(message, "info")
    else:
        flash(message, "danger")

    return redirect(url_for("admin.events_list"))


@admin_bp.route("/events/<event_id>/archive", methods=["POST"])
@login_required
@role_required("admin")
def archive_event_action(event_id):
    db = current_app.config["DB"]
    admin_id = session.get("user_id")

    success, message = archive_or_delete_event(db, event_id, admin_id, actor_role="admin")
    if success:
        flash(message, "info")
    else:
        flash(message, "danger")

    return redirect(url_for("admin.events_list"))


@admin_bp.route("/users")
@login_required
@role_required("admin")
def users_list():
    db = current_app.config["DB"]
    role_filter = request.args.get("role", "")
    query = {}
    if role_filter:
        query["role"] = role_filter

    users = list(db.users.find(query).sort("created_at", -1))
    return render_template("admin/users.html", users=users, current_role=role_filter)


@admin_bp.route("/users/<user_id>/toggle-status", methods=["POST"])
@login_required
@role_required("admin")
def toggle_user_status(user_id):
    db = current_app.config["DB"]
    admin_id = session.get("user_id")

    user = db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        flash("User not found.", "danger")
        return redirect(url_for("admin.users_list"))

    new_status = not user.get("is_active", True)
    db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"is_active": new_status, "updated_at": datetime.utcnow()}}
    )
    status_str = "activated" if new_status else "deactivated"
    create_audit_log(
        db, admin_id, "admin", "TOGGLE_USER_STATUS", "users", user_id,
        {"email": user.get("email"), "new_status": new_status}
    )
    flash(f"User '{user.get('email')}' has been {status_str}.", "info")
    return redirect(url_for("admin.users_list"))


@admin_bp.route("/organizers")
@login_required
@role_required("admin")
def organizers_queue():
    db = current_app.config["DB"]
    pipeline = [
        {"$lookup": {
            "from": "users",
            "localField": "user_id",
            "foreignField": "_id",
            "as": "user"
        }},
        {"$unwind": "$user"},
        {"$sort": {"created_at": -1}}
    ]
    applications = list(db.organizer_verifications.aggregate(pipeline))
    return render_template("admin/organizers.html", applications=applications)


@admin_bp.route("/organizers/<verif_id>/review", methods=["POST"])
@login_required
@role_required("admin")
def review_organizer(verif_id):
    db = current_app.config["DB"]
    admin_id = session.get("user_id")

    status = request.form.get("status")  # 'verified' or 'rejected'
    notes = request.form.get("admin_notes", "").strip()

    if status not in ["verified", "rejected"]:
        flash("Invalid verification status.", "danger")
        return redirect(url_for("admin.organizers_queue"))

    verif = db.organizer_verifications.find_one({"_id": ObjectId(verif_id)})
    if not verif:
        flash("Verification record not found.", "danger")
        return redirect(url_for("admin.organizers_queue"))

    db.organizer_verifications.update_one(
        {"_id": ObjectId(verif_id)},
        {"$set": {
            "status": status,
            "admin_notes": notes,
            "reviewed_by": ObjectId(admin_id),
            "reviewed_at": datetime.utcnow()
        }}
    )

    # Notify organizer
    db.notifications.insert_one({
        "user_id": verif["user_id"],
        "title": f"Organizer Status: {status.capitalize()}",
        "message": f"Your organizer verification application has been marked as '{status}'. Note: {notes}",
        "type": "update",
        "is_read": False,
        "is_archived": False,
        "created_at": datetime.utcnow()
    })

    create_audit_log(
        db, admin_id, "admin", "REVIEW_ORGANIZER", "organizer_verifications",
        verif_id, {"status": status, "user_id": str(verif["user_id"])}
    )

    flash(f"Organizer status updated to '{status}'.", "success")
    return redirect(url_for("admin.organizers_queue"))


@admin_bp.route("/venues", methods=["GET", "POST"])
@login_required
@role_required("admin")
def venues():
    db = current_app.config["DB"]
    admin_id = session.get("user_id")

    if request.method == "POST":
        name = request.form.get("name")
        code = request.form.get("code")
        capacity = request.form.get("capacity")
        facilities = request.form.get("facilities", "").split(",")

        success, message, _ = create_venue(db, name, code, capacity, facilities, admin_id, "admin")
        if success:
            flash(message, "success")
            return redirect(url_for("admin.venues"))
        else:
            flash(message, "danger")

    venue_list = get_all_venues(db, active_only=False)
    return render_template("admin/venues.html", venues=venue_list)


@admin_bp.route("/venues/<venue_id>/edit", methods=["POST"])
@login_required
@role_required("admin")
def edit_venue(venue_id):
    db = current_app.config["DB"]
    admin_id = session.get("user_id")

    name = request.form.get("name")
    code = request.form.get("code")
    capacity = request.form.get("capacity")
    facilities = request.form.get("facilities", "").split(",")

    success, message = update_venue(db, venue_id, name, code, capacity, facilities, admin_id, "admin")
    if success:
        flash(message, "success")
    else:
        flash(message, "danger")

    return redirect(url_for("admin.venues"))


@admin_bp.route("/venues/<venue_id>/toggle", methods=["POST"])
@login_required
@role_required("admin")
def toggle_venue(venue_id):
    db = current_app.config["DB"]
    admin_id = session.get("user_id")

    venue = db.venues.find_one({"_id": ObjectId(venue_id)})
    if venue:
        new_status = not venue.get("is_active", True)
        toggle_venue_status(db, venue_id, new_status, admin_id, "admin")
        flash(f"Venue '{venue.get('name')}' active status updated.", "info")

    return redirect(url_for("admin.venues"))


@admin_bp.route("/reports")
@login_required
@role_required("admin")
def reports():
    db = current_app.config["DB"]
    metrics = get_admin_dashboard_metrics(db)
    return render_template("admin/reports.html", metrics=metrics)


@admin_bp.route("/audit-logs")
@login_required
@role_required("admin")
def audit_logs():
    db = current_app.config["DB"]
    page = int(request.args.get("page", 1))
    per_page = 25

    total_logs = db.audit_logs.count_documents({})
    logs = list(db.audit_logs.find().sort("timestamp", -1).skip((page - 1) * per_page).limit(per_page))

    return render_template("admin/audit_logs.html", logs=logs, page=page, total_logs=total_logs)


@admin_bp.route("/suggestions", methods=["GET", "POST"])
@login_required
@role_required("admin")
def manage_suggestions():
    db = current_app.config["DB"]

    if request.method == "POST":
        sugg_id = request.form.get("suggestion_id")
        reply = request.form.get("admin_reply", "").strip()
        status = request.form.get("status", "resolved")

        db.platform_suggestions.update_one(
            {"_id": ObjectId(sugg_id)},
            {"$set": {"admin_reply": reply, "status": status, "updated_at": datetime.utcnow()}}
        )
        flash("Suggestion reply updated.", "success")
        return redirect(url_for("admin.manage_suggestions"))

    pipeline = [
        {"$lookup": {
            "from": "users",
            "localField": "user_id",
            "foreignField": "_id",
            "as": "user"
        }},
        {"$unwind": "$user"},
        {"$sort": {"created_at": -1}}
    ]
    suggestions = list(db.platform_suggestions.aggregate(pipeline))
    return render_template("admin/suggestions.html", suggestions=suggestions)
