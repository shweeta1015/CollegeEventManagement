import logging
from datetime import datetime
from bson import ObjectId
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

logger = logging.getLogger(__name__)

# Global client and db references
_client = None
_db = None
_is_mock = False


def get_db(uri="mongodb://localhost:27017/college_events_db", db_name="college_events_db", force_mock=False):
    """
    Connect to MongoDB. If connection fails or force_mock is True,
    gracefully fallback to high-fidelity mongomock instance.
    """
    global _client, _db, _is_mock
    
    if _db is not None and not force_mock:
        return _db
    
    if force_mock or (uri and uri.startswith("mongomock://")):
        try:
            import mongomock
            _client = mongomock.MongoClient()
            _db = _client[db_name]
            _is_mock = True
            logger.info(f"[Database] Initialized mongomock database: {db_name}")
            return _db
        except Exception as e:
            logger.error(f"[Database] Failed to init mongomock: {e}")
            raise
    
    # Try real MongoDB connection
    try:
        real_client = MongoClient(uri, serverSelectionTimeoutMS=2000)
        # Verify connection with admin ping command
        real_client.admin.command("ping")
        _client = real_client
        _db = _client[db_name]
        _is_mock = False
        logger.info(f"[Database] Connected successfully to MongoDB at: {uri} (Database: {db_name})")
        return _db
    except (ConnectionFailure, ServerSelectionTimeoutError, Exception) as err:
        logger.warning(
            f"[Database] Could not connect to real MongoDB ({err}). "
            f"Falling back to high-fidelity in-memory MongoDB engine (mongomock)."
        )
        import mongomock
        _client = mongomock.MongoClient()
        _db = _client[db_name]
        _is_mock = True
        logger.info(f"[Database] Initialized fallback mongomock database: {db_name}")
        return _db


def is_mock_db():
    """Check if current database is running under mongomock."""
    global _is_mock
    return _is_mock


def init_indexes(db):
    """
    Define and enforce primary, unique, and compound indexes across MongoDB collections.
    Demonstrates core ADBMS index design concepts.
    """
    try:
        # 1. Users collection
        db.users.create_index([("email", ASCENDING)], unique=True, name="idx_users_email_unique")
        db.users.create_index([("role", ASCENDING)], name="idx_users_role")
        
        # 2. Venues collection
        db.venues.create_index([("name", ASCENDING)], unique=True, name="idx_venues_name_unique")
        db.venues.create_index([("code", ASCENDING)], unique=True, name="idx_venues_code_unique")
        
        # 3. Events collection
        # Compound index for organizer query and date sorting
        db.events.create_index([("organizer_id", ASCENDING), ("start_time", ASCENDING)], name="idx_events_org_start")
        # Query optimization indexes
        db.events.create_index([("status", ASCENDING), ("start_time", ASCENDING)], name="idx_events_status_start")
        db.events.create_index([("category", ASCENDING)], name="idx_events_category")
        
        # 4. Registrations collection
        # Unique ticket verification code
        db.registrations.create_index([("ticket_code", ASCENDING)], unique=True, name="idx_reg_ticket_code_unique")
        # Compound index for event and student lookups
        db.registrations.create_index(
            [("event_id", ASCENDING), ("student_id", ASCENDING)], 
            name="idx_reg_event_student"
        )
        db.registrations.create_index([("status", ASCENDING)], name="idx_reg_status")
        
        # 5. Feedback collection
        # A student can submit at most one feedback per attended event
        db.feedback.create_index(
            [("event_id", ASCENDING), ("student_id", ASCENDING)], 
            unique=True, 
            name="idx_feedback_event_student_unique"
        )
        
        # 6. Notifications collection
        db.notifications.create_index(
            [("user_id", ASCENDING), ("created_at", DESCENDING)], 
            name="idx_notif_user_time"
        )
        
        # 7. Audit logs collection
        db.audit_logs.create_index([("timestamp", DESCENDING)], name="idx_audit_timestamp")
        db.audit_logs.create_index([("actor_id", ASCENDING)], name="idx_audit_actor")
        
        # 8. Organizer verifications collection
        db.organizer_verifications.create_index([("user_id", ASCENDING)], unique=True, name="idx_org_verif_user_unique")
        
        logger.info("[Database] All MongoDB indexes verified and created successfully.")
    except Exception as e:
        logger.warning(f"[Database] Note during index creation: {e}")


def create_audit_log(db, actor_id, actor_role, action, target_collection, target_id=None, details=None, ip_address=None):
    """Record administrative or organizer operations for accountability and audit compliance."""
    log_doc = {
        "actor_id": ObjectId(actor_id) if actor_id and isinstance(actor_id, (str, ObjectId)) else None,
        "actor_role": actor_role or "system",
        "action": action,
        "target_collection": target_collection,
        "target_id": ObjectId(target_id) if target_id and isinstance(target_id, (str, ObjectId)) else target_id,
        "details": details or {},
        "ip_address": ip_address or "127.0.0.1",
        "timestamp": datetime.utcnow()
    }
    return db.audit_logs.insert_one(log_doc)
