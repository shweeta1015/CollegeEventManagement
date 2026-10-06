from flask import Blueprint, render_template, request, current_app, flash, redirect, url_for, session
from bson import ObjectId
from datetime import datetime

from services.event_service import get_public_events
from services.feedback_service import get_event_feedback
from models.validators import VALID_CATEGORIES
from routes.decorators import login_required

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    db = current_app.config["DB"]
    now = datetime.utcnow()

    # Featured upcoming events
    featured_events, _ = get_public_events(db, page=1, per_page=6)

    # High-level statistics
    total_events = db.events.count_documents({"status": {"$ne": "archived"}})
    total_venues = db.venues.count_documents({"is_active": True})
    total_registrations = db.registrations.count_documents({"status": {"$in": ["registered", "checked-in"]}})

    return render_template(
        "public/index.html",
        featured_events=featured_events,
        total_events=total_events,
        total_venues=total_venues,
        total_registrations=total_registrations,
        categories=VALID_CATEGORIES
    )


@main_bp.route("/events")
def events_catalog():
    db = current_app.config["DB"]
    category = request.args.get("category", "")
    search = request.args.get("search", "").strip()
    start_date = request.args.get("start_date", "")
    page = int(request.args.get("page", 1))

    events, total_count = get_public_events(
        db, category=category, search=search, start_date=start_date, page=page, per_page=9
    )

    return render_template(
        "public/events.html",
        events=events,
        total_count=total_count,
        categories=VALID_CATEGORIES,
        current_category=category,
        search_query=search,
        start_date=start_date,
        page=page
    )


@main_bp.route("/events/<event_id>")
def event_detail(event_id):
    db = current_app.config["DB"]
    try:
        ev_oid = ObjectId(event_id)
    except Exception:
        flash("Invalid event identifier.", "danger")
        return redirect(url_for("main.events_catalog"))

    event = db.events.find_one({"_id": ev_oid})
    if not event:
        flash("Event not found.", "warning")
        return redirect(url_for("main.events_catalog"))

    venue = db.venues.find_one({"_id": event.get("venue_id")})
    organizer = db.users.find_one({"_id": event.get("organizer_id")})
    feedback_list = get_event_feedback(db, event_id)

    # Check student registration status if logged in
    user_registration = None
    if session.get("user_id"):
        user_registration = db.registrations.find_one({
            "event_id": ev_oid,
            "student_id": ObjectId(session["user_id"]),
            "status": {"$in": ["registered", "waitlisted", "checked-in"]}
        })

    # Average rating calculation
    avg_rating = 0.0
    if feedback_list:
        avg_rating = round(sum(f["rating"] for f in feedback_list) / len(feedback_list), 1)

    return render_template(
        "public/event_detail.html",
        event=event,
        venue=venue,
        organizer=organizer,
        feedback_list=feedback_list,
        avg_rating=avg_rating,
        user_registration=user_registration
    )


@main_bp.route("/about")
def about():
    """Information page explaining ADBMS architectural concepts demonstrated in this project."""
    return render_template("public/about.html")


@main_bp.route("/suggestions", methods=["GET", "POST"])
@login_required
def suggestions():
    db = current_app.config["DB"]
    user_id = session.get("user_id")

    if request.method == "POST":
        topic = request.form.get("topic", "").strip()
        message = request.form.get("message", "").strip()

        if not topic or not message:
            flash("Both topic and message are required.", "danger")
        else:
            db.platform_suggestions.insert_one({
                "user_id": ObjectId(user_id),
                "topic": topic,
                "message": message,
                "status": "new",
                "admin_reply": "",
                "created_at": datetime.utcnow()
            })
            flash("Thank you for your feedback! The administration team has received your suggestion.", "success")
            return redirect(url_for("main.suggestions"))

    my_suggestions = list(db.platform_suggestions.find({"user_id": ObjectId(user_id)}).sort("created_at", -1))
    return render_template("public/suggestions.html", suggestions=my_suggestions)
