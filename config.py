import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


class Config:
    """Base application configuration."""
    SECRET_KEY = os.getenv("SECRET_KEY", "college-events-adbms-default-secret-key-2026")
    MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/college_events_db")
    DATABASE_NAME = os.getenv("DATABASE_NAME", "college_events_db")
    
    # Uploads
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", 5 * 1024 * 1024))  # 5 MB
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads", "event_banners")
    ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
    
    # Business Logic Constants
    BUDGET_BREAKDOWN_THRESHOLD = float(os.getenv("BUDGET_BREAKDOWN_THRESHOLD", 10000.0))
    EMAIL_DELIVERY_MODE = os.getenv("EMAIL_DELIVERY_MODE", "local_demo")
    
    # Session Security
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = 86400  # 24 hours


class DevelopmentConfig(Config):
    DEBUG = True
    TESTING = False
    SESSION_COOKIE_SECURE = False


class TestingConfig(Config):
    DEBUG = True
    TESTING = True
    SESSION_COOKIE_SECURE = False
    MONGODB_URI = "mongomock://localhost/test_college_events"
    DATABASE_NAME = "test_college_events"


class ProductionConfig(Config):
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
