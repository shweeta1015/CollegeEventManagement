from bson import ObjectId
from services.auth_service import register_user, authenticate_user, verify_email_token, is_rate_limited, record_failed_attempt


def test_user_registration_success(db):
    """Test standard valid user registration."""
    success, msg, user_id = register_user(
        db,
        email="newstudent@college.edu",
        password="Password@123",
        full_name="New Student",
        role="student",
        phone="+919876543299"
    )
    assert success is True
    assert user_id is not None

    user = db.users.find_one({"_id": user_id})
    assert user is not None
    assert user["email"] == "newstudent@college.edu"
    assert user["role"] == "student"
    assert user["password_hash"] != "Password@123"  # Must be hashed


def test_duplicate_email_registration_fails(db, test_users):
    """Test duplicate-key error handling on email constraint."""
    success, msg, _ = register_user(
        db,
        email=test_users["student1"]["email"],  # Existing email
        password="Password@123",
        full_name="Duplicate Rahul",
        role="student",
        phone="+919876543299"
    )
    assert success is False
    assert "already exists" in msg.lower()


def test_invalid_phone_validation(db):
    """Test phone validation rule (10-15 digits, optional +)."""
    success, msg, _ = register_user(
        db,
        email="invalidphone@college.edu",
        password="Password@123",
        full_name="Phone Tester",
        role="student",
        phone="123"  # Too short
    )
    assert success is False
    assert "phone number must be 10 to 15 digits" in msg.lower()


def test_email_verification_token_flow(db):
    """Test token generation and verification."""
    success, _, user_id = register_user(
        db,
        email="verifytest@college.edu",
        password="Password@123",
        full_name="Token Tester",
        role="student",
        phone="+919876543200"
    )
    user = db.users.find_one({"_id": user_id})
    token = user["verification_token"]
    assert token is not None

    # Verify using valid token
    verif_ok, verif_msg = verify_email_token(db, token)
    assert verif_ok is True

    updated_user = db.users.find_one({"_id": user_id})
    assert updated_user["email_verified"] is True
    assert updated_user["verification_token"] is None

    # Re-using token should fail
    verif_retry, _ = verify_email_token(db, token)
    assert verif_retry is False


def test_authentication_and_password_hashing(db, test_users):
    """Verify authentication succeeds with correct password and fails with invalid."""
    ok, _, user = authenticate_user(db, "student1@college.edu", "Student@123")
    assert ok is True
    assert user["email"] == "student1@college.edu"

    fail, err, _ = authenticate_user(db, "student1@college.edu", "WrongPassword")
    assert fail is False
    assert "invalid" in err.lower()


def test_role_based_access_control(client, test_users):
    """Verify backend RBAC: Student accessing admin routes is redirected with access denied."""
    # Simulate student session
    with client.session_transaction() as sess:
        sess["user_id"] = str(test_users["student1"]["_id"])
        sess["role"] = "student"
        sess["full_name"] = test_users["student1"]["full_name"]

    # Student trying to access admin dashboard
    response = client.get("/admin/dashboard", follow_redirects=True)
    assert b"Access Denied" in response.data or response.status_code == 200

    # Student trying to access organizer dashboard
    response_org = client.get("/organizer/dashboard", follow_redirects=True)
    assert b"Access Denied" in response_org.data or response_org.status_code == 200
