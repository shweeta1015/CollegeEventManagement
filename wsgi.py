import os
from app import create_app
from seed_data import seed_database

# Create application for production WSGI server
env = os.getenv("FLASK_ENV", "production")
app = create_app(env)

# Auto-seed if running on a brand-new cloud database with 0 users
with app.app_context():
    db = app.config.get("DB")
    if db is not None:
        try:
            if db.users.count_documents({}) == 0:
                print("[WSGI] Fresh database detected on startup. Initializing demo seed data...")
                seed_database(db)
        except Exception as e:
            print(f"[WSGI] Note during startup auto-seed check: {e}")

if __name__ == "__main__":
    app.run()
