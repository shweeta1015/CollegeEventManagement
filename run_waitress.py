"""
Local Production Server Launcher (Waitress WSGI for Windows)
Serves the College Event Management System on http://127.0.0.1:8000 and across local network.
"""
import os
from waitress import serve
from wsgi import app

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    print("=" * 70)
    print("  COLLEGE EVENT MANAGEMENT SYSTEM - PRODUCTION WSGI SERVER")
    print("=" * 70)
    print(f"  * Serving on http://127.0.0.1:{port}")
    print(f"  * Serving on http://localhost:{port}")
    print("  * Multi-threaded production server ready for evaluation.")
    print("  * Press Ctrl+C to terminate.")
    print("=" * 70)
    serve(app, host="0.0.0.0", port=port, threads=6)
