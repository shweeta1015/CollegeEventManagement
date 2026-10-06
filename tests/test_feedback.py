from datetime import datetime, timedelta
from bson import ObjectId
from services.feedback_service import (
    submit_feedback, update_feedback, respond_to_feedback
)
from services.registration_service import register_for_event, check_in_attendee
from services.event_service import create_event
from models.sentiment import analyze_sentiment_demo


def test_feedback_requires_verified_attendance(db, test_users, test_venue):
    """Test attendance prerequisite: only students with 'checked-in' status can submit feedback."""
    now = datetime.utcnow()
    event_data = {
        "title": "Machine Learning Fundamentals",
        "category": "Academic",
        "venue_id": str(test_venue["_id"]),
        "start_time": (now + timedelta(days=2)).isoformat(),
        "end_time": (now + timedelta(days=2, hours=3)).isoformat(),
        "capacity": 20,
        "description": "Foundations of supervised and unsupervised machine learning models, loss functions, and gradient descent.",
        "budget_total": 0.0
    }
    _, _, ev_id = create_event(db, event_data, test_users["org_verified"]["_id"], "organizer")
    _, _, reg = register_for_event(db, ev_id, test_users["student1"]["_id"])

    # 1. Attempt before check-in (status is 'registered')
    fail_ok, fail_msg, _ = submit_feedback(db, ev_id, test_users["student1"]["_id"], rating=5, comment="Great session!")
    assert fail_ok is False
    assert "only students who attended" in fail_msg.lower()

    # 2. Check in attendee
    check_in_attendee(db, reg["ticket_code"], test_users["org_verified"]["_id"], "organizer")

    # 3. Attempt after check-in (status is 'checked-in') -> succeeds
    succ_ok, succ_msg, fb_id = submit_feedback(
        db, ev_id, test_users["student1"]["_id"], rating=5,
        comment="The hands-on coding was fantastic, clear, and very helpful."
    )
    assert succ_ok is True
    assert fb_id is not None

    fb = db.feedback.find_one({"_id": fb_id})
    assert fb["rating"] == 5
    assert fb["sentiment_label"] == "Positive"


def test_sentiment_analysis_demo_categorization():
    """Verify keyword-based sentiment demo classifier output."""
    pos = analyze_sentiment_demo("The speaker was fantastic, engaging, and clear!")
    assert pos["label"] == "Positive"
    assert "fantastic" in pos["matched_positive"]

    neg = analyze_sentiment_demo("The event was delayed, crowded, and very boring.")
    assert neg["label"] == "Constructive/Negative"
    assert "delayed" in neg["matched_negative"]

    neutral = analyze_sentiment_demo("Attended the presentation from campus hall.")
    assert neutral["label"] == "Neutral"


def test_organizer_response_to_feedback(db, test_users, test_venue):
    """Test organizer can respond to feedback on their event."""
    now = datetime.utcnow()
    event_data = {
        "title": "Data Structures Workshop",
        "category": "Workshop",
        "venue_id": str(test_venue["_id"]),
        "start_time": (now + timedelta(days=2)).isoformat(),
        "end_time": (now + timedelta(days=2, hours=3)).isoformat(),
        "capacity": 20,
        "description": "Detailed review of binary search trees, AVL trees, and amortized complexity analysis.",
        "budget_total": 0.0
    }
    _, _, ev_id = create_event(db, event_data, test_users["org_verified"]["_id"], "organizer")
    _, _, reg = register_for_event(db, ev_id, test_users["student1"]["_id"])
    check_in_attendee(db, reg["ticket_code"], test_users["org_verified"]["_id"], "organizer")

    _, _, fb_id = submit_feedback(db, ev_id, test_users["student1"]["_id"], rating=4, comment="Good workshop!")

    # Organizer replies
    ok, msg = respond_to_feedback(
        db, fb_id, test_users["org_verified"]["_id"],
        "Thank you for participating! Glad the tree examples helped.", "organizer"
    )
    assert ok is True

    fb = db.feedback.find_one({"_id": fb_id})
    assert fb["organizer_response"] is not None
    assert "tree examples" in fb["organizer_response"]["text"]
