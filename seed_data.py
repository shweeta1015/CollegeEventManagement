import os
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash
from bson import ObjectId

from config import Config
from database import get_db, init_indexes

def seed_database(db=None):
    """
    Populate database with clean, realistic demonstration data for college evaluation.
    """
    if db is None:
        db = get_db(Config.MONGODB_URI, Config.DATABASE_NAME)
        
    print("[Seed] Initializing indexes...")
    init_indexes(db)

    print("[Seed] Clearing existing demonstration collections...")
    for col in ["users", "venues", "events", "registrations", "feedback", "notifications", "organizer_verifications", "audit_logs", "platform_suggestions"]:
        db[col].delete_many({})

    # 1. Seed Users
    print("[Seed] Creating users (Admin, Organizers, Students)...")
    admin_id = ObjectId()
    org1_id = ObjectId()
    org2_id = ObjectId()
    student1_id = ObjectId()
    student2_id = ObjectId()
    student3_id = ObjectId()

    now = datetime.utcnow()

    users = [
        {
            "_id": admin_id,
            "email": "admin@college.edu",
            "password_hash": generate_password_hash("Admin@123"),
            "full_name": "Dr. Sarah Mitchell (Dean & Admin)",
            "role": "admin",
            "phone": "+919876543210",
            "is_active": True,
            "email_verified": True,
            "verification_token": None,
            "created_at": now - timedelta(days=60),
            "updated_at": now - timedelta(days=60)
        },
        {
            "_id": org1_id,
            "email": "organizer1@college.edu",
            "password_hash": generate_password_hash("Organizer@123"),
            "full_name": "Prof. Alan Vance (ACM Club Lead)",
            "role": "organizer",
            "phone": "+919876543211",
            "is_active": True,
            "email_verified": True,
            "verification_token": None,
            "created_at": now - timedelta(days=45),
            "updated_at": now - timedelta(days=45)
        },
        {
            "_id": org2_id,
            "email": "organizer2@college.edu",
            "password_hash": generate_password_hash("Organizer@123"),
            "full_name": "Elena Rostova (Music Society Lead)",
            "role": "organizer",
            "phone": "+919876543212",
            "is_active": True,
            "email_verified": True,
            "verification_token": None,
            "created_at": now - timedelta(days=10),
            "updated_at": now - timedelta(days=10)
        },
        {
            "_id": student1_id,
            "email": "student1@college.edu",
            "password_hash": generate_password_hash("Student@123"),
            "full_name": "Rahul Sharma",
            "role": "student",
            "phone": "+919876543221",
            "is_active": True,
            "email_verified": True,
            "verification_token": None,
            "created_at": now - timedelta(days=30),
            "updated_at": now - timedelta(days=30)
        },
        {
            "_id": student2_id,
            "email": "student2@college.edu",
            "password_hash": generate_password_hash("Student@123"),
            "full_name": "Priya Nair",
            "role": "student",
            "phone": "+919876543222",
            "is_active": True,
            "email_verified": True,
            "verification_token": None,
            "created_at": now - timedelta(days=25),
            "updated_at": now - timedelta(days=25)
        },
        {
            "_id": student3_id,
            "email": "student3@college.edu",
            "password_hash": generate_password_hash("Student@123"),
            "full_name": "Dev Patel",
            "role": "student",
            "phone": "+919876543223",
            "is_active": True,
            "email_verified": True,
            "verification_token": None,
            "created_at": now - timedelta(days=20),
            "updated_at": now - timedelta(days=20)
        }
    ]
    db.users.insert_many(users)

    # 2. Organizer Verifications
    db.organizer_verifications.insert_many([
        {
            "user_id": org1_id,
            "college_reg_no": "FAC-CS-2022-09",
            "department": "Computer Science & Engineering",
            "faculty_advisor": "Dr. Sarah Mitchell",
            "status": "verified",
            "admin_notes": "Official faculty advisor for ACM Student Chapter. Verified and approved.",
            "reviewed_by": admin_id,
            "reviewed_at": now - timedelta(days=40),
            "created_at": now - timedelta(days=45)
        },
        {
            "user_id": org2_id,
            "college_reg_no": "STU-MUS-2024-41",
            "department": "Department of Fine Arts & Humanities",
            "faculty_advisor": "Prof. Marcus Thorne",
            "status": "pending",
            "admin_notes": "Application received. Pending faculty confirmation letter.",
            "reviewed_by": None,
            "reviewed_at": None,
            "created_at": now - timedelta(days=10)
        }
    ])

    # 3. Seed Venues
    print("[Seed] Creating venues...")
    venue1_id = ObjectId()
    venue2_id = ObjectId()
    venue3_id = ObjectId()

    venues = [
        {
            "_id": venue1_id,
            "name": "Sir C.V. Raman Grand Auditorium",
            "code": "AUD-01",
            "capacity": 350,
            "facilities": ["Dolby Surround Audio", "Laser Projector", "Central AC", "Stage Lighting", "VIP Lounge"],
            "is_active": True,
            "created_at": now - timedelta(days=50),
            "updated_at": now - timedelta(days=50)
        },
        {
            "_id": venue2_id,
            "name": "Advanced Computing & AI Lab Seminar Hall",
            "code": "CS-101",
            "capacity": 60,
            "facilities": ["Gigabit LAN & WiFi", "Interactive Smartboard", "Dual Display Monitors", "Audio Mic"],
            "is_active": True,
            "created_at": now - timedelta(days=50),
            "updated_at": now - timedelta(days=50)
        },
        {
            "_id": venue3_id,
            "name": "Green Open-Air Amphitheatre",
            "code": "AMP-01",
            "capacity": 500,
            "facilities": ["Acoustic Shell", "Floodlights", "Open Lawn Seating", "Power Backups"],
            "is_active": True,
            "created_at": now - timedelta(days=50),
            "updated_at": now - timedelta(days=50)
        }
    ]
    db.venues.insert_many(venues)

    # 4. Seed Events
    print("[Seed] Creating events (Upcoming, Past, Academic, Cultural)...")
    event1_id = ObjectId()  # Upcoming AI Workshop
    event2_id = ObjectId()  # Upcoming Cultural Night
    event3_id = ObjectId()  # Past Seminar (for feedback demo)

    events = [
        {
            "_id": event1_id,
            "title": "National Hackathon 2026: GenAI & Distributed NoSQL Systems",
            "organizer_id": org1_id,
            "venue_id": venue2_id,
            "description": "Join the premier 24-hour collegiate hackathon exploring cutting-edge generative AI models and MongoDB distributed architectures. Teams will build production-grade web applications, participate in mentor sprints, and present before industry judges.",
            "category": "Workshop",
            "start_time": now + timedelta(days=7, hours=10),
            "end_time": now + timedelta(days=7, hours=16),
            "capacity": 50,
            "registered_count": 2,
            "waitlist_count": 0,
            "status": "published",
            "banner_image": "",
            "budget": {
                "total": 25000.0,
                "breakdown": [
                    {"item": "Winner Prizes & Mementos: ₹15,000"},
                    {"item": "Snacks & Refreshments: ₹7,000"},
                    {"item": "Certificates & Badges: ₹3,000"}
                ],
                "approved": True
            },
            "created_at": now - timedelta(days=5),
            "updated_at": now - timedelta(days=5)
        },
        {
            "_id": event2_id,
            "title": "Annual Inter-Collegiate Cultural Carnival & Music Fest",
            "organizer_id": org1_id,
            "venue_id": venue1_id,
            "description": "The flagship cultural evening featuring live bands, dramatic arts, dance battles, and culinary stalls. Open to all students, alumni, and university faculty across disciplines.",
            "category": "Cultural",
            "start_time": now + timedelta(days=14, hours=17),
            "end_time": now + timedelta(days=14, hours=22),
            "capacity": 300,
            "registered_count": 1,
            "waitlist_count": 0,
            "status": "published",
            "banner_image": "",
            "budget": {
                "total": 45000.0,
                "breakdown": [
                    {"item": "Stage & Audio Rental: ₹25,000"},
                    {"item": "Guest Artists: ₹15,000"},
                    {"item": "Decorations & Safety: ₹5,000"}
                ],
                "approved": True
            },
            "created_at": now - timedelta(days=4),
            "updated_at": now - timedelta(days=4)
        },
        {
            "_id": event3_id,
            "title": "ADBMS Industry Seminar: Indexing Strategies in MongoDB",
            "organizer_id": org1_id,
            "venue_id": venue2_id,
            "description": "An in-depth technical seminar covering B-tree indexes, compound indexes, explain plans, and query execution optimization in modern MongoDB production clusters.",
            "category": "Academic",
            "start_time": now - timedelta(days=3, hours=10),
            "end_time": now - timedelta(days=3, hours=13),
            "capacity": 60,
            "registered_count": 3,
            "waitlist_count": 0,
            "status": "completed",
            "banner_image": "",
            "budget": {
                "total": 5000.0,
                "breakdown": [],
                "approved": True
            },
            "created_at": now - timedelta(days=20),
            "updated_at": now - timedelta(days=2)
        }
    ]
    db.events.insert_many(events)

    # 5. Seed Registrations
    print("[Seed] Creating sample registrations & QR tickets...")
    reg1_id = ObjectId()
    reg2_id = ObjectId()
    reg3_id = ObjectId()
    reg4_id = ObjectId()

    registrations = [
        # Student 1 registered for upcoming Hackathon
        {
            "_id": reg1_id,
            "event_id": event1_id,
            "student_id": student1_id,
            "ticket_code": "TKT-HACK2026-001",
            "status": "registered",
            "registered_at": now - timedelta(days=3),
            "check_in_time": None,
            "check_in_by": None,
            "created_at": now - timedelta(days=3),
            "updated_at": now - timedelta(days=3)
        },
        # Student 2 registered for upcoming Hackathon
        {
            "_id": reg2_id,
            "event_id": event1_id,
            "student_id": student2_id,
            "ticket_code": "TKT-HACK2026-002",
            "status": "registered",
            "registered_at": now - timedelta(days=2),
            "check_in_time": None,
            "check_in_by": None,
            "created_at": now - timedelta(days=2),
            "updated_at": now - timedelta(days=2)
        },
        # Student 1 registered for upcoming Cultural Fest
        {
            "_id": reg3_id,
            "event_id": event2_id,
            "student_id": student1_id,
            "ticket_code": "TKT-CULT2026-001",
            "status": "registered",
            "registered_at": now - timedelta(days=1),
            "check_in_time": None,
            "check_in_by": None,
            "created_at": now - timedelta(days=1),
            "updated_at": now - timedelta(days=1)
        },
        # Student 1 checked-in for Past Seminar (eligible for feedback!)
        {
            "_id": reg4_id,
            "event_id": event3_id,
            "student_id": student1_id,
            "ticket_code": "TKT-ADBMS2026-001",
            "status": "checked-in",
            "registered_at": now - timedelta(days=10),
            "check_in_time": now - timedelta(days=3, hours=9, minutes=45),
            "check_in_by": org1_id,
            "created_at": now - timedelta(days=10),
            "updated_at": now - timedelta(days=3)
        }
    ]
    db.registrations.insert_many(registrations)

    # 6. Seed Sample Feedback & Sentiment
    print("[Seed] Creating feedback...")
    db.feedback.insert_one({
        "event_id": event3_id,
        "student_id": student1_id,
        "rating": 5,
        "comment": "The explanation of compound indexes and aggregation pipelines was fantastic and extremely clear! Really loved the interactive query demo.",
        "sentiment_label": "Positive",
        "sentiment_score": 0.9,
        "sentiment_keywords": {
            "positive": ["fantastic", "clear", "loved"],
            "negative": []
        },
        "organizer_response": {
            "text": "Thank you Rahul! Delighted to hear you enjoyed the aggregation exercises.",
            "responded_by": org1_id,
            "responded_at": now - timedelta(days=2)
        },
        "created_at": now - timedelta(days=2, hours=18),
        "updated_at": now - timedelta(days=2)
    })

    # 7. Seed Notifications
    print("[Seed] Creating sample notifications...")
    notifications = [
        {
            "user_id": student1_id,
            "title": "Registration Confirmed!",
            "message": "Your registration for 'National Hackathon 2026' has been confirmed. Ticket code: TKT-HACK2026-001.",
            "type": "registration",
            "is_read": False,
            "is_archived": False,
            "created_at": now - timedelta(days=3)
        },
        {
            "user_id": student1_id,
            "title": "Welcome to College Events",
            "message": "Welcome Rahul Sharma to the College Event Portal!",
            "type": "registration",
            "is_read": True,
            "is_archived": False,
            "created_at": now - timedelta(days=30)
        }
    ]
    db.notifications.insert_many(notifications)

    # 8. Seed Audit Logs
    print("[Seed] Creating audit logs...")
    db.audit_logs.insert_many([
        {
            "actor_id": admin_id,
            "actor_role": "admin",
            "action": "SYSTEM_SEED_INITIALIZED",
            "target_collection": "system",
            "target_id": None,
            "details": {"environment": "ADBMS_Project_Demo"},
            "ip_address": "127.0.0.1",
            "timestamp": now
        }
    ])

    print("\n[Seed] ==================================================================")
    print("[Seed] Database successfully populated with realistic demonstration data!")
    print("[Seed] ==================================================================")
    print("[Seed] DEMO USER CREDENTIALS:")
    print("[Seed] 1. Admin:      admin@college.edu      / Admin@123")
    print("[Seed] 2. Organizer:  organizer1@college.edu  / Organizer@123 (Verified ACM Lead)")
    print("[Seed] 3. Organizer:  organizer2@college.edu  / Organizer@123 (Pending Verification)")
    print("[Seed] 4. Student:    student1@college.edu    / Student@123 (Has QR Ticket & Attended Event)")
    print("[Seed] 5. Student:    student2@college.edu    / Student@123")
    print("[Seed] ==================================================================\n")


if __name__ == "__main__":
    seed_database()
