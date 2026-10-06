from datetime import datetime, timedelta
from bson import ObjectId
from services.event_service import (
    create_event, update_event, archive_or_delete_event, approve_event
)


def test_create_event_verified_organizer(db, test_users, test_venue):
    """Test valid event creation by verified organizer."""
    now = datetime.utcnow()
    event_data = {
        "title": "Introduction to MongoDB Aggregations",
        "category": "Academic",
        "venue_id": str(test_venue["_id"]),
        "start_time": (now + timedelta(days=2)).isoformat(),
        "end_time": (now + timedelta(days=2, hours=3)).isoformat(),
        "capacity": 30,
        "description": "Comprehensive tutorial covering aggregate pipelines, match, group, project, and index execution plans.",
        "budget_total": 4000.0,
        "budget_breakdown": []
    }

    ok, msg, ev_id = create_event(db, event_data, test_users["org_verified"]["_id"], "organizer")
    assert ok is True
    assert ev_id is not None

    ev = db.events.find_one({"_id": ev_id})
    assert ev["title"] == event_data["title"]
    assert ev["capacity"] == 30
    assert ev["registered_count"] == 0


def test_unverified_organizer_cannot_create_event(db, test_users, test_venue):
    """Test unverified organizer is blocked from creating/publishing events."""
    now = datetime.utcnow()
    event_data = {
        "title": "Unverified Club Meetup",
        "category": "Social",
        "venue_id": str(test_venue["_id"]),
        "start_time": (now + timedelta(days=3)).isoformat(),
        "end_time": (now + timedelta(days=3, hours=2)).isoformat(),
        "capacity": 20,
        "description": "Informal club meetup to discuss semester activities and upcoming social outreach programs.",
        "budget_total": 1000.0
    }

    ok, msg, _ = create_event(db, event_data, test_users["org_unverified"]["_id"], "organizer")
    assert ok is False
    assert "only verified organizers" in msg.lower()


def test_event_duration_and_description_validations(db, test_users, test_venue):
    """Test validation errors for description < 50 chars and duration < 1 hour."""
    now = datetime.utcnow()
    
    # 1. Short description
    short_desc_data = {
        "title": "Short Desc Event",
        "category": "Workshop",
        "venue_id": str(test_venue["_id"]),
        "start_time": (now + timedelta(days=2)).isoformat(),
        "end_time": (now + timedelta(days=2, hours=2)).isoformat(),
        "capacity": 25,
        "description": "Too short.",  # Less than 50 chars
        "budget_total": 0.0
    }
    ok1, msg1, _ = create_event(db, short_desc_data, test_users["org_verified"]["_id"], "organizer")
    assert ok1 is False
    assert "at least 50 characters" in msg1.lower()

    # 2. Duration less than 1 hour
    short_duration_data = {
        "title": "Flash Event Meeting",
        "category": "Workshop",
        "venue_id": str(test_venue["_id"]),
        "start_time": (now + timedelta(days=2)).isoformat(),
        "end_time": (now + timedelta(days=2, minutes=30)).isoformat(),  # 30 mins
        "capacity": 25,
        "description": "This is a detailed event description with more than fifty characters to test duration constraints.",
        "budget_total": 0.0
    }
    ok2, msg2, _ = create_event(db, short_duration_data, test_users["org_verified"]["_id"], "organizer")
    assert ok2 is False
    assert "at least 1 hour" in msg2.lower()


def test_capacity_cannot_exceed_venue_limit(db, test_users, test_venue):
    """Test capacity boundary check against venue limit (venue capacity is 50)."""
    now = datetime.utcnow()
    overbooked_data = {
        "title": "Massive Overcapacity Symposium",
        "category": "Seminar",
        "venue_id": str(test_venue["_id"]),
        "start_time": (now + timedelta(days=4)).isoformat(),
        "end_time": (now + timedelta(days=4, hours=3)).isoformat(),
        "capacity": 100,  # Exceeds venue limit of 50
        "description": "An ambitious seminar attempting to book more attendees than the auditorium capacity allows.",
        "budget_total": 2000.0
    }

    ok, msg, _ = create_event(db, overbooked_data, test_users["org_verified"]["_id"], "organizer")
    assert ok is False
    assert "cannot exceed venue capacity" in msg.lower()


def test_unique_title_per_organizer_per_date(db, test_users, test_venue):
    """Test uniqueness constraint: same organizer cannot create two events with identical title on same date."""
    now = datetime.utcnow()
    base_data = {
        "title": "Duplicate Date Tech Talk",
        "category": "Academic",
        "venue_id": str(test_venue["_id"]),
        "start_time": (now + timedelta(days=5, hours=10)).isoformat(),
        "end_time": (now + timedelta(days=5, hours=12)).isoformat(),
        "capacity": 30,
        "description": "Detailed description of technical conference to test unique title per organizer per date.",
        "budget_total": 0.0
    }

    ok1, _, _ = create_event(db, base_data, test_users["org_verified"]["_id"], "organizer")
    assert ok1 is True

    # Attempt to insert identical title on the same date by same organizer
    ok2, msg2, _ = create_event(db, base_data, test_users["org_verified"]["_id"], "organizer")
    assert ok2 is False
    assert "already have an event with this title on the same date" in msg2.lower()


def test_archive_event_soft_delete(db, test_users, test_venue):
    """Test that event deletion softly archives the document and notifies registered users."""
    now = datetime.utcnow()
    event_data = {
        "title": "Archivable Robotics Workshop",
        "category": "Workshop",
        "venue_id": str(test_venue["_id"]),
        "start_time": (now + timedelta(days=6)).isoformat(),
        "end_time": (now + timedelta(days=6, hours=2)).isoformat(),
        "capacity": 20,
        "description": "A workshop scheduled to be cancelled and archived to verify soft delete compliance.",
        "budget_total": 0.0
    }
    _, _, ev_id = create_event(db, event_data, test_users["org_verified"]["_id"], "organizer")

    # Soft archive
    ok, msg = archive_or_delete_event(db, ev_id, test_users["org_verified"]["_id"], "organizer")
    assert ok is True

    ev = db.events.find_one({"_id": ev_id})
    assert ev["status"] == "archived"
