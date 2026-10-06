from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app
from bson import ObjectId

from routes.decorators import login_required, role_required
from services.registration_service import (
    register_for_event, cancel_registration, generate_qr_code_base64
)
from services.feedback_service import (
    submit_feedback, update_feedback, delete_feedback
)
from services.notification_service import (
    get_user_notifications, mark_notification_read, mark_all_notifications_read,
    archive_notification, delete_notification
)
from services.report_service import get_student_dashboard_metrics

student_bp = Blueprint("student", __name__, url_prefix="/student")


@student_bp.route("/dashboard")
@login_required
@role_required("student")
def dashboard():
    db = current_app.config["DB"]
    student_id = session.get("user_id")

    metrics = get_student_dashboard_metrics(db, student_id)
    notifications, unread_count = get_user_notifications(db, student_id)

    return render_template(
        "student/dashboard.html",
        metrics=metrics,
        notifications=notifications,
        unread_count=unread_count
    )


@student_bp.route("/register/<event_id>", methods=["POST"])
@login_required
@role_required("student")
def register(event_id):
    db = current_app.config["DB"]
    student_id = session.get("user_id")
    ip_addr = request.remote_addr or "127.0.0.1"

    success, message, reg_info = register_for_event(db, event_id, student_id, ip_address=ip_addr)

    if success:
        flash(message, "success")
        if reg_info and reg_info.get("status") == "registered":
            return redirect(url_for("student.view_ticket", registration_id=reg_info["registration_id"]))
    else:
        flash(message, "danger")

    return redirect(url_for("main.event_detail", event_id=event_id))


@student_bp.route("/cancel-registration/<registration_id>", methods=["POST"])
@login_required
@role_required("student")
def cancel_reg(registration_id):
    db = current_app.config["DB"]
    student_id = session.get("user_id")

    success, message = cancel_registration(db, registration_id, student_id, actor_role="student")
    if success:
        flash(message, "info")
    else:
        flash(message, "danger")

    return redirect(url_for("student.dashboard"))


@student_bp.route("/ticket/<registration_id>")
@login_required
def view_ticket(registration_id):
    """View unique digital QR ticket."""
    db = current_app.config["DB"]
    user_id = session.get("user_id")
    role = session.get("role")

    try:
        reg = db.registrations.find_one({"_id": ObjectId(registration_id)})
    except Exception:
        flash("Invalid registration identifier.", "danger")
        return redirect(url_for("student.dashboard"))

    if not reg:
        flash("Ticket not found.", "warning")
        return redirect(url_for("student.dashboard"))

    # IDOR protection: only ticket owner, organizer of the event, or admin can view
    event = db.events.find_one({"_id": reg["event_id"]})
    if role == "student" and str(reg["student_id"]) != str(user_id):
        flash("Access denied. You cannot view another attendee's ticket.", "danger")
        return redirect(url_for("student.dashboard"))

    venue = db.venues.find_one({"_id": event.get("venue_id")})
    student = db.users.find_one({"_id": reg["student_id"]})

    # Generate QR Code image base64 data URI
    qr_data = reg.get("ticket_code", "")
    qr_code_b64 = generate_qr_code_base64(qr_data)

    return render_template(
        "student/ticket.html",
        registration=reg,
        event=event,
        venue=venue,
        student=student,
        qr_code_b64=qr_code_b64
    )


@student_bp.route("/feedback/<event_id>", methods=["GET", "POST"])
@login_required
@role_required("student")
def feedback(event_id):
    """Submit or update feedback for an attended event."""
    db = current_app.config["DB"]
    student_id = session.get("user_id")
    ev_oid = ObjectId(event_id)

    event = db.events.find_one({"_id": ev_oid})
    if not event:
        flash("Event not found.", "danger")
        return redirect(url_for("student.dashboard"))

    # Check if student already submitted feedback
    existing_feedback = db.feedback.find_one({"event_id": ev_oid, "student_id": ObjectId(student_id)})

    if request.method == "POST":
        rating = request.form.get("rating")
        comment = request.form.get("comment", "").strip()

        if existing_feedback:
            success, message = update_feedback(db, existing_feedback["_id"], student_id, rating, comment)
        else:
            success, message, _ = submit_feedback(db, event_id, student_id, rating, comment)

        if success:
            flash(message, "success")
            return redirect(url_for("main.event_detail", event_id=event_id))
        else:
            flash(message, "danger")

    return render_template(
        "student/feedback_form.html",
        event=event,
        feedback=existing_feedback
    )


@student_bp.route("/feedback/delete/<feedback_id>", methods=["POST"])
@login_required
@role_required("student")
def remove_feedback(feedback_id):
    db = current_app.config["DB"]
    student_id = session.get("user_id")

    success, message = delete_feedback(db, feedback_id, student_id, actor_role="student")
    if success:
        flash(message, "info")
    else:
        flash(message, "danger")

    return redirect(url_for("student.dashboard"))


@student_bp.route("/notifications")
@login_required
def notifications_view():
    db = current_app.config["DB"]
    user_id = session.get("user_id")

    notifications, unread_count = get_user_notifications(db, user_id, include_archived=True)
    return render_template("student/notifications.html", notifications=notifications, unread_count=unread_count)


@student_bp.route("/notifications/read/<notif_id>", methods=["POST"])
@login_required
def mark_read(notif_id):
    db = current_app.config["DB"]
    user_id = session.get("user_id")
    mark_notification_read(db, notif_id, user_id)
    return redirect(url_for("student.notifications_view"))


@student_bp.route("/notifications/read-all", methods=["POST"])
@login_required
def mark_all_read():
    db = current_app.config["DB"]
    user_id = session.get("user_id")
    mark_all_notifications_read(db, user_id)
    flash("All notifications marked as read.", "success")
    return redirect(url_for("student.notifications_view"))


@student_bp.route("/notifications/archive/<notif_id>", methods=["POST"])
@login_required
def archive_notif(notif_id):
    db = current_app.config["DB"]
    user_id = session.get("user_id")
    archive_notification(db, notif_id, user_id)
    return redirect(url_for("student.notifications_view"))


@student_bp.route("/notifications/delete/<notif_id>", methods=["POST"])
@login_required
def delete_notif(notif_id):
    db = current_app.config["DB"]
    user_id = session.get("user_id")
    delete_notification(db, notif_id, user_id)
    flash("Notification deleted.", "info")
    return redirect(url_for("student.notifications_view"))
