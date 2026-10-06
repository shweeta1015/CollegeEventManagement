from flask import Blueprint, request, jsonify, session, current_app, Response
from bson import ObjectId

from routes.decorators import api_role_required
from services.registration_service import check_in_attendee
from services.report_service import export_event_attendees_csv, export_admin_events_csv, get_admin_dashboard_metrics

api_bp = Blueprint("api", __name__, url_prefix="/api")


@api_bp.route("/checkin", methods=["POST"])
@api_role_required("organizer", "admin")
def api_checkin():
    """
    Asynchronous JSON check-in endpoint for QR code scanner and mobile terminals.
    """
    db = current_app.config["DB"]
    actor_id = session.get("user_id")
    actor_role = session.get("role")

    data = request.get_json(silent=True) or request.form
    ticket_code = data.get("ticket_code", "").strip()

    if not ticket_code:
        return jsonify({"success": False, "message": "Ticket code is required."}), 400

    success, message, result = check_in_attendee(db, ticket_code, actor_id, actor_role)
    if success:
        return jsonify({"success": True, "message": message, "data": result}), 200
    else:
        return jsonify({"success": False, "message": message}), 400


@api_bp.route("/export/event/<event_id>/attendees.csv")
@api_role_required("organizer", "admin")
def export_event_csv(event_id):
    """Download event attendee roster in CSV format."""
    db = current_app.config["DB"]
    csv_data = export_event_attendees_csv(db, event_id)

    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename=attendees_{event_id}.csv"}
    )


@api_bp.route("/export/admin/events.csv")
@api_role_required("admin")
def export_admin_csv():
    """Download system-wide event statistics in CSV format."""
    db = current_app.config["DB"]
    csv_data = export_admin_events_csv(db)

    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=college_events_summary.csv"}
    )


@api_bp.route("/reports/charts-data")
@api_role_required("admin")
def get_charts_data():
    """Provides structured data for Chart.js administrative dashboard."""
    db = current_app.config["DB"]
    metrics = get_admin_dashboard_metrics(db)

    categories = [item["_id"] for item in metrics["category_distribution"]]
    category_counts = [item["event_count"] for item in metrics["category_distribution"]]

    venues = [item["name"] for item in metrics["venue_utilization"]]
    venue_counts = [item["event_count"] for item in metrics["venue_utilization"]]

    return jsonify({
        "categories": {"labels": categories, "data": category_counts},
        "venues": {"labels": venues, "data": venue_counts},
        "registration_status": {
            "labels": ["Checked-In", "Active Registered", "Waitlisted", "Cancelled"],
            "data": [
                metrics["checked_in_count"],
                metrics["registered_active_count"],
                metrics["waitlisted_count"],
                metrics["cancelled_count"]
            ]
        }
    })
