import uuid
import logging
from datetime import datetime, timedelta
from bson import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
from pymongo.errors import DuplicateKeyError

from models.validators import validate_email, validate_phone, VALID_ROLES
from database import create_audit_log

logger = logging.getLogger(__name__)

# In-memory sliding window for login rate limiting: { ip_or_email: [timestamps] }
_login_attempts = {}
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_WINDOW_MINUTES = 5


def is_rate_limited(identifier):
    """Check if identifier (IP or email) exceeded maximum failed login attempts within window."""
    now = datetime.utcnow()
    attempts = _login_attempts.get(identifier, [])
    # Filter attempts within the window
    recent = [t for t in attempts if (now - t) < timedelta(minutes=LOCKOUT_WINDOW_MINUTES)]
    _login_attempts[identifier] = recent
    return len(recent) >= MAX_LOGIN_ATTEMPTS


def record_failed_attempt(identifier):
    """Record a failed login attempt."""
    now = datetime.utcnow()
    attempts = _login_attempts.get(identifier, [])
    attempts.append(now)
    _login_attempts[identifier] = attempts


def reset_failed_attempts(identifier):
    """Clear failed login attempts upon successful login."""
    if identifier in _login_attempts:
        del _login_attempts[identifier]


def register_user(db, email, password, full_name, role="student", phone="", ip_address="127.0.0.1", reg_no="", department=""):
    """
    Register a new user:
    - Validate inputs
    - Hash password using Werkzeug scrypt/pbkdf2
    - Enforce unique email constraint (handling duplicate key error)
    - Generate email verification token (for local demo)
    - If role is 'organizer', initialize organizer_verifications document
    - Audit log user registration
    """
    valid_email, clean_email_or_err = validate_email(email)
    if not valid_email:
        return False, clean_email_or_err, None

    clean_email = clean_email_or_err
    
    if not password or len(password) < 6:
        return False, "Password must be at least 6 characters long.", None

    if not full_name or len(full_name.strip()) < 2:
        return False, "Full name must be at least 2 characters.", None

    if role not in VALID_ROLES:
        return False, f"Invalid role specified. Must be one of: {', '.join(VALID_ROLES)}", None

    valid_ph, clean_phone = validate_phone(phone)
    if not valid_ph:
        return False, clean_phone, None

    # Check for existing email before insert
    existing = db.users.find_one({"email": clean_email})
    if existing:
        return False, "An account with this email address already exists.", None

    token = f"VERIF-{uuid.uuid4().hex[:16]}"
    password_hash = generate_password_hash(password)

    user_doc = {
        "email": clean_email,
        "password_hash": password_hash,
        "full_name": full_name.strip(),
        "role": role,
        "phone": clean_phone,
        "is_active": True,
        "email_verified": False,
        "verification_token": token,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }

    try:
        result = db.users.insert_one(user_doc)
        user_id = result.inserted_id

        # If registering as organizer, create verification record
        if role == "organizer":
            db.organizer_verifications.insert_one({
                "user_id": user_id,
                "college_reg_no": reg_no.strip() if reg_no else "PENDING",
                "department": department.strip() if department else "General",
                "faculty_advisor": "",
                "status": "pending",
                "admin_notes": "Awaiting initial administrative review.",
                "reviewed_by": None,
                "reviewed_at": None,
                "created_at": datetime.utcnow()
            })

        # Add welcome notification
        db.notifications.insert_one({
            "user_id": user_id,
            "title": "Welcome to College Event Portal!",
            "message": f"Welcome {full_name.strip()}! Please verify your email using token: {token}",
            "type": "registration",
            "is_read": False,
            "is_archived": False,
            "created_at": datetime.utcnow()
        })

        create_audit_log(
            db, 
            actor_id=user_id, 
            actor_role=role, 
            action="USER_REGISTERED", 
            target_collection="users", 
            target_id=user_id, 
            details={"email": clean_email, "role": role},
            ip_address=ip_address
        )

        return True, "Registration successful.", user_id
    except DuplicateKeyError:
        return False, "An account with this email address already exists.", None
    except Exception as e:
        logger.error(f"Error during user registration: {e}")
        return False, f"Registration failed: {str(e)}", None


def authenticate_user(db, email, password, ip_address="127.0.0.1"):
    """
    Authenticate user with credentials and rate-limiting.
    """
    clean_email = email.strip().lower() if email else ""
    rate_key = f"{ip_address}:{clean_email}"

    if is_rate_limited(rate_key):
        return False, f"Too many failed login attempts. Please try again after {LOCKOUT_WINDOW_MINUTES} minutes.", None

    user = db.users.find_one({"email": clean_email})
    if not user:
        record_failed_attempt(rate_key)
        return False, "Invalid email or password.", None

    if not user.get("is_active", True):
        return False, "This account has been deactivated. Please contact the administrator.", None

    if not check_password_hash(user.get("password_hash", ""), password):
        record_failed_attempt(rate_key)
        return False, "Invalid email or password.", None

    # Reset attempts on success
    reset_failed_attempts(rate_key)
    
    # Audit log
    create_audit_log(
        db,
        actor_id=user["_id"],
        actor_role=user.get("role", "student"),
        action="USER_LOGIN",
        target_collection="users",
        target_id=user["_id"],
        ip_address=ip_address
    )

    return True, "Login successful.", user


def verify_email_token(db, token):
    """Verify user's email using token."""
    if not token:
        return False, "Verification token is required."
    
    user = db.users.find_one({"verification_token": token.strip()})
    if not user:
        return False, "Invalid or expired verification token."

    db.users.update_one(
        {"_id": user["_id"]},
        {"$set": {"email_verified": True, "verification_token": None, "updated_at": datetime.utcnow()}}
    )
    return True, "Email verified successfully."


def deactivate_user_account(db, user_id, actor_id, actor_role):
    """Soft-deactivate user account instead of hard deletion."""
    user = db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        return False, "User not found."

    db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"is_active": False, "updated_at": datetime.utcnow()}}
    )

    create_audit_log(
        db,
        actor_id=actor_id,
        actor_role=actor_role,
        action="DEACTIVATE_USER",
        target_collection="users",
        target_id=user_id,
        details={"deactivated_email": user.get("email")}
    )
    return True, "User account deactivated."
