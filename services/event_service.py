import logging
from datetime import datetime
from bson import ObjectId
from pymongo.errors import DuplicateKeyError

from models.validators import validate_event_data, sanitize_markdown
from database import create_audit_log

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# VENUE SERVICES
# ---------------------------------------------------------------------------

def create_venue(db, name, code, capacity, facilities, actor_id, actor_role):
    """Admin creates a new event venue."""
    if not name or len(name.strip()) < 2:
        return False, "Venue name must be at least 2 characters.", None
    if not code or len(code.strip()) < 2:
        return False, "Venue code must be at least 2 characters.", None
    try:
        cap = int(capacity)
        if cap <= 0:
            return False, "Venue capacity must be a positive integer.", None
    except (ValueError, TypeError):
        return False, "Invalid venue capacity.", None

    existing = db.venues.find_one({"$or": [{"name": name.strip()}, {"code": code.strip().upper()}]})
    if existing:
        return False, "A venue with this name or code already exists.", None

    facility_list = [f.strip() for f in facilities if f.strip()] if isinstance(facilities, list) else []

    venue_doc = {
        "name": name.strip(),
        "code": code.strip().upper(),
        "capacity": cap,
        "facilities": facility_list,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }

    try:
        res = db.venues.insert_one(venue_doc)
        create_audit_log(
            db, actor_id, actor_role, "CREATE_VENUE", "venues", res.inserted_id,
            {"name": name.strip(), "capacity": cap}
        )
        return True, "Venue created successfully.", res.inserted_id
    except DuplicateKeyError:
        return False, "A venue with this name or code already exists.", None


def get_all_venues(db, active_only=True):
    """Retrieve venues."""
    query = {"is_active": True} if active_only else {}
    return list(db.venues.find(query).sort("name", 1))


def update_venue(db, venue_id, name, code, capacity, facilities, actor_id, actor_role):
    """Update venue details."""
    try:
        cap = int(capacity)
        if cap <= 0:
            return False, "Capacity must be greater than zero."
    except (ValueError, TypeError):
        return False, "Invalid capacity."

    facility_list = [f.strip() for f in facilities if f.strip()] if isinstance(facilities, list) else []

    db.venues.update_one(
        {"_id": ObjectId(venue_id)},
        {"$set": {
            "name": name.strip(),
            "code": code.strip().upper(),
            "capacity": cap,
            "facilities": facility_list,
            "updated_at": datetime.utcnow()
        }}
    )
    create_audit_log(db, actor_id, actor_role, "UPDATE_VENUE", "venues", venue_id)
    return True, "Venue updated successfully."


def toggle_venue_status(db, venue_id, is_active, actor_id, actor_role):
    """Soft-activate or deactivate venue."""
    db.venues.update_one(
        {"_id": ObjectId(venue_id)},
        {"$set": {"is_active": bool(is_active), "updated_at": datetime.utcnow()}}
    )
    create_audit_log(db, actor_id, actor_role, "TOGGLE_VENUE_STATUS", "venues", venue_id, {"is_active": is_active})
    return True, "Venue status updated."


# ---------------------------------------------------------------------------
# EVENT SERVICES
# ---------------------------------------------------------------------------

def is_organizer_verified(db, user_id):
    """Check if organizer is verified and approved."""
    verif = db.organizer_verifications.find_one({"user_id": ObjectId(user_id)})
    if not verif:
        return False, "Organizer profile verification record not found."
    if verif.get("status") != "verified":
        return False, f"Organizer status is '{verif.get('status')}'. Only verified organizers can publish events."
    return True, "Organizer is verified."


