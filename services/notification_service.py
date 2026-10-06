import logging
from datetime import datetime
from bson import ObjectId

logger = logging.getLogger(__name__)


def create_notification(db, user_id, title, message, n_type="update"):
    """Create in-app notification for a user."""
    doc = {
        "user_id": ObjectId(user_id),
        "title": title,
        "message": message,
        "type": n_type,
        "is_read": False,
        "is_archived": False,
        "created_at": datetime.utcnow()
    }
    return db.notifications.insert_one(doc)


def get_user_notifications(db, user_id, include_archived=False):
    """Retrieve notifications for user."""
    query = {"user_id": ObjectId(user_id)}
    if not include_archived:
        query["is_archived"] = False

    notifications = list(db.notifications.find(query).sort("created_at", -1).limit(50))
    unread_count = db.notifications.count_documents({"user_id": ObjectId(user_id), "is_read": False, "is_archived": False})

    return notifications, unread_count


def mark_notification_read(db, notif_id, user_id):
    """Mark single notification as read."""
    db.notifications.update_one(
        {"_id": ObjectId(notif_id), "user_id": ObjectId(user_id)},
        {"$set": {"is_read": True}}
    )
    return True


def mark_all_notifications_read(db, user_id):
    """Mark all active notifications for user as read."""
    db.notifications.update_many(
        {"user_id": ObjectId(user_id), "is_read": False},
        {"$set": {"is_read": True}}
    )
    return True


def archive_notification(db, notif_id, user_id):
    """Archive notification."""
    db.notifications.update_one(
        {"_id": ObjectId(notif_id), "user_id": ObjectId(user_id)},
        {"$set": {"is_archived": True}}
    )
    return True


def delete_notification(db, notif_id, user_id):
    """Delete notification."""
    db.notifications.delete_one({"_id": ObjectId(notif_id), "user_id": ObjectId(user_id)})
    return True


def trigger_event_reminders(db, event_id, actor_id, actor_role):
    """
    Demo task trigger: Sends reminder notifications to all confirmed attendees of an event.
    Simulates automated cron/task scheduler for college evaluation.
    """
    event = db.events.find_one({"_id": ObjectId(event_id)})
    if not event:
        return False, "Event not found.", 0

    if actor_role != "admin" and str(event["organizer_id"]) != str(actor_id):
        return False, "Access denied. Cannot send reminders for other events.", 0

    registrations = list(db.registrations.find({"event_id": ObjectId(event_id), "status": "registered"}))
    sent_count = 0

    for reg in registrations:
        formatted_date = event["start_time"].strftime("%d %b %Y at %I:%M %p")
        db.notifications.insert_one({
            "user_id": reg["student_id"],
            "title": f"Reminder: Upcoming Event '{event['title']}'",
            "message": f"Friendly reminder that '{event['title']}' starts on {formatted_date}. Please carry your QR ticket code: {reg['ticket_code']}.",
            "type": "reminder",
            "is_read": False,
            "is_archived": False,
            "created_at": datetime.utcnow()
        })
        sent_count += 1

    return True, f"Reminder dispatched to {sent_count} registered attendee(s).", sent_count
