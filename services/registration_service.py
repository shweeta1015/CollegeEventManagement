import io
import base64
import uuid
import logging
from datetime import datetime
from bson import ObjectId
from pymongo import ReturnDocument
import qrcode

from database import create_audit_log

logger = logging.getLogger(__name__)


def generate_qr_code_base64(ticket_data):
    """
    Generate a QR code image encoded as Base64 data URI using qrcode package.
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=2,
    )
    qr.add_data(ticket_data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#1a202c", back_color="#ffffff")

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    b64_str = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{b64_str}"


def register_for_event(db, event_id, student_id, ip_address="127.0.0.1"):
    """
    Atomic event registration with concurrency control:
    1. Checks if student already has an active registration (registered, waitlisted, or checked-in).
    2. Atomically increments registered_count if registered_count < capacity using find_one_and_update.
       Demonstrates MongoDB conditional atomic update pattern to guarantee zero overbooking.
    3. If capacity reached, registers student on waitlist.
    4. Generates unique cryptographic QR ticket token for confirmed attendees.
    5. Dispatches in-app notification.
    """
    ev_oid = ObjectId(event_id)
    st_oid = ObjectId(student_id)

    event = db.events.find_one({"_id": ev_oid})
    if not event:
        return False, "Event does not exist.", None

    if event.get("status") != "published":
        return False, f"Event is not open for registration (status: {event.get('status')}).", None

    if event.get("start_time") <= datetime.utcnow():
        return False, "Cannot register for an event that has already commenced or concluded.", None

    # Check for duplicate active registration
    existing = db.registrations.find_one({
        "event_id": ev_oid,
        "student_id": st_oid,
        "status": {"$in": ["registered", "waitlisted", "checked-in"]}
    })
    if existing:
        return False, f"You are already {existing.get('status')} for this event.", None

    # Atomic capacity reservation: check capacity condition in query filter
    capacity = int(event.get("capacity", 0))
    updated_event = db.events.find_one_and_update(
        {
            "_id": ev_oid,
            "registered_count": {"$lt": capacity},
            "status": "published"
        },
        {"$inc": {"registered_count": 1}, "$set": {"updated_at": datetime.utcnow()}},
        return_document=ReturnDocument.AFTER
    )

    ticket_code = f"TKT-{uuid.uuid4().hex[:12].upper()}"
    now = datetime.utcnow()

    if updated_event:
        # Confirmed Seat Secured
        status = "registered"
        msg = f"Registration confirmed! Your ticket code is {ticket_code}."
    else:
        # Event is Full -> Queue on Waitlist
        status = "waitlisted"
        db.events.update_one({"_id": ev_oid}, {"$inc": {"waitlist_count": 1}})
        msg = "The event is currently at maximum capacity. You have been placed on the priority waitlist."

    reg_doc = {
        "event_id": ev_oid,
        "student_id": st_oid,
        "ticket_code": ticket_code,
        "status": status,
        "registered_at": now,
        "check_in_time": None,
        "check_in_by": None,
        "created_at": now,
        "updated_at": now
    }

    res = db.registrations.insert_one(reg_doc)

    # In-app notification
    db.notifications.insert_one({
        "user_id": st_oid,
        "title": f"Registration: {event.get('title')}",
        "message": msg,
        "type": "registration",
        "is_read": False,
        "is_archived": False,
        "created_at": now
    })

    create_audit_log(
        db, student_id, "student", f"REGISTER_EVENT_{status.upper()}", "registrations",
        res.inserted_id, {"ticket_code": ticket_code, "status": status}, ip_address=ip_address
    )

    return True, msg, {
        "registration_id": str(res.inserted_id),
        "ticket_code": ticket_code,
        "status": status
    }


def cancel_registration(db, registration_id, student_id, actor_role="student"):
    """
    Cancel an existing registration.
    If a confirmed registration is cancelled:
    - Atomically decrements registered_count.
    - Automatically checks waitlist and promotes the oldest waitlisted student to 'registered'!
    - Notifies the promoted student immediately.
    """
    reg = db.registrations.find_one({"_id": ObjectId(registration_id)})
    if not reg:
        return False, "Registration not found."

    # IDOR check
    if actor_role != "admin" and str(reg["student_id"]) != str(student_id):
        return False, "Access denied. Cannot cancel another student's registration."

    if reg.get("status") in ["cancelled", "checked-in"]:
        return False, f"Cannot cancel registration with status: {reg.get('status')}."

    prev_status = reg.get("status")
    now = datetime.utcnow()

    # Update registration to cancelled
    db.registrations.update_one(
        {"_id": reg["_id"]},
        {"$set": {"status": "cancelled", "updated_at": now}}
    )

    ev_oid = reg["event_id"]
    event = db.events.find_one({"_id": ev_oid})

    if prev_status == "registered":
        # Free up capacity counter
        db.events.update_one({"_id": ev_oid}, {"$inc": {"registered_count": -1}})

        # Auto-promote oldest waitlisted student (FIFO queue via sorting by registered_at ASC)
        oldest_waitlisted = db.registrations.find_one_and_update(
            {"event_id": ev_oid, "status": "waitlisted"},
            {"$set": {"status": "registered", "updated_at": now}},
            sort=[("registered_at", 1)],
            return_document=ReturnDocument.AFTER
        )

        if oldest_waitlisted:
            # Re-increment registered_count for promoted student & decrement waitlist
            db.events.update_one({"_id": ev_oid}, {
                "$inc": {"registered_count": 1, "waitlist_count": -1}
            })
            # Send high-priority notification to promoted student
            db.notifications.insert_one({
                "user_id": oldest_waitlisted["student_id"],
                "title": f"Waitlist Promotion: {event.get('title')}",
                "message": f"Great news! A seat opened up and your registration for '{event.get('title')}' is now CONFIRMED! Your ticket code is {oldest_waitlisted['ticket_code']}.",
                "type": "waitlist_promoted",
                "is_read": False,
                "is_archived": False,
                "created_at": now
            })
    elif prev_status == "waitlisted":
        db.events.update_one({"_id": ev_oid}, {"$inc": {"waitlist_count": -1}})

    create_audit_log(
        db, student_id, actor_role, "CANCEL_REGISTRATION", "registrations",
        reg["_id"], {"previous_status": prev_status}
    )

    return True, "Registration has been cancelled successfully."


def check_in_attendee(db, ticket_code, organizer_id, actor_role):
    """
    Validate QR ticket and perform check-in:
    - Verifies ticket exists and is associated with event.
    - Prevents double check-in.
    - Ensures organizer has ownership of this event.
    - Atomically updates status to 'checked-in' and records timestamp.
    """
    clean_code = str(ticket_code or "").strip().upper()
    if not clean_code:
        return False, "Ticket code is required.", None

    reg = db.registrations.find_one({"ticket_code": clean_code})
    if not reg:
        return False, "Invalid ticket code. No matching registration found.", None

    event = db.events.find_one({"_id": reg["event_id"]})
    if not event:
        return False, "Associated event could not be found.", None

    # Enforce organizer permissions
    if actor_role != "admin" and str(event["organizer_id"]) != str(organizer_id):
        return False, "Permission denied. You can only check-in attendees for your own events.", None

    if reg.get("status") == "checked-in":
        formatted_time = reg.get("check_in_time", datetime.utcnow()).strftime("%Y-%m-%d %H:%M:%S")
        return False, f"Ticket already used! Checked in previously at {formatted_time}.", None

    if reg.get("status") == "cancelled":
        return False, "Invalid check-in attempt: This registration was previously cancelled.", None

    if reg.get("status") == "waitlisted":
        return False, "Student is on waitlist. Only confirmed registrations can check in.", None

    now = datetime.utcnow()
    db.registrations.update_one(
        {"_id": reg["_id"]},
        {"$set": {
            "status": "checked-in",
            "check_in_time": now,
            "check_in_by": ObjectId(organizer_id),
            "updated_at": now
        }}
    )

    student = db.users.find_one({"_id": reg["student_id"]})
    student_name = student.get("full_name", "Student") if student else "Student"

    # Send confirmation notification to student
    db.notifications.insert_one({
        "user_id": reg["student_id"],
        "title": f"Checked in: {event.get('title')}",
        "message": f"Welcome! Your attendance for '{event.get('title')}' has been verified. You can now submit your feedback.",
        "type": "update",
        "is_read": False,
        "is_archived": False,
        "created_at": now
    })

    create_audit_log(
        db, organizer_id, actor_role, "CHECK_IN_ATTENDEE", "registrations",
        reg["_id"], {"ticket_code": clean_code, "student_id": str(reg['student_id'])}
    )

    return True, f"Check-in verified successfully for {student_name}!", {
        "student_name": student_name,
        "ticket_code": clean_code,
        "check_in_time": now.strftime("%I:%M %p, %d %b %Y")
    }


def get_student_registrations(db, student_id):
    """Retrieve all registrations for a student with event and venue details."""
    pipeline = [
        {"$match": {"student_id": ObjectId(student_id)}},
        {"$lookup": {
            "from": "events",
            "localField": "event_id",
            "foreignField": "_id",
            "as": "event"
        }},
        {"$unwind": "$event"},
        {"$lookup": {
            "from": "venues",
            "localField": "event.venue_id",
            "foreignField": "_id",
            "as": "venue"
        }},
        {"$unwind": {"path": "$venue", "preserveNullAndEmptyArrays": True}},
        {"$sort": {"registered_at": -1}}
    ]
    return list(db.registrations.aggregate(pipeline))
