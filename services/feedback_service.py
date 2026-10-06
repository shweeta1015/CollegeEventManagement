import logging
from datetime import datetime
from bson import ObjectId

from models.validators import validate_feedback_data
from models.sentiment import analyze_sentiment_demo
from database import create_audit_log

logger = logging.getLogger(__name__)


def submit_feedback(db, event_id, student_id, rating, comment):
    """
    Submit post-event feedback:
    - Strictly checks that student ATTENDED (checked-in) the event.
    - Validates rating (1-5) and comment length.
    - Runs keyword-based demo sentiment classification.
    - Prevents duplicate feedback for the same student and event.
    """
    ev_oid = ObjectId(event_id)
    st_oid = ObjectId(student_id)

    # 1. Verify attendance
    attendance = db.registrations.find_one({
        "event_id": ev_oid,
        "student_id": st_oid,
        "status": "checked-in"
    })
    if not attendance:
        return False, "Attendance verification failed: Only students who attended (checked in) can submit feedback.", None

    # 2. Check for existing feedback
    existing = db.feedback.find_one({"event_id": ev_oid, "student_id": st_oid})
    if existing:
        return False, "You have already submitted feedback for this event. You can edit your existing feedback.", None

    # 3. Validate
    is_valid, errors = validate_feedback_data(rating, comment)
    if not is_valid:
        return False, "; ".join(errors), None

    sentiment_res = analyze_sentiment_demo(comment)

    feedback_doc = {
        "event_id": ev_oid,
        "student_id": st_oid,
        "rating": int(rating),
        "comment": comment.strip() if comment else "",
        "sentiment_label": sentiment_res["label"],
        "sentiment_score": sentiment_res["score"],
        "sentiment_keywords": {
            "positive": sentiment_res["matched_positive"],
            "negative": sentiment_res["matched_negative"]
        },
        "organizer_response": None,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }

    res = db.feedback.insert_one(feedback_doc)

    # Send notification to event organizer
    event = db.events.find_one({"_id": ev_oid})
    if event:
        db.notifications.insert_one({
            "user_id": event["organizer_id"],
            "title": f"New Feedback: {event.get('title')}",
            "message": f"A student submitted a {rating}-star rating for your event.",
            "type": "update",
            "is_read": False,
            "is_archived": False,
            "created_at": datetime.utcnow()
        })

    create_audit_log(
        db, student_id, "student", "SUBMIT_FEEDBACK", "feedback", res.inserted_id,
        {"rating": int(rating), "sentiment": sentiment_res["label"]}
    )

    return True, "Feedback submitted successfully!", res.inserted_id


def update_feedback(db, feedback_id, student_id, rating, comment):
    """Allow student to edit their own feedback."""
    fb = db.feedback.find_one({"_id": ObjectId(feedback_id)})
    if not fb:
        return False, "Feedback not found."

    if str(fb["student_id"]) != str(student_id):
        return False, "Access denied. Cannot edit another student's feedback."

    is_valid, errors = validate_feedback_data(rating, comment)
    if not is_valid:
        return False, "; ".join(errors)

    sentiment_res = analyze_sentiment_demo(comment)

    db.feedback.update_one(
        {"_id": fb["_id"]},
        {"$set": {
            "rating": int(rating),
            "comment": comment.strip() if comment else "",
            "sentiment_label": sentiment_res["label"],
            "sentiment_score": sentiment_res["score"],
            "sentiment_keywords": {
                "positive": sentiment_res["matched_positive"],
                "negative": sentiment_res["matched_negative"]
            },
            "updated_at": datetime.utcnow()
        }}
    )
    return True, "Feedback updated successfully."


def delete_feedback(db, feedback_id, student_id, actor_role="student"):
    """Delete student feedback (owner or admin)."""
    fb = db.feedback.find_one({"_id": ObjectId(feedback_id)})
    if not fb:
        return False, "Feedback not found."

    if actor_role != "admin" and str(fb["student_id"]) != str(student_id):
        return False, "Access denied. Cannot delete another user's feedback."

    db.feedback.delete_one({"_id": fb["_id"]})
    return True, "Feedback deleted."


def respond_to_feedback(db, feedback_id, organizer_id, response_text, actor_role):
    """Organizer responds to feedback on their event."""
    fb = db.feedback.find_one({"_id": ObjectId(feedback_id)})
    if not fb:
        return False, "Feedback not found."

    event = db.events.find_one({"_id": fb["event_id"]})
    if not event:
        return False, "Event not found."

    if actor_role != "admin" and str(event["organizer_id"]) != str(organizer_id):
        return False, "Permission denied: You can only respond to feedback on your own events."

    clean_text = str(response_text or "").strip()
    if not clean_text:
        return False, "Response text cannot be empty."

    db.feedback.update_one(
        {"_id": fb["_id"]},
        {"$set": {
            "organizer_response": {
                "text": clean_text,
                "responded_by": ObjectId(organizer_id),
                "responded_at": datetime.utcnow()
            },
            "updated_at": datetime.utcnow()
        }}
    )

    # Notify student
    db.notifications.insert_one({
        "user_id": fb["student_id"],
        "title": f"Organizer Replied: {event.get('title')}",
        "message": f"The organizer of '{event.get('title')}' replied to your feedback.",
        "type": "update",
        "is_read": False,
        "is_archived": False,
        "created_at": datetime.utcnow()
    })

    return True, "Response posted successfully."


def get_event_feedback(db, event_id):
    """Retrieve all feedback for an event with student names."""
    pipeline = [
        {"$match": {"event_id": ObjectId(event_id)}},
        {"$lookup": {
            "from": "users",
            "localField": "student_id",
            "foreignField": "_id",
            "as": "student"
        }},
        {"$unwind": "$student"},
        {"$project": {
            "rating": 1,
            "comment": 1,
            "sentiment_label": 1,
            "sentiment_score": 1,
            "sentiment_keywords": 1,
            "organizer_response": 1,
            "created_at": 1,
            "student_name": "$student.full_name",
            "student_id": 1
        }},
        {"$sort": {"created_at": -1}}
    ]
    return list(db.feedback.aggregate(pipeline))
