"""
System Verification Script
Tests end-to-end integration across all views, database seeder, and roles.
"""
from app import create_app
from seed_data import seed_database

def verify_system():
    print("==================================================================")
    print("STARTING FULL END-TO-END SYSTEM INTEGRATION VERIFICATION")
    print("==================================================================")

    app = create_app("development")
    client = app.test_client()
    db = app.config["DB"]

    # 1. Seed database
    print("\n[Step 1] Running database seeder...")
    seed_database(db)

    # 2. Verify Public Pages
    print("\n[Step 2] Testing public pages...")
    res = client.get("/")
    assert res.status_code == 200, f"Landing page failed: {res.status_code}"
    assert b"Official Campus Events Portal" in res.data
    print("  [OK] Landing page (/) OK")

    res = client.get("/events")
    assert res.status_code == 200
    assert b"Campus Events Catalog" in res.data
    print("  [OK] Events Catalog (/events) OK")

    res = client.get("/about")
    assert res.status_code == 200
    assert b"ADBMS Architecture" in res.data
    print("  [OK] About ADBMS page (/about) OK")

    # 3. Test Student Login & Dashboard
    print("\n[Step 3] Testing Student session & dashboard...")
    res = client.post("/login", data={"email": "student1@college.edu", "password": "Student@123"}, follow_redirects=True)
    assert res.status_code == 200
    assert b"Welcome back, Rahul Sharma" in res.data or b"Student Dashboard" in res.data
    print("  [OK] Student login OK")

    res = client.get("/student/dashboard")
    assert res.status_code == 200
    assert b"My Upcoming Event Tickets" in res.data
    print("  [OK] Student Dashboard OK")

    # 4. Test Organizer Login & Dashboard
    print("\n[Step 4] Testing Organizer session & dashboard...")
    client.get("/logout")
    res = client.post("/login", data={"email": "organizer1@college.edu", "password": "Organizer@123"}, follow_redirects=True)
    assert res.status_code == 200

    res = client.get("/organizer/dashboard")
    assert res.status_code == 200
    assert b"Organizer Console" in res.data
    assert b"My Organized Events" in res.data
    print("  [OK] Organizer Dashboard OK")

    # 5. Test Admin Login & Dashboard
    print("\n[Step 5] Testing Admin session & dashboards...")
    client.get("/logout")
    res = client.post("/login", data={"email": "admin@college.edu", "password": "Admin@123"}, follow_redirects=True)
    assert res.status_code == 200

    res = client.get("/admin/dashboard")
    assert res.status_code == 200
    assert b"Administrator Control Center" in res.data
    print("  [OK] Admin Dashboard OK")

    res = client.get("/admin/events")
    assert res.status_code == 200
    assert b"Campus Events Oversight" in res.data
    print("  [OK] Admin Events Oversight OK")

    res = client.get("/admin/venues")
    assert res.status_code == 200
    assert b"Campus Venues Management" in res.data
    print("  [OK] Admin Venues Management OK")

    res = client.get("/admin/reports")
    assert res.status_code == 200
    assert b"System Analytics & Aggregation Reports" in res.data
    print("  [OK] Admin Reports & Aggregations OK")

    res = client.get("/admin/audit-logs")
    assert res.status_code == 200
    assert b"Security Audit Trail" in res.data
    print("  [OK] Admin Audit Logs OK")

    # 6. Test JSON API endpoints
    print("\n[Step 6] Testing API endpoints...")
    res = client.get("/api/reports/charts-data")
    assert res.status_code == 200
    data = res.get_json()
    assert "categories" in data
    assert "registration_status" in data
    assert "venues" in data
    print("  [OK] /api/reports/charts-data OK")

    res = client.get("/api/export/admin/events.csv")
    assert res.status_code == 200
    assert b"Event ID,Title,Category" in res.data
    print("  [OK] /api/export/admin/events.csv OK")

    print("\n==================================================================")
    print("ALL INTEGRATION CHECKS PASSED SUCCESSFULLY (100% WORKING)!")
    print("==================================================================")


if __name__ == "__main__":
    verify_system()