def create_event(db, data, organizer_id, actor_role="organizer"):
    """
    Create a new event with full validations:
    - Verified organizer requirement
    - Title unique per organizer per date
    - Duration >= 1 hour, start in future
    - Venue capacity check
    - Markdown sanitization
    """
    # 1. Organizer verification check
    if actor_role != "admin":
        verified, msg = is_organizer_verified(db, organizer_id)
        if not verified:
            return False, msg, None

    # 2. Validation
    is_valid, errors = validate_event_data(data, is_update=False)
    if not is_valid:
        return False, "; ".join(errors), None

    # 3. Venue check
    venue_id = data.get("venue_id")
    try:
        venue = db.venues.find_one({"_id": ObjectId(venue_id), "is_active": True})
        if not venue:
            return False, "Selected venue does not exist or is inactive.", None
    except Exception:
        return False, "Invalid venue identifier.", None

    capacity = int(data.get("capacity"))
    if capacity > venue.get("capacity", 0):
        return False, f"Event capacity ({capacity}) cannot exceed venue capacity ({venue.get('capacity')}).", None

    start_dt = data["start_time"] if isinstance(data["start_time"], datetime) else datetime.fromisoformat(data["start_time"])
    end_dt = data["end_time"] if isinstance(data["end_time"], datetime) else datetime.fromisoformat(data["end_time"])

    # 4. Check uniqueness: title per organizer per date
    start_date_str = start_dt.strftime("%Y-%m-%d")
    existing_same_day = db.events.find_one({
        "organizer_id": ObjectId(organizer_id),
        "title": {"$regex": f"^{data['title'].strip()}$", "$options": "i"},
        "start_time": {
            "$gte": datetime.strptime(f"{start_date_str} 00:00:00", "%Y-%m-%d %H:%M:%S"),
            "$lte": datetime.strptime(f"{start_date_str} 23:59:59", "%Y-%m-%d %H:%M:%S")
        },
        "status": {"$ne": "archived"}
    })
    if existing_same_day:
        return False, "You already have an event with this title on the same date.", None

    # Initial status: Admin or verified organizers publish directly by default, unless draft specified
    if "status" in data:
        initial_status = data["status"]
    elif actor_role == "admin":
        initial_status = "published"
    else:
        verified, _ = is_organizer_verified(db, organizer_id)
        initial_status = "published" if verified else "pending_approval"

    if initial_status not in ["draft", "pending_approval", "published"]:
        initial_status = "pending_approval"

    budget_breakdown = data.get("budget_breakdown", [])
    if isinstance(budget_breakdown, str):
        # Allow simple comma/newline separated budget items if submitted as text
        budget_breakdown = [{"item": line.strip()} for line in budget_breakdown.split("\n") if line.strip()]

    event_doc = {
        "title": data["title"].strip(),
        "organizer_id": ObjectId(organizer_id),
        "venue_id": ObjectId(venue_id),
        "description": sanitize_markdown(data["description"].strip()),
        "category": data["category"].strip(),
        "start_time": start_dt,
        "end_time": end_dt,
        "capacity": capacity,
        "registered_count": 0,
        "waitlist_count": 0,
        "status": initial_status,
        "banner_image": data.get("banner_image", ""),
        "budget": {
            "total": float(data.get("budget_total", 0.0)),
            "breakdown": budget_breakdown,
            "approved": actor_role == "admin"
        },
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }

    res = db.events.insert_one(event_doc)
    event_id = res.inserted_id

    create_audit_log(
        db, organizer_id, actor_role, "CREATE_EVENT", "events", event_id,
        {"title": event_doc["title"], "status": initial_status}
    )

    return True, "Event created successfully.", event_id


def update_event(db, event_id, data, actor_id, actor_role):
    """Update event with ownership enforcement."""
    event = db.events.find_one({"_id": ObjectId(event_id)})
    if not event:
        return False, "Event not found."

    # Enforce IDOR ownership: only owning organizer or admin can edit
    if actor_role != "admin" and str(event["organizer_id"]) != str(actor_id):
        return False, "Access denied. You do not have permission to modify this event."

    if event.get("status") in ["archived", "completed"]:
        return False, f"Cannot update an event in '{event.get('status')}' status."

    is_valid, errors = validate_event_data(data, is_update=True)
    if not is_valid:
        return False, "; ".join(errors)

    venue = db.venues.find_one({"_id": ObjectId(data["venue_id"])})
    if not venue:
        return False, "Invalid venue."

    capacity = int(data.get("capacity"))
    if capacity > venue.get("capacity", 0):
        return False, f"Event capacity exceeds venue limit of {venue.get('capacity')}."

    start_dt = data["start_time"] if isinstance(data["start_time"], datetime) else datetime.fromisoformat(data["start_time"])
    end_dt = data["end_time"] if isinstance(data["end_time"], datetime) else datetime.fromisoformat(data["end_time"])

    update_fields = {
        "title": data["title"].strip(),
        "venue_id": ObjectId(data["venue_id"]),
        "description": sanitize_markdown(data["description"].strip()),
        "category": data["category"].strip(),
        "start_time": start_dt,
        "end_time": end_dt,
        "capacity": capacity,
        "budget.total": float(data.get("budget_total", 0.0)),
        "updated_at": datetime.utcnow()
    }

    if data.get("banner_image"):
        update_fields["banner_image"] = data["banner_image"]

    db.events.update_one({"_id": ObjectId(event_id)}, {"$set": update_fields})
    create_audit_log(db, actor_id, actor_role, "UPDATE_EVENT", "events", event_id)

    return True, "Event updated successfully."


