# College Event Management System

> **Full-Stack Campus Event Portal built with Python Flask, MongoDB NoSQL, Chart.js, and QR Ticketing for Advanced Database Management Systems (ADBMS).**

---

## Overview

The **College Event Management System** is a complete, production-grade web application engineered to demonstrate modern NoSQL database design, high-concurrency handling, and server-side aggregation pipelines using **MongoDB** and **Flask**.

The platform provides dedicated workflows for **Administrators**, **Event Organizers**, and **Students**, featuring atomic capacity reservations, paperless QR ticketing, post-event feedback analysis, and real-time analytical dashboards.

---

## Table of Contents

- [Core Features by Role](#core-features-by-role)
- [ADBMS & MongoDB NoSQL Concepts](#adbms--mongodb-nosql-concepts)
- [Database Schema & Data Model](#database-schema--data-model)
- [Technology Stack](#technology-stack)
- [Quick Start Guide](#quick-start-guide)
- [Demo Credentials](#demo-credentials)
- [API Endpoints Reference](#api-endpoints-reference)
- [Automated Testing](#automated-testing)
- [Cloud Deployment](#cloud-deployment)
- [College Viva & Presentation Guide](#college-viva--presentation-guide)

---

## Core Features by Role

### 🛡️ Administrator
- **System-Wide Dashboard**: Real-time KPI counters (active events, bookings, registered users, overall attendance rate) visualized with interactive **Chart.js** graphs.
- **Organizer Verification Queue**: Review faculty and club lead credentials (college registration number, department, advisor) before granting event-publishing privileges.
- **Event Approvals & Archival**: Approve pending event drafts, reject with review feedback, or soft-archive completed events.
- **Venue Management**: Configure campus auditoriums, labs, and open grounds with capacity ceilings and facility tags.
- **Analytics & Aggregation Reports**: Multi-stage aggregation pipelines generating category popularity, venue utilization, and system activity metrics with **one-click CSV export**.
- **Security Audit Logs**: Immutable audit trail tracking every administrative action (actor, role, action, target collection, IP, timestamp).
- **Platform Suggestions**: Review and reply to student and organizer feedback.

### 📋 Event Organizer
- **Event Creation & Management**: Create events with categories, venues, schedules, rich markdown descriptions, banner image upload (with auto-compression), and budget breakdowns.
- **Verification Gate**: Only verified organizers approved by the administrator can publish events to students.
- **Attendee Roster & CSV Export**: Real-time roster of confirmed, waitlisted, and checked-in students with CSV download.
- **QR Check-In Console**: Live verification console supporting handheld barcode scanners or manual ticket entry with instant duplicate check-in prevention.
- **Automated Reminders**: Trigger reminder notifications to all confirmed attendees.
- **Feedback & Sentiment Review**: Inspect student ratings and keyword-categorized sentiment tags; post replies directly to student reviews.

### 🎓 Student
- **Event Discovery**: Search and filter upcoming campus events by category, date range, or keywords with live capacity progress bars.
- **Atomic Registration**: Instant seat reservation protected against overbooking. If an event is full, the student is automatically queued on a priority waitlist.
- **Waitlist Auto-Promotion**: When a registered student cancels, the oldest waitlisted attendee is atomically promoted to confirmed status and notified immediately.
- **Digital QR Ticket**: Unique QR code boarding pass generated per registration with base64 PNG rendering and a printable ticket layout.
- **Attendance-Gated Feedback**: Only students who checked in at the venue can submit ratings (1–5 stars) and reviews.
- **Keyword Sentiment Demo**: Rule-based categorization tagging comments as *Positive*, *Neutral*, or *Constructive*.
- **In-App Notification Center**: Notifications for booking confirmations, waitlist promotions, schedule reminders, and cancellations with mark-as-read and archival controls.

---

## ADBMS & MongoDB NoSQL Concepts

| ADBMS Principle | Implementation in Project | Technical Justification |
| :--- | :--- | :--- |
| **Referencing vs. Embedding** | References (`ObjectId`) used for `users`, `events`, `registrations`, `venues`. Embedding used for budget items, feedback responses, and facility lists. | Avoids the 16MB document size limit for unbounded attendee growth while maximizing fast read locality for bounded subdocuments. |
| **Atomic Concurrency Control** | `find_one_and_update` with `{ registered_count: { $lt: capacity } }` and `{ $inc: { registered_count: 1 } }`. | Eliminates race conditions and overbooking under simultaneous registrations without heavy distributed database locking. |
| **FIFO Waitlist Queue** | Atomic update query sorted by `registered_at: 1` promoting the oldest record when an active attendee cancels. | Demonstrates transactional-style state transitions using atomic single-document updates. |
| **Indexing Strategies** | Unique indexes on `users.email`, `venues.code`, `registrations.ticket_code`. Compound indexes on `events(organizer_id, start_time)` and `feedback(event_id, student_id)`. | Enforces business constraints at the database engine level and avoids expensive in-memory collection scans (`COLLSCAN` &rarr; `IXSCAN`). |
| **Aggregation Pipelines** | Multi-stage aggregation pipelines: `$match` &rarr; `$lookup` &rarr; `$unwind` &rarr; `$group` &rarr; `$project` &rarr; `$sort`. | Executes complex server-side data transformations and attendance analytics without loading raw documents into application RAM. |
| **Soft Deletions & Auditing** | `status: "archived"` for events; `is_active: False` for users; comprehensive `audit_logs` collection. | Preserves historical referential integrity and maintains an immutable security audit trail. |
| **Flexible Architecture** | Dual-engine support: native MongoDB (local or Atlas) with seamless fallback to in-memory `mongomock`. | Enables immediate zero-dependency testing during academic evaluations while remaining fully compatible with real cloud clusters. |

---

## Database Schema & Data Model

### Collections Overview

```text
college_events_db
├── users                     (User accounts, hashed passwords, roles)
├── organizer_verifications   (Verification requests, department, faculty advisor)
├── venues                    (Auditoriums, capacity limits, facilities)
├── events                    (Event schedule, capacity counters, budget)
├── registrations             (Tickets, attendee state, check-in timestamps)
├── feedback                  (Ratings, comments, sentiment labels, replies)
├── notifications             (In-app user alerts, read/archive status)
├── platform_suggestions      (User suggestions and administrator replies)
└── audit_logs                (Immutable security & action audit logs)
```

### Sample Document Structures

#### `users` Collection
```json
{
  "_id": "ObjectId('6701a1b2c3d4e5f6a7b8c901')",
  "email": "student1@college.edu",
  "password_hash": "scrypt:32768:8:1$...",
  "full_name": "Rahul Sharma",
  "role": "student",
  "phone": "+919876543221",
  "is_active": true,
  "email_verified": true,
  "created_at": "2026-09-01T10:00:00Z"
}
```

#### `events` Collection
```json
{
  "_id": "ObjectId('6701a1b2c3d4e5f6a7b8c902')",
  "title": "National Hackathon 2026: GenAI & Distributed Systems",
  "organizer_id": "ObjectId('6701a1b2c3d4e5f6a7b8c900')",
  "venue_id": "ObjectId('6701a1b2c3d4e5f6a7b8c910')",
  "category": "Workshop",
  "start_time": "2026-10-15T10:00:00Z",
  "end_time": "2026-10-15T16:00:00Z",
  "capacity": 50,
  "registered_count": 2,
  "waitlist_count": 0,
  "status": "published",
  "banner_image": "abc123_hackathon.png",
  "budget": {
    "total": 25000.0,
    "breakdown": [
      { "item": "Winner Prizes: ₹15,000" },
      { "item": "Refreshments: ₹10,000" }
    ],
    "approved": true
  }
}
```

#### `registrations` Collection
```json
{
  "_id": "ObjectId('6701a1b2c3d4e5f6a7b8c903')",
  "event_id": "ObjectId('6701a1b2c3d4e5f6a7b8c902')",
  "student_id": "ObjectId('6701a1b2c3d4e5f6a7b8c901')",
  "ticket_code": "TKT-HACK2026-001",
  "status": "registered",
  "registered_at": "2026-09-25T11:00:00Z",
  "check_in_time": null,
  "check_in_by": null
}
```

---

## Technology Stack

- **Backend**: Python 3.11+, Flask 3.1
- **Database**: MongoDB 6+ / MongoDB Atlas with `PyMongo` 4.18
- **In-Memory Fallback**: `mongomock`
- **WSGI Production Servers**: `gunicorn` (Linux/Cloud), `waitress` (Windows)
- **Frontend**: HTML5, CSS3, Bootstrap 5.3, FontAwesome 6, Vanilla JavaScript
- **Visualizations**: Chart.js 4.4
- **QR Engine**: `qrcode` with Pillow
- **Testing**: `pytest`

---

## Quick Start Guide

### 1. Clone the Repository
```bash
git clone https://github.com/shweeta1015/CollegeEventManagement.git
cd CollegeEventManagement
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
*(On Windows PowerShell: `Copy-Item .env.example .env`)*

> **Note on MongoDB**: If you have a local MongoDB instance or MongoDB Atlas cluster, set `MONGODB_URI` in `.env`. If MongoDB is not running locally, the system automatically runs on an in-memory high-fidelity mock engine with zero setup.

### 4. Populate Demonstration Data
```bash
python seed_data.py
```

### 5. Launch Application
```bash
python app.py
```
Open **`http://127.0.0.1:5000`** in your browser.

---

## Demo Credentials

The database seeder includes pre-configured demonstration accounts for evaluation:

| Role | Email | Password | Pre-configured State |
| :--- | :--- | :--- | :--- |
| **Administrator** | `admin@college.edu` | `Admin@123` | Full access to approval queues, venue management, audit logs, and reports |
| **Organizer (Verified)** | `organizer1@college.edu` | `Organizer@123` | Verified ACM Lead with active events, attendee rosters, and QR check-in terminal |
| **Organizer (Pending)** | `organizer2@college.edu` | `Organizer@123` | Pending review; demonstrates the verification gate (cannot publish until approved) |
| **Student (Attendee)** | `student1@college.edu` | `Student@123` | Has active QR ticket and checked-in attendance record eligible for reviews |
| **Student (General)** | `student2@college.edu` | `Student@123` | Unregistered attendee to test fresh event registration and waitlisting |

*Tip: The sign-in page features 1-click **Quick Demo Fill** buttons to speed up demonstration during evaluation.*

---

## API Endpoints Reference

| Endpoint | Method | Role | Description |
| :--- | :--- | :--- | :--- |
| `/api/checkin` | `POST` | Organizer, Admin | JSON QR scanner terminal for live attendee check-in |
| `/api/export/event/<id>/attendees.csv` | `GET` | Organizer, Admin | Export event attendee roster in CSV format |
| `/api/export/admin/events.csv` | `GET` | Admin | Export system-wide events and metrics in CSV format |
| `/api/reports/charts-data` | `GET` | Admin | Real-time aggregation feed for Chart.js dashboards |

---

## Automated Testing

The project includes an automated test suite covering authentication, role-based access control, event constraints, atomic capacity limits, QR check-in validation, and aggregation reports:

```bash
python -m pytest tests/ -v
```

**Results**: 22 passed tests (100% pass rate).

---

## Cloud Deployment

The repository includes production configurations ready for deployment:
- `Procfile` and `render.yaml` for one-click deployment on **Render.com**.
- `railway.json` for **Railway.app** deployment.
- `wsgi.py` production entrypoint with automatic demo seeding on brand-new cloud databases.
- `run_waitress.py` for multi-threaded production hosting on Windows.

For complete cloud setup instructions with MongoDB Atlas, see **[DEPLOYMENT.md](DEPLOYMENT.md)**.

---

## College Viva & Presentation Guide

### Key Questions to Anticipate in an ADBMS Viva:

1. **Why use MongoDB instead of a traditional RDBMS like MySQL?**
   - *Answer:* College events have dynamic and polymorphic structures (custom hackathon rules, speaker bios, varying budget breakdowns) that evolve across event types. MongoDB's document model accommodates schema evolution without expensive `ALTER TABLE` migrations. Furthermore, MongoDB aggregation pipelines allow complex multi-collection analytics to run directly inside the database engine.

2. **How does the system prevent event overbooking under high concurrency?**
   - *Answer:* We utilize MongoDB atomic conditional updates via `find_one_and_update`. The condition `{ registered_count: { $lt: capacity } }` ensures that only requests meeting the capacity ceiling increment the counter (`{ $inc: { registered_count: 1 } }`). If multiple students attempt to register simultaneously, MongoDB isolates each update at the document level, guaranteeing that capacity is never exceeded.

3. **How does the waitlist promotion algorithm work?**
   - *Answer:* When an attendee cancels a confirmed registration, the system atomically decrements `registered_count` and runs a FIFO query on `registrations` sorted by `registered_at: 1` with `status: 'waitlisted'`. The oldest record is atomically updated to `status: 'registered'`, and an in-app priority notification is immediately generated for that student.

4. **What indexing strategies were implemented?**
   - *Answer:*
     - Unique single-field index on `users.email` and `registrations.ticket_code`.
     - Compound index on `events (organizer_id, start_time)` to optimize organizer dashboard queries and chronological sorting.
     - Compound unique index on `feedback (event_id, student_id)` to ensure each student can submit only one review per attended event.
