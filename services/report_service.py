import csv
import io
import logging
from datetime import datetime
from bson import ObjectId

logger = logging.getLogger(__name__)


def get_admin_dashboard_metrics(db):
    """
    Compute comprehensive administrative metrics using MongoDB Aggregation Framework.
    Demonstrates complex aggregation stages: $group, $facet, $project, $lookup, $unwind.
    """
    now = datetime.utcnow()

    # 1. Event Status Distribution
    event_status_pipeline = [
        {"$group": {
            "_id": "$status",
            "count": {"$sum": 1},
            "total_registered": {"$sum": "$registered_count"},
            "total_capacity": {"$sum": "$capacity"}
        }}
    ]
    event_status_agg = list(db.events.aggregate(event_status_pipeline))
    event_stats = {item["_id"]: item for item in event_status_agg}

    total_events = sum(item["count"] for item in event_status_agg)
    active_events = event_stats.get("published", {}).get("count", 0)
    pending_events = event_stats.get("pending_approval", {}).get("count", 0)
    archived_events = event_stats.get("archived", {}).get("count", 0)
    cancelled_events = event_stats.get("cancelled", {}).get("count", 0)

    # 2. User Distribution by Role
    user_pipeline = [
        {"$group": {
            "_id": "$role",
            "count": {"$sum": 1},
            "active_count": {"$sum": {"$cond": ["$is_active", 1, 0]}}
        }}
    ]
    user_agg = list(db.users.aggregate(user_pipeline))
    user_counts = {item["_id"]: item["count"] for item in user_agg}

    # 3. Registration Status Metrics (Overall Attendance & No-Show Rate)
    reg_status_pipeline = [
        {"$group": {
            "_id": "$status",
            "count": {"$sum": 1}
        }}
    ]
    reg_agg = list(db.registrations.aggregate(reg_status_pipeline))
    reg_counts = {item["_id"]: item["count"] for item in reg_agg}

    total_registrations = sum(reg_counts.values())
    checked_in = reg_counts.get("checked-in", 0)
    registered_active = reg_counts.get("registered", 0)
    waitlisted = reg_counts.get("waitlisted", 0)
    cancelled = reg_counts.get("cancelled", 0)

    # Calculate real-time attendance rate: checked-in / (checked-in + registered_active)
    confirmed_pool = checked_in + registered_active
    attendance_rate = round((checked_in / confirmed_pool * 100), 1) if confirmed_pool > 0 else 0.0
    cancellation_rate = round((cancelled / total_registrations * 100), 1) if total_registrations > 0 else 0.0

    # 4. Category Popularity Aggregation
    category_pipeline = [
        {"$match": {"status": {"$ne": "archived"}}},
        {"$group": {
            "_id": "$category",
            "event_count": {"$sum": 1},
            "total_registered": {"$sum": "$registered_count"}
        }},
        {"$sort": {"event_count": -1}}
    ]
    category_distribution = list(db.events.aggregate(category_pipeline))

    # 5. Venue Utilization Aggregation
    venue_util_pipeline = [
        {"$lookup": {
            "from": "events",
            "localField": "_id",
            "foreignField": "venue_id",
            "as": "events"
        }},
        {"$project": {
            "name": 1,
            "code": 1,
            "capacity": 1,
            "event_count": {"$size": "$events"},
            "total_booked_seats": {"$sum": "$events.registered_count"}
        }},
        {"$sort": {"event_count": -1}}
    ]
    venue_utilization = list(db.venues.aggregate(venue_util_pipeline))

    # 6. Recent Audit Logs
    recent_audits = list(db.audit_logs.find().sort("timestamp", -1).limit(10))

    return {
        "total_events": total_events,
        "active_events": active_events,
        "pending_events": pending_events,
        "archived_events": archived_events,
        "cancelled_events": cancelled_events,
        "user_counts": user_counts,
        "total_registrations": total_registrations,
        "checked_in_count": checked_in,
        "registered_active_count": registered_active,
        "waitlisted_count": waitlisted,
        "cancelled_count": cancelled,
        "attendance_rate": attendance_rate,
        "cancellation_rate": cancellation_rate,
        "category_distribution": category_distribution,
        "venue_utilization": venue_utilization,
        "recent_audits": recent_audits
    }


