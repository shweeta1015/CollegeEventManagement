from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app, jsonify
from bson import ObjectId
from datetime import datetime

from routes.decorators import login_required, role_required
from services.event_service import (
    create_event, update_event, archive_or_delete_event, is_organizer_verified, get_all_venues
)
from services.registration_service import check_in_attendee
from services.feedback_service import respond_to_feedback, get_event_feedback
from services.notification_service import trigger_event_reminders
from services.report_service import get_organizer_dashboard_metrics
from models.validators import validate_and_process_image, VALID_CATEGORIES

organizer_bp = Blueprint("organizer", __name__, url_prefix="/organizer")


@organizer_bp.route("/dashboard")
@login_required
@role_required("organizer")
def dashboard():
    db = current_app.config["DB"]
    organizer_id = session.get("user_id")

    metrics = get_organizer_dashboard_metrics(db, organizer_id)
    is_verified, verif_msg = is_organizer_verified(db, organizer_id)

    return render_template(
        "organizer/dashboard.html",
        metrics=metrics,
        is_verified=is_verified,
        verif_msg=verif_msg
    )


@organizer_bp.route("/events/new", methods=["GET", "POST"])
@login_required
@role_required("organizer")
def new_event():
    db = current_app.config["DB"]
    organizer_id = session.get("user_id")

    # Strict check: only verified organizers can create/publish events
    is_verified, verif_msg = is_organizer_verified(db, organizer_id)
    if not is_verified:
        flash(f"Cannot create events: {verif_msg}. Please update your verification details in your profile.", "danger")
        return redirect(url_for("organizer.dashboard"))

    venues = get_all_venues(db, active_only=True)

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        category = request.form.get("category", "").strip()
        venue_id = request.form.get("venue_id", "").strip()
        start_time = request.form.get("start_time", "").strip()
        end_time = request.form.get("end_time", "").strip()
        capacity = request.form.get("capacity", 0)
        description = request.form.get("description", "").strip()
        budget_total = request.form.get("budget_total", 0.0)
        budget_breakdown = request.form.get("budget_breakdown", "").strip()

        banner_filename = ""
        # Handle file upload if present
        if "banner_image" in request.files:
            file = request.files["banner_image"]
            if file and file.filename != "":
                upload_folder = current_app.config["UPLOAD_FOLDER"]
                ok, img_msg, filename = validate_and_process_image(file, upload_folder)
                if not ok:
                    flash(f"Banner image error: {img_msg}", "danger")
                    return render_template("organizer/event_form.html", venues=venues, categories=VALID_CATEGORIES)
                banner_filename = filename

        event_data = {
            "title": title,
            "category": category,
            "venue_id": venue_id,
            "start_time": start_time,
            "end_time": end_time,
            "capacity": capacity,
            "description": description,
            "budget_total": budget_total,
            "budget_threshold": current_app.config["BUDGET_BREAKDOWN_THRESHOLD"],
            "budget_breakdown": budget_breakdown,
            "banner_image": banner_filename,
            "status": "published"  # Verified organizers can publish directly
        }

        success, message, event_id = create_event(db, event_data, organizer_id, actor_role="organizer")
        if success:
            flash("Event created and published successfully!", "success")
            return redirect(url_for("organizer.dashboard"))
        else:
            flash(message, "danger")

    return render_template("organizer/event_form.html", venues=venues, categories=VALID_CATEGORIES, event=None)


@organizer_bp.route("/events/<event_id>/edit", methods=["GET", "POST"])
@login_required
@role_required("organizer")
def edit_event(event_id):
    db = current_app.config["DB"]
    organizer_id = session.get("user_id")

    event = db.events.find_one({"_id": ObjectId(event_id)})
    if not event:
        flash("Event not found.", "danger")
        return redirect(url_for("organizer.dashboard"))

    # IDOR check: Organizer can only edit their own event
    if str(event["organizer_id"]) != str(organizer_id):
        flash("Access denied: You do not own this event.", "danger")
        return redirect(url_for("organizer.dashboard"))

    venues = get_all_venues(db, active_only=True)

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        category = request.form.get("category", "").strip()
        venue_id = request.form.get("venue_id", "").strip()
        start_time = request.form.get("start_time", "").strip()
        end_time = request.form.get("end_time", "").strip()
        capacity = request.form.get("capacity", 0)
        description = request.form.get("description", "").strip()
        budget_total = request.form.get("budget_total", 0.0)

        banner_filename = event.get("banner_image", "")
        if "banner_image" in request.files:
            file = request.files["banner_image"]
            if file and file.filename != "":
                upload_folder = current_app.config["UPLOAD_FOLDER"]
                ok, img_msg, filename = validate_and_process_image(file, upload_folder)
                if not ok:
                    flash(f"Banner image error: {img_msg}", "danger")
                    return render_template("organizer/event_form.html", venues=venues, categories=VALID_CATEGORIES, event=event)
                banner_filename = filename

        event_data = {
            "title": title,
            "category": category,
            "venue_id": venue_id,
            "start_time": start_time,
            "end_time": end_time,
            "capacity": capacity,
            "description": description,
            "budget_total": budget_total,
            "banner_image": banner_filename
        }

        success, message = update_event(db, event_id, event_data, organizer_id, actor_role="organizer")
        if success:
            flash(message, "success")
            return redirect(url_for("organizer.dashboard"))
        else:
            flash(message, "danger")

    return render_template("organizer/event_form.html", venues=venues, categories=VALID_CATEGORIES, event=event)