def archive_or_delete_event(db, event_id, actor_id, actor_role):
    """Soft-delete / archive event instead of hard deletion."""
    event = db.events.find_one({"_id": ObjectId(event_id)})
    if not event:
        return False, "Event not found."

    if actor_role != "admin" and str(event["organizer_id"]) != str(actor_id):
        return False, "Access denied. Cannot delete another organizer's event."

    db.events.update_one(
        {"_id": ObjectId(event_id)},
        {"$set": {"status": "archived", "updated_at": datetime.utcnow()}}
    )

    # Notify all registered students of cancellation / archival
    regs = db.registrations.find({"event_id": ObjectId(event_id), "status": {"$in": ["registered", "waitlisted"]}})
    for reg in regs:
        db.notifications.insert_one({
            "user_id": reg["student_id"],
            "title": f"Event Archived: {event['title']}",
            "message": f"The event '{event['title']}' has been cancelled or archived by the organizers.",
            "type": "cancellation",
            "is_read": False,
            "is_archived": False,
            "created_at": datetime.utcnow()
        })

    create_audit_log(db, actor_id, actor_role, "ARCHIVE_EVENT", "events", event_id)
    return True, "Event has been archived and attendees notified."


def approve_event(db, event_id, admin_id, approved=True, notes=""):
    """Admin approves or rejects event."""
    event = db.events.find_one({"_id": ObjectId(event_id)})
    if not event:
        return False, "Event not found."

    new_status = "published" if approved else "rejected"
    db.events.update_one(
        {"_id": ObjectId(event_id)},
        {"$set": {
            "status": new_status,
            "admin_review_notes": notes,
            "reviewed_by": ObjectId(admin_id),
            "updated_at": datetime.utcnow()
        }}
    )

    # Notify organizer
    db.notifications.insert_one({
        "user_id": event["organizer_id"],
        "title": f"Event {new_status.capitalize()}: {event['title']}",
        "message": f"Your event '{event['title']}' has been {new_status} by the administrator. {notes}",
        "type": "update",
        "is_read": False,
        "is_archived": False,
        "created_at": datetime.utcnow()
    })

    create_audit_log(db, admin_id, "admin", f"{new_status.upper()}_EVENT", "events", event_id)
    return True, f"Event {new_status} successfully."


def get_public_events(db, category=None, search=None, start_date=None, page=1, per_page=12):
    """
    Search and filter published events with MongoDB Aggregation Pipeline ($lookup venue).
    """
    match_stage = {"status": "published"}

    if category and category != "All":
        match_stage["category"] = category

    if search:
        match_stage["$or"] = [
            {"title": {"$regex": search, "$options": "i"}},
            {"description": {"$regex": search, "$options": "i"}}
        ]

    if start_date:
        try:
            filter_dt = datetime.fromisoformat(start_date)
            match_stage["start_time"] = {"$gte": filter_dt}
        except ValueError:
            pass

    pipeline = [
        {"$match": match_stage},
        {"$lookup": {
            "from": "venues",
            "localField": "venue_id",
            "foreignField": "_id",
            "as": "venue"
        }},
        {"$unwind": {"path": "$venue", "preserveNullAndEmptyArrays": True}},
        {"$lookup": {
            "from": "users",
            "localField": "organizer_id",
            "foreignField": "_id",
            "as": "organizer"
        }},
        {"$unwind": {"path": "$organizer", "preserveNullAndEmptyArrays": True}},
        {"$sort": {"start_time": 1}},
        {"$skip": (page - 1) * per_page},
        {"$limit": per_page}
    ]

    events = list(db.events.aggregate(pipeline))
    total_count = db.events.count_documents(match_stage)

    return events, total_count
