import pytest
from datetime import datetime, timedelta
from bson import ObjectId
from werkzeug.security import generate_password_hash

from app import create_app
from database import get_db, init_indexes


@pytest.fixture(scope="session")
def app():
    """Create Flask application configured for testing."""
    test_app = create_app("testing")
    return test_app


@pytest.fixture(scope="function")
def db(app):
    """Provide a clean in-memory database for each test function."""
    database = get_db(uri="mongomock://localhost/test_db", db_name="test_db", force_mock=True)
    # Clear collections
    for col in ["users", "venues", "events", "registrations", "feedback", "notifications", "organizer_verifications", "audit_logs", "platform_suggestions"]:
        database[col].delete_many({})
    init_indexes(database)
    app.config["DB"] = database
    return database


@pytest.fixture
def client(app, db):
    """Flask test client."""
    return app.test_client()


@pytest.fixture
def test_users(db):
    """Seed test users (admin, verified organizer, unverified organizer, students)."""
    now = datetime.utcnow()
    
    admin_id = ObjectId()
    org1_id = ObjectId()
    org2_id = ObjectId()
    student1_id = ObjectId()
    student2_id = ObjectId()

    users = [
        {
            "_id": admin_id,
            "email": "admin@college.edu",
            "password_hash": generate_password_hash("Admin@123"),
            "full_name": "Dean Admin",
            "role": "admin",
            "phone": "+919876543210",
            "is_active": True,
            "email_verified": True,
            "created_at": now
        },
        {
            "_id": org1_id,
            "email": "org1@college.edu",
            "password_hash": generate_password_hash("Organizer@123"),
            "full_name": "Prof Verified",
            "role": "organizer",
            "phone": "+919876543211",
            "is_active": True,
            "email_verified": True,
            "created_at": now
        },
        {
            "_id": org2_id,
            "email": "org2@college.edu",
            "password_hash": generate_password_hash("Organizer@123"),
            "full_name": "Unverified Organizer",
            "role": "organizer",
            "phone": "+919876543212",
            "is_active": True,
            "email_verified": True,
            "created_at": now
        },
        {
            "_id": student1_id,
            "email": "student1@college.edu",
            "password_hash": generate_password_hash("Student@123"),
            "full_name": "Student One",
            "role": "student",
            "phone": "+919876543221",
            "is_active": True,
            "email_verified": True,
            "created_at": now
        },
        {
            "_id": student2_id,
            "email": "student2@college.edu",
            "password_hash": generate_password_hash("Student@123"),
            "full_name": "Student Two",
            "role": "student",
            "phone": "+919876543222",
            "is_active": True,
            "email_verified": True,
            "created_at": now
        }
    ]
    db.users.insert_many(users)

    # Verifications
    db.organizer_verifications.insert_many([
        {
            "user_id": org1_id,
            "college_reg_no": "FAC-01",
            "department": "CSE",
            "status": "verified"
        },
        {
            "user_id": org2_id,
            "college_reg_no": "FAC-02",
            "department": "ECE",
            "status": "pending"
        }
    ])

    return {
        "admin": users[0],
        "org_verified": users[1],
        "org_unverified": users[2],
        "student1": users[3],
        "student2": users[4]
    }


@pytest.fixture
def test_venue(db):
    """Seed test venue."""
    venue_id = ObjectId()
    doc = {
        "_id": venue_id,
        "name": "Computing Seminar Hall",
        "code": "CS-101",
        "capacity": 50,
        "facilities": ["Projector", "AC"],
        "is_active": True,
        "created_at": datetime.utcnow()
    }
    db.venues.insert_one(doc)
    return doc
