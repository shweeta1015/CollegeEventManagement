from datetime import datetime, timedelta
from bson import ObjectId
from services.registration_service import register_for_event, check_in_attendee
from services.event_service import create_event


def test_valid_qr_checkin(db, test_users, test_venue):
    """Test standard check-in flow with valid ticket code."""
    now = datetime.utcnow()
    event_data = {
        "title": "Cloud Architecture Deep Dive",
        "category": "Academic",
        "venue_id": str(test_venue["_id"]),
        "start_time": (now + timedelta(days=2)).isoformat(),
        "end_time": (now + timedelta(days=2, hours=3)).isoformat(),
        "capacity": 20,
        "description": "Exploration of scalable microservices, container orchestration, and serverless backends.",
        "budget_total": 0.0
    }
    _, _, ev_id = create_event(db, event_data, test_users["org_verified"]["_id"], "organizer")
    _, _, reg = register_for_event(db, ev_id, test_users["student1"]["_id"])

    ticket_code = reg["ticket_code"]

    # Organizer checks in attendee
    ok, msg, data = check_in_attendee(db, ticket_code, test_users["org_verified"]["_id"], "organizer")
    assert ok is True
    assert "verified successfully" in msg.lower()

    # Verify database record updated
    updated_reg = db.registrations.find_one({"ticket_code": ticket_code})
    assert updated_reg["status"] == "checked-in"
    assert updated_reg["check_in_time"] is not None


def test_duplicate_checkin_prevented(db, test_users, test_venue):
    """Test duplicate check-in rejection: once scanned, ticket cannot be used again."""
    now = datetime.utcnow()
    event_data = {
        "title": "Cybersecurity Defenses Summit",
        "category": "Workshop",
        "venue_id": str(test_venue["_id"]),
        "start_time": (now + timedelta(days=3)).isoformat(),
        "end_time": (now + timedelta(days=3, hours=3)).isoformat(),
        "capacity": 20,
        "description": "Network penetration testing, threat hunting, and defensive hardening methodologies.",
        "budget_total": 0.0
    }
    _, _, ev_id = create_event(db, event_data, test_users["org_verified"]["_id"], "organizer")
    _, _, reg = register_for_event(db, ev_id, test_users["student1"]["_id"])

    ticket_code = reg["ticket_code"]

    # First check-in succeeds
    ok1, _, _ = check_in_attendee(db, ticket_code, test_users["org_verified"]["_id"], "organizer")
    assert ok1 is True

    # Second check-in must fail
    ok2, err_msg, _ = check_in_attendee(db, ticket_code, test_users["org_verified"]["_id"], "organizer")
    assert ok2 is False
    assert "already used" in err_msg.lower()


def test_unauthorized_organizer_checkin_denied(db, test_users, test_venue):
    """Test IDOR protection: Organizer B cannot check-in attendees for Organizer A's event."""
    now = datetime.utcnow()
    event_data = {
        "title": "Organizer A Event Exclusive",
        "category": "Seminar",
        "venue_id": str(test_venue["_id"]),
        "start_time": (now + timedelta(days=4)).isoformat(),
        "end_time": (now + timedelta(days=4, hours=2)).isoformat(),
        "capacity": 20,
        "description": "Private departmental discussion on curriculum enhancements and accreditation requirements.",
        "budget_total": 0.0
    }
    # Created by org_verified
    _, _, ev_id = create_event(db, event_data, test_users["org_verified"]["_id"], "organizer")
    _, _, reg = register_for_event(db, ev_id, test_users["student1"]["_id"])

    ticket_code = reg["ticket_code"]

    # org_unverified (different organizer) tries to check-in attendee
    ok, err_msg, _ = check_in_attendee(db, ticket_code, test_users["org_unverified"]["_id"], "organizer")
    assert ok is False
    assert "permission denied" in err_msg.lower()
