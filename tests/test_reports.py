from datetime import datetime, timedelta
from bson import ObjectId
from services.report_service import (
    get_admin_dashboard_metrics, export_event_attendees_csv, export_admin_events_csv
)
from services.event_service import create_event
from services.registration_service import register_for_event, check_in_attendee


def test_admin_metrics_aggregation_pipelines(db, test_users, test_venue):
    """Test multi-stage aggregation pipeline calculating metrics and attendance percentage."""
    now = datetime.utcnow()
    event_data = {
        "title": "Big Data Engineering Seminar",
        "category": "Academic",
        "venue_id": str(test_venue["_id"]),
        "start_time": (now + timedelta(days=2)).isoformat(),
        "end_time": (now + timedelta(days=2, hours=3)).isoformat(),
        "capacity": 20,
        "description": "Exploration of map-reduce paradigms, distributed file systems, and column-family stores.",
        "budget_total": 0.0
    }
    _, _, ev_id = create_event(db, event_data, test_users["org_verified"]["_id"], "organizer")

    # Register student 1 and student 2
    _, _, reg1 = register_for_event(db, ev_id, test_users["student1"]["_id"])
    _, _, reg2 = register_for_event(db, ev_id, test_users["student2"]["_id"])

    # Check-in student 1 (attendance = 1 out of 2 = 50.0%)
    check_in_attendee(db, reg1["ticket_code"], test_users["org_verified"]["_id"], "organizer")

    metrics = get_admin_dashboard_metrics(db)

    assert metrics["total_events"] >= 1
    assert metrics["total_registrations"] >= 2
    assert metrics["checked_in_count"] >= 1
    assert metrics["attendance_rate"] == 50.0
    assert len(metrics["category_distribution"]) >= 1


def test_csv_export_generation(db, test_users, test_venue):
    """Test attendee and admin events CSV exports contain proper column headers and rows."""
    now = datetime.utcnow()
    event_data = {
        "title": "CSV Export Verification Fest",
        "category": "Cultural",
        "venue_id": str(test_venue["_id"]),
        "start_time": (now + timedelta(days=5)).isoformat(),
        "end_time": (now + timedelta(days=5, hours=4)).isoformat(),
        "capacity": 30,
        "description": "Cultural event organized to verify CSV generation pipelines and attendee rosters.",
        "budget_total": 5000.0
    }
    _, _, ev_id = create_event(db, event_data, test_users["org_verified"]["_id"], "organizer")
    _, _, reg = register_for_event(db, ev_id, test_users["student1"]["_id"])

    # Export attendee CSV
    attendee_csv = export_event_attendees_csv(db, ev_id)
    assert "Ticket Code" in attendee_csv
    assert "Student Name" in attendee_csv
    assert reg["ticket_code"] in attendee_csv

    # Export admin summary CSV
    admin_csv = export_admin_events_csv(db)
    assert "Event ID" in admin_csv
    assert "CSV Export Verification Fest" in admin_csv