@organizer_bp.route("/events/<event_id>/archive", methods=["POST"])
@login_required
@role_required("organizer")
def archive_event(event_id):
    db = current_app.config["DB"]
    organizer_id = session.get("user_id")

    success, message = archive_or_delete_event(db, event_id, organizer_id, actor_role="organizer")
    if success:
        flash(message, "info")
    else:
        flash(message, "danger")

    return redirect(url_for("organizer.dashboard"))


@organizer_bp.route("/events/<event_id>/attendees")
@login_required
@role_required("organizer")
def attendees_roster(event_id):
    db = current_app.config["DB"]
    organizer_id = session.get("user_id")

    event = db.events.find_one({"_id": ObjectId(event_id)})
    if not event or str(event["organizer_id"]) != str(organizer_id):
        flash("Access denied or event not found.", "danger")
        return redirect(url_for("organizer.dashboard"))

    pipeline = [
        {"$match": {"event_id": ObjectId(event_id)}},
        {"$lookup": {
            "from": "users",
            "localField": "student_id",
            "foreignField": "_id",
            "as": "student"
        }},
        {"$unwind": "$student"},
        {"$sort": {"registered_at": 1}}
    ]
    attendees = list(db.registrations.aggregate(pipeline))

    return render_template("organizer/attendees.html", event=event, attendees=attendees)


@organizer_bp.route("/events/<event_id>/checkin", methods=["GET", "POST"])
@login_required
@role_required("organizer")
def checkin_page(event_id):
    """
    Check-in console for event organizers:
    Supports live text ticket entry or camera QR scanner via JS.
    """
    db = current_app.config["DB"]
    organizer_id = session.get("user_id")

    event = db.events.find_one({"_id": ObjectId(event_id)})
    if not event or str(event["organizer_id"]) != str(organizer_id):
        flash("Access denied or event not found.", "danger")
        return redirect(url_for("organizer.dashboard"))

    if request.method == "POST":
        ticket_code = request.form.get("ticket_code", "").strip()
        success, message, data = check_in_attendee(db, ticket_code, organizer_id, actor_role="organizer")
        if success:
            flash(message, "success")
        else:
            flash(message, "danger")

    recent_checkins = list(db.registrations.find({
        "event_id": ObjectId(event_id),
        "status": "checked-in"
    }).sort("check_in_time", -1).limit(10))

    return render_template("organizer/checkin.html", event=event, recent_checkins=recent_checkins)


@organizer_bp.route("/events/<event_id>/reminders", methods=["POST"])
@login_required
@role_required("organizer")
def send_reminders(event_id):
    """Demo trigger to dispatch reminder notifications to all confirmed attendees."""
    db = current_app.config["DB"]
    organizer_id = session.get("user_id")

    success, message, count = trigger_event_reminders(db, event_id, organizer_id, actor_role="organizer")
    if success:
        flash(message, "success")
    else:
        flash(message, "danger")

    return redirect(url_for("organizer.dashboard"))


@organizer_bp.route("/feedback/respond/<feedback_id>", methods=["POST"])
@login_required
@role_required("organizer")
def reply_feedback(feedback_id):
    db = current_app.config["DB"]
    organizer_id = session.get("user_id")
    response_text = request.form.get("response_text", "")

    success, message = respond_to_feedback(db, feedback_id, organizer_id, response_text, actor_role="organizer")
    if success:
        flash(message, "success")
    else:
        flash(message, "danger")

    return redirect(request.referrer or url_for("organizer.dashboard"))