def get_organizer_dashboard_metrics(db, organizer_id):
    """
    Organizer specific event performance, feedback score, and attendance metrics.
    """
    org_oid = ObjectId(organizer_id)

    # 1. Organizer Events with attendee counts
    pipeline = [
        {"$match": {"organizer_id": org_oid}},
        {"$lookup": {
            "from": "venues",
            "localField": "venue_id",
            "foreignField": "_id",
            "as": "venue"
        }},
        {"$unwind": {"path": "$venue", "preserveNullAndEmptyArrays": True}},
        {"$sort": {"start_time": -1}}
    ]
    events = list(db.events.aggregate(pipeline))

    event_ids = [e["_id"] for e in events]

    # 2. Registration stats across organizer's events
    reg_pipeline = [
        {"$match": {"event_id": {"$in": event_ids}}},
        {"$group": {
            "_id": "$status",
            "count": {"$sum": 1}
        }}
    ]
    reg_agg = list(db.registrations.aggregate(reg_pipeline))
    reg_stats = {item["_id"]: item["count"] for item in reg_agg}

    total_reg = sum(reg_stats.values())
    checked_in = reg_stats.get("checked-in", 0)
    active = reg_stats.get("registered", 0)
    cancelled = reg_stats.get("cancelled", 0)
    waitlisted = reg_stats.get("waitlisted", 0)

    # 3. Feedback ratings and sentiment aggregation
    fb_pipeline = [
        {"$match": {"event_id": {"$in": event_ids}}},
        {"$group": {
            "_id": None,
            "avg_rating": {"$avg": "$rating"},
            "total_feedback": {"$sum": 1},
            "positive_count": {"$sum": {"$cond": [{"$eq": ["$sentiment_label", "Positive"]}, 1, 0]}},
            "neutral_count": {"$sum": {"$cond": [{"$eq": ["$sentiment_label", "Neutral"]}, 1, 0]}},
            "negative_count": {"$sum": {"$cond": [{"$eq": ["$sentiment_label", "Constructive/Negative"]}, 1, 0]}}
        }}
    ]
    fb_agg = list(db.feedback.aggregate(fb_pipeline))
    feedback_summary = fb_agg[0] if fb_agg else {
        "avg_rating": 0.0, "total_feedback": 0, "positive_count": 0, "neutral_count": 0, "negative_count": 0
    }
    if feedback_summary.get("avg_rating"):
        feedback_summary["avg_rating"] = round(feedback_summary["avg_rating"], 2)

    return {
        "events": events,
        "total_events": len(events),
        "total_registrations": total_reg,
        "checked_in_count": checked_in,
        "active_registrations": active,
        "cancelled_count": cancelled,
        "waitlisted_count": waitlisted,
        "feedback_summary": feedback_summary,
        # Promotion Effectiveness (Clearly labelled demo tracking metric)
        "demo_promotion_tracking": {
            "notice": "Simulated referral tracking for college evaluation",
            "channels": [
                {"source": "College Portal Direct", "percentage": 58},
                {"source": "Department Noticeboard", "percentage": 24},
                {"source": "Student WhatsApp Groups", "percentage": 18}
            ]
        }
    }


def get_student_dashboard_metrics(db, student_id):
    """
    Student dashboard data: registrations, history, and category recommendations.
    """
    st_oid = ObjectId(student_id)
    now = datetime.utcnow()

    # Registrations with event details
    registrations = list(db.registrations.aggregate([
        {"$match": {"student_id": st_oid}},
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
    ]))

    upcoming = []
    attended = []
    past = []
    registered_categories = set()

    for reg in registrations:
        ev = reg.get("event", {})
        registered_categories.add(ev.get("category", "General"))
        if reg.get("status") == "checked-in":
            attended.append(reg)
        elif reg.get("status") in ["registered", "waitlisted"] and ev.get("start_time", now) > now:
            upcoming.append(reg)
        else:
            past.append(reg)

    # Interest-based recommendations: Find published upcoming events matching student's past categories
    recommend_query = {
        "status": "published",
        "start_time": {"$gt": now},
        "category": {"$in": list(registered_categories) if registered_categories else ["Academic", "Workshop"]}
    }
    # Exclude already registered event IDs
    reg_event_ids = [reg["event_id"] for reg in registrations]
    if reg_event_ids:
        recommend_query["_id"] = {"$nin": reg_event_ids}

    recommended_events = list(db.events.find(recommend_query).sort("start_time", 1).limit(4))

    return {
        "upcoming": upcoming,
        "attended": attended,
        "past": past,
        "total_registered": len(registrations),
        "total_attended": len(attended),
        "recommended_events": recommended_events
    }


def export_event_attendees_csv(db, event_id):
    """
    Generate CSV string of event registrations and check-in statuses.
    """
    pipeline = [
        {"$match": {"event_id": ObjectId(event_id)}},
        {"$lookup": {
            "from": "users",
            "localField": "student_id",
            "foreignField": "_id",
            "as": "student"
        }},
        {"$unwind": "$student"},
        {"$sort": {"registered_at": 1}}
    ]
    records = list(db.registrations.aggregate(pipeline))

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Ticket Code", "Student Name", "Email", "Phone", "Status", "Registered At", "Check-in Time"])

    for r in records:
        student = r.get("student", {})
        check_in_str = r.get("check_in_time").strftime("%Y-%m-%d %H:%M:%S") if r.get("check_in_time") else "N/A"
        reg_time_str = r.get("registered_at").strftime("%Y-%m-%d %H:%M:%S") if r.get("registered_at") else "N/A"
        writer.writerow([
            r.get("ticket_code", ""),
            student.get("full_name", ""),
            student.get("email", ""),
            student.get("phone", ""),
            r.get("status", ""),
            reg_time_str,
            check_in_str
        ])

    return output.getvalue()


def export_admin_events_csv(db):
    """
    Generate CSV string of all events in system with metrics.
    """
    pipeline = [
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
        {"$sort": {"created_at": -1}}
    ]
    events = list(db.events.aggregate(pipeline))

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Event ID", "Title", "Category", "Status", "Venue", "Capacity", 
        "Registered", "Waitlisted", "Organizer Name", "Organizer Email", 
        "Start Time", "End Time", "Budget (INR)"
    ])

    for ev in events:
        venue = ev.get("venue", {})
        org = ev.get("organizer", {})
        writer.writerow([
            str(ev["_id"]),
            ev.get("title", ""),
            ev.get("category", ""),
            ev.get("status", ""),
            venue.get("name", "N/A"),
            ev.get("capacity", 0),
            ev.get("registered_count", 0),
            ev.get("waitlist_count", 0),
            org.get("full_name", "N/A"),
            org.get("email", "N/A"),
            ev.get("start_time", "").strftime("%Y-%m-%d %H:%M") if ev.get("start_time") else "",
            ev.get("end_time", "").strftime("%Y-%m-%d %H:%M") if ev.get("end_time") else "",
            ev.get("budget", {}).get("total", 0.0)
        ])

    return output.getvalue()
