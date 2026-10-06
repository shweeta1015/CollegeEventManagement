from datetime import datetime, timedelta
from bson import ObjectId
from services.registration_service import register_for_event, cancel_registration
from services.event_service import create_event


def test_registration_and_duplicate_prevention(db, test_users, test_venue):
    """Test successful registration and rejection of duplicate active registration."""
    now = datetime.utcnow()
    event_data = {
        "title": "Quantum Computing Primer",
        "category": "Seminar",
        "venue_id": str(test_venue["_id"]),
        "start_time": (now + timedelta(days=5)).isoformat(),
        "end_time": (now + timedelta(days=5, hours=2)).isoformat(),
        "capacity": 20,
        "description": "An introduction to quantum algorithms, qubits, and quantum circuit simulation for students.",
        "budget_total": 0.0
    }
    _, _, ev_id = create_event(db, event_data, test_users["org_verified"]["_id"], "organizer")

    # 1. First registration
    ok1, msg1, reg1 = register_for_event(db, ev_id, test_users["student1"]["_id"])
    assert ok1 is True
    assert reg1["status"] == "registered"
    assert reg1["ticket_code"].startswith("TKT-")

    # Check event registered_count
    ev = db.events.find_one({"_id": ev_id})
    assert ev["registered_count"] == 1

    # 2. Duplicate registration attempt by same student
    ok2, msg2, _ = register_for_event(db, ev_id, test_users["student1"]["_id"])
    assert ok2 is False
    assert "already" in msg2.lower()

    # registered_count should not increase
    ev_check = db.events.find_one({"_id": ev_id})
    assert ev_check["registered_count"] == 1


def test_capacity_concurrency_and_waitlisting(db, test_users, test_venue):
    """
    Test zero-overbooking capacity control and automatic waitlisting:
    Event capacity = 1
    Student 1 registers -> Confirmed
    Student 2 registers -> Placed on Waitlist
    Student 1 cancels -> Student 2 automatically promoted to Confirmed!
    """
    now = datetime.utcnow()
    event_data = {
        "title": "Exclusive High Performance Computing Lab",
        "category": "Workshop",
        "venue_id": str(test_venue["_id"]),
        "start_time": (now + timedelta(days=7)).isoformat(),
        "end_time": (now + timedelta(days=7, hours=3)).isoformat(),
        "capacity": 1,  # Only 1 seat available!
        "description": "Hands-on cluster configuration workshop with strictly limited hardware seats for participants.",
        "budget_total": 0.0
    }
    _, _, ev_id = create_event(db, event_data, test_users["org_verified"]["_id"], "organizer")

    # Student 1 gets the single available seat
    ok1, _, reg1 = register_for_event(db, ev_id, test_users["student1"]["_id"])
    assert ok1 is True
    assert reg1["status"] == "registered"

    ev_state1 = db.events.find_one({"_id": ev_id})
    assert ev_state1["registered_count"] == 1
    assert ev_state1["waitlist_count"] == 0

    # Student 2 attempts to register -> event is full -> placed on waitlist
    ok2, msg2, reg2 = register_for_event(db, ev_id, test_users["student2"]["_id"])
    assert ok2 is True
    assert reg2["status"] == "waitlisted"
    assert "waitlist" in msg2.lower()

    ev_state2 = db.events.find_one({"_id": ev_id})
    assert ev_state2["registered_count"] == 1
    assert ev_state2["waitlist_count"] == 1

    # Student 1 cancels their confirmed registration
    ok_cancel, cancel_msg = cancel_registration(db, reg1["registration_id"], test_users["student1"]["_id"])
    assert ok_cancel is True

    # Student 2 should now be automatically promoted to 'registered'
    reg2_updated = db.registrations.find_one({"_id": ObjectId(reg2["registration_id"])})
    assert reg2_updated["status"] == "registered"

    # Event counts should reflect confirmed seat for student 2 and 0 waitlisted
    ev_state3 = db.events.find_one({"_id": ev_id})
    assert ev_state3["registered_count"] == 1
    assert ev_state3["waitlist_count"] == 0

    # Check notification dispatched to student 2 informing them of promotion
    notif = db.notifications.find_one({"user_id": test_users["student2"]["_id"], "type": "waitlist_promoted"})
    assert notif is not None
    assert "CONFIRMED" in notif["message"]
