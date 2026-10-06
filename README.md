# College Event Management System (ADBMS Project)

[![Python](https://img.shields.io/badge/Python-3.14%2B-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.1-black.svg)](https://flask.palletsprojects.com/)
[![MongoDB](https://img.shields.io/badge/MongoDB-NoSQL-green.svg)](https://www.mongodb.com/)
[![Tests](https://img.shields.io/badge/Tests-Pytest%20Passing-brightgreen.svg)]()

A complete, production-grade full-stack web application designed for academic evaluation in **Advanced Database Management Systems (ADBMS)**. This portal showcases the architecture, querying power, data modeling, concurrency guarantees, and indexing mechanisms of **MongoDB NoSQL** using **Python Flask** and **PyMongo**.

---

## Table of Contents
1. [Key Features by Role](#key-features-by-role)
2. [ADBMS & MongoDB NoSQL Concepts Demonstrated](#adbms--mongodb-nosql-concepts-demonstrated)
3. [MongoDB Data Model & Schema Design](#mongodb-data-model--schema-design)
4. [Tech Stack](#tech-stack)
5. [Windows Setup & Installation](#windows-setup--installation)
6. [Demo Accounts & Credentials](#demo-accounts--credentials)
7. [API Endpoints Reference](#api-endpoints-reference)
8. [Automated Testing](#automated-testing)
9. [Cloud Deployment Guide (Render, Railway, Atlas)](#cloud-deployment-guide)
10. [College Viva & Presentation Guide](#college-viva--presentation-guide)

---

## 1. Key Features by Role

### 🛡️ Admin
- **System-Wide Dashboard**: Real-time KPI counters (events, registrations, active users, attendance percentage) visualized with interactive **Chart.js** graphs.
- **Organizer Verification Queue**: Inspect incoming organizer applications (department, university registration number, faculty advisor) and verify/reject event-publishing privileges.
- **Event Approvals & Archival**: Review pending event proposals, approve, reject with feedback notes, or soft-archive.
- **Campus Venue Management**: Create and configure auditoriums, seminar halls, and open-air amphitheatres with seating capacity limits and facility tags.
- **Analytics & Aggregation Reports**: Multi-stage aggregation reports covering event category popularity, venue utilization, attendance ratios, and system activity with **CSV export**.
- **Security Audit Logs**: Immutable audit log recording every administrative/organizer action (actor, role, action, target collection, IP, timestamp).
- **Platform Suggestions**: Review and respond to student/organizer suggestions.

### 📋 Organizer
- **Event Creation & Management**: Create events with category, venue, schedule, markdown description, budget breakdown (mandatory above ₹10,000 threshold), and banner image upload with auto-resize.
- **Strict Verification Gate**: Only verified and approved organizers can create or publish events.
- **Attendee Roster & CSV Export**: Inspect registered, waitlisted, and checked-in students with real-time status badges and one-click CSV download.
- **QR Code Check-In Console**: Interactive check-in terminal supporting handheld barcode scanners or manual ticket code entry. Features live async validation, instant student identification, and strict double-check-in prevention.
- **Attendee Reminders**: Trigger reminder notifications dispatched to all confirmed attendees.
- **Feedback Management**: View attendee reviews, star ratings, and sentiment tags; reply directly to student feedback.

### 🎓 Student
- **Event Discovery**: Search and filter upcoming events by category, date range, and keywords with visual capacity progress bars.
- **Atomic Registration & Waitlisting**: Safe seat booking preventing overbooking. Automatic placement on priority waitlist when an event reaches capacity.
- **Waitlist Auto-Promotion**: When a registered student cancels, the oldest waitlisted student is atomically promoted to confirmed registration and immediately notified.
- **Digital QR Ticket**: Unique QR code boarding pass generated per registration with base64 data URI rendering and printable ticket view.
- **Attendance-Gated Feedback**: Only students who checked in at the venue can rate (1–5 stars) and review events.
- **Keyword Sentiment Demo**: Rule-based sentiment analysis categorizing feedback comments as Positive, Neutral, or Constructive.
- **In-App Notification Center**: Notifications for booking confirmation, waitlist promotion, cancellations, reminders, and organizer replies with read/unread, archive, and delete operations.

---

## 2. ADBMS & MongoDB NoSQL Concepts Demonstrated

| Concept | Implementation in Project | Why it matters |
| :--- | :--- | :--- |
| **Referencing vs. Embedding** | References (`ObjectId`) used for `users`, `events`, `registrations`, `venues`. Embedding used for budget items, feedback responses, and facility lists. | Avoids the 16MB document size limit for unbounded relationships while exploiting fast single-document read locality for bounded subdocuments. |
| **Atomicity & Concurrency Control** | `find_one_and_update` with `{ registered_count: { $lt: capacity } }` and `{ $inc: { registered_count: 1 } }`. | Prevents race conditions and overbooking under high concurrent traffic without heavy distributed locking. |
| **Indexing Strategies** | Unique indexes on `users.email`, `venues.code`, `registrations.ticket_code`. Compound index on `events (organizer_id, start_time)` and `registrations (event_id, student_id)`. | Accelerates multi-field queries, enforces business uniqueness at the database engine level, and eliminates costly in-memory sorts (`COLLSCAN` vs `IXSCAN`). |
| **Aggregation Pipeline** | Multi-stage aggregation pipelines: `$match` &rarr; `$lookup` &rarr; `$unwind` &rarr; `$group` &rarr; `$project` &rarr; `$sort`. | Demonstrates server-side analytics, computing attendance percentage: `(checked_in / total_pool) * 100`, category distribution, and venue utilization without pulling raw documents into RAM. |
| **Soft Deletions & Auditing** | `status: "archived"` for events; `is_active: False` for users; comprehensive `audit_logs` collection. | Preserves historical referential integrity, historical rosters, and satisfies security compliance guidelines. |
| **Flexible Deployment Architecture** | Dual engine support: Native MongoDB connection (local or Atlas) with seamless automatic fallback to `mongomock` in-memory engine. | Ensures zero crashes on evaluation machines lacking a running MongoDB daemon while connecting seamlessly to real clusters when configured. |

---

## 3. MongoDB Data Model & Schema Design

### 1. `users`
```json
{
  "_id": ObjectId("..."),
  "email": "student1@college.edu",
  "password_hash": "scrypt:32768:8:1$...",
  "full_name": "Rahul Sharma",
  "role": "student",
  "phone": "+919876543221",
  "is_active": true,
  "email_verified": true,
  "verification_token": null,
  "created_at": ISODate("2026-09-01T10:00:00Z")
}
```

### 2. `events`
```json
{
  "_id": ObjectId("..."),
  "title": "National Hackathon 2026: GenAI & Distributed NoSQL Systems",
  "organizer_id": ObjectId("..."),
  "venue_id": ObjectId("..."),
  "description": "Join the premier 24-hour collegiate hackathon...",
  "category": "Workshop",
  "start_time": ISODate("2026-10-05T10:00:00Z"),
  "end_time": ISODate("2026-10-05T16:00:00Z"),
  "capacity": 50,
  "registered_count": 2,
  "waitlist_count": 0,
  "status": "published",
  "banner_image": "abc123_hackathon.png",
  "budget": {
    "total": 25000.0,
    "breakdown": [
      { "item": "Winner Prizes: ₹15,000" },
      { "item": "Refreshments: ₹7,000" }
    ],
    "approved": true
  },
  "created_at": ISODate("2026-09-20T10:00:00Z")
}
```

### 3. `registrations`
```json
{
  "_id": ObjectId("..."),
  "event_id": ObjectId("..."),
  "student_id": ObjectId("..."),
  "ticket_code": "TKT-HACK2026-001",
  "status": "registered",
  "registered_at": ISODate("2026-09-25T11:00:00Z"),
  "check_in_time": null,
  "check_in_by": null
}
```

### 4. `venues`
```json
{
  "_id": ObjectId("..."),
  "name": "Sir C.V. Raman Grand Auditorium",
  "code": "AUD-01",
  "capacity": 350,
  "facilities": ["Dolby Surround Audio", "Laser Projector", "Central AC"],
  "is_active": true
}
```

### 5. `feedback`
```json
{
  "_id": ObjectId("..."),
  "event_id": ObjectId("..."),
  "student_id": ObjectId("..."),
  "rating": 5,
  "comment": "The hands-on aggregation demo was fantastic and clear!",
  "sentiment_label": "Positive",
  "sentiment_score": 0.9,
  "sentiment_keywords": { "positive": ["fantastic", "clear"], "negative": [] },
  "organizer_response": {
    "text": "Thank you Rahul! Glad you enjoyed it.",
    "responded_by": ObjectId("..."),
    "responded_at": ISODate("2026-09-26T12:00:00Z")
  }
}
```

---

## 4. Tech Stack

- **Backend**: Python 3.14+, Flask 3.1
- **Database**: MongoDB 6+ / MongoDB Atlas with `PyMongo` 4.18
- **In-Memory Mock Fallback**: `mongomock`
- **Frontend**: HTML5, CSS3, Bootstrap 5.3, FontAwesome 6, Vanilla JavaScript
- **Data Visualizations**: Chart.js 4.4
- **QR Ticketing**: `qrcode` with Pillow
- **Testing**: `pytest`

---

## 5. Windows Setup & Installation

### Step 1: Open PowerShell in the project directory
```powershell
cd c:\Users\Shweta\Desktop\anti_gravity_workspace\CollegeEventManagement
```

### Step 2: Install Dependencies
```powershell
python -m pip install -r requirements.txt
```

### Step 3: Configure Environment
Copy `.env.example` to `.env` (already pre-configured with working defaults):
```powershell
Copy-Item .env.example .env
```

*Note on MongoDB connection:*
- If you have MongoDB installed locally or a free MongoDB Atlas URI, set `MONGODB_URI` in `.env`:
  `MONGODB_URI=mongodb+srv://<user>:<pass>@cluster0.mongodb.net/college_events_db?retryWrites=true&w=majority`
- If no local MongoDB server is running, the app automatically switches to **mongomock** (high-fidelity in-memory MongoDB) so the application and tests run immediately without error!

### Step 4: Populate Seed Data
```powershell
python seed_data.py
```

### Step 5: Run Application
```powershell
python app.py
```
Open **`http://127.0.0.1:5000`** in your browser.

---

## 6. Demo Accounts & Credentials

The database seeder includes realistic mock accounts for quick evaluation:

| Role | Email | Password | Description |
| :--- | :--- | :--- | :--- |
| **Admin** | `admin@college.edu` | `Admin@123` | Dean / Platform Administrator |
| **Organizer (Verified)** | `organizer1@college.edu` | `Organizer@123` | ACM Lead (can publish events, scan tickets) |
| **Organizer (Pending)** | `organizer2@college.edu` | `Organizer@123` | Music Club Lead (under admin review) |
| **Student (With Ticket)** | `student1@college.edu` | `Student@123` | Has active QR ticket and attended seminar |
| **Student** | `student2@college.edu` | `Student@123` | General student attendee |

*Tip: The login page includes 1-click **Quick Demo Fill** buttons to speed up demonstration during evaluation!*

---

## 7. API Endpoints Reference

| Endpoint | Method | Role | Description |
| :--- | :--- | :--- | :--- |
| `/api/checkin` | `POST` | Organizer, Admin | JSON QR scanner check-in terminal |
| `/api/export/event/<event_id>/attendees.csv` | `GET` | Organizer, Admin | Download event attendee roster CSV |
| `/api/export/admin/events.csv` | `GET` | Admin | Download system-wide event statistics CSV |
| `/api/reports/charts-data` | `GET` | Admin | Aggregated data for Chart.js dashboard |

---

## 8. Automated Testing

Run the comprehensive pytest suite covering CRUD, capacity concurrency, waitlist promotion, QR check-in, feedback permissions, and aggregation pipelines:

```powershell
python -m pytest tests/ -v
```

---

## 9. Cloud Deployment Guide

The repository includes production deployment configurations for **Render**, **Railway**, and **MongoDB Atlas**:
- `Procfile` and `render.yaml` for automatic containerized deployment.
- `railway.json` for Railway NIXPACKS deployments.
- `wsgi.py` production entrypoint with automatic demo database seeder on initial startup.
- `run_waitress.py` for multi-threaded production serving on Windows.

For detailed step-by-step instructions with screenshots guidance, refer to **[DEPLOYMENT.md](DEPLOYMENT.md)**.

---

## 10. College Viva & Presentation Guide

### Key Questions to Anticipate in an ADBMS Viva:

1. **Why choose MongoDB over traditional RDBMS like MySQL for this system?**
   - *Answer:* College events have diverse polymorphic structures (hackathon rules, guest speaker bios, custom budget itemizations, media attachments) that vary across event types. MongoDB's document model allows flexible schema evolution without costly `ALTER TABLE` migrations. Furthermore, MongoDB aggregation pipelines efficiently compute cross-collection analytics directly inside the database engine.

2. **How does your system prevent event overbooking under concurrent registrations?**
   - *Answer:* We utilize MongoDB atomic conditional updates via `find_one_and_update`. The condition `{ registered_count: { $lt: capacity } }` ensures that only requests meeting the capacity criterion increment the counter (`{ $inc: { registered_count: 1 } }`). If multiple students click register simultaneously, MongoDB isolates each document update atomically at the document level, guaranteeing that capacity is never exceeded.

3. **How does waitlist promotion work?**
   - *Answer:* When a confirmed attendee cancels, the system atomically decrements `registered_count` and executes a FIFO query on `registrations` sorting by `registered_at: 1` with `status: 'waitlisted'`. The oldest record is atomically transitioned to `status: 'registered'`, and an in-app priority notification is dispatched.

4. **What indexing strategies did you employ?**
   - *Answer:*
     - Unique single-field index on `users.email` and `registrations.ticket_code`.
     - Compound index on `events (organizer_id, start_time)` to optimize the organizer dashboard query and date sorting.
     - Compound unique index on `feedback (event_id, student_id)` to ensure one student can only submit one feedback per event.
