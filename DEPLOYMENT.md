# Cloud Deployment Guide: College Event Management System

This guide walks you through deploying the **College Event Management System** for free to **Render** (or **Railway**) using **MongoDB Atlas** (Free M0 Shared Cluster).

---

## Architecture in the Cloud

```mermaid
flowchart LR
    Browser["Client Browser"]
    Render["Render.com / Railway Web Service (Gunicorn + Flask)"]
    Atlas[("MongoDB Atlas Cloud Database (M0 Free Tier)")]

    Browser <-->|HTTPS| Render
    Render <-->|PyMongo Connection String| Atlas
```

---

## Step 1: Set Up Free MongoDB Atlas Database (Takes ~2 minutes)

1. Go to **[mongodb.com/cloud/atlas](https://www.mongodb.com/cloud/atlas)** and sign up or log in.
2. Click **Create a Deployment** &rarr; Select the **M0 Free** cluster tier (Free Forever).
3. Select any cloud provider and region closest to you (e.g. AWS / Mumbai, Singapore, or Frankfurt).
4. **Security Quickstart**:
   - **Database User**: Create a username (e.g., `collegeadmin`) and password (e.g., `SecurePass123!`). *Save these!*
   - **Network Access**: Add IP Address &rarr; Click **Allow Access from Anywhere** (`0.0.0.0/0`). *(This allows your Render web service to connect to the database).*
5. Click **Finish and Close**.
6. On the database dashboard, click **Connect** &rarr; **Drivers** &rarr; **Python** (version 3.12 or later).
7. Copy your connection string. It will look like this:
   ```text
   mongodb+srv://collegeadmin:SecurePass123!@cluster0.abcde.mongodb.net/college_events_db?retryWrites=true&w=majority
   ```
   *(Replace `<password>` with your actual password and ensure the database name at the end is `college_events_db`).*

---

## Step 2: Push Code to GitHub

Open **PowerShell** in the project directory:

```powershell
cd c:\Users\Shweta\Desktop\anti_gravity_workspace\CollegeEventManagement
```

If you haven't already created a GitHub repository:
1. Go to **[github.com/new](https://github.com/new)** and create a new repository named `CollegeEventManagement` (Public or Private).
2. Run these commands in PowerShell:
   ```powershell
   git branch -M main
   git remote add origin https://github.com/<YOUR_GITHUB_USERNAME>/CollegeEventManagement.git
   git push -u origin main
   ```

---

## Step 3: Deploy to Render (Recommended - Free Tier)

1. Go to **[render.com](https://render.com)** and sign in with GitHub.
2. Click **New +** in the top right &rarr; Select **Web Service**.
3. Select **Build and deploy from a Git repository** &rarr; Connect your `CollegeEventManagement` repository.
4. Fill in the deployment settings:
   - **Name**: `college-event-management` *(or any unique name)*
   - **Region**: Closest to you (e.g., Singapore, Frankfurt, or Oregon)
   - **Branch**: `main`
   - **Root Directory**: Leave blank (default)
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn wsgi:app --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 120`
   - **Instance Type**: **Free**
5. Under **Environment Variables**, click **Add Environment Variable** and add:

   | Key | Value | Description |
   | :--- | :--- | :--- |
   | `MONGODB_URI` | `mongodb+srv://collegeadmin:SecurePass123!@cluster0.abcde.mongodb.net/college_events_db?retryWrites=true&w=majority` | Your MongoDB Atlas connection URI |
   | `DATABASE_NAME` | `college_events_db` | Database name |
   | `SECRET_KEY` | `college-prod-secret-key-2026-secure` | Session encryption secret key |
   | `FLASK_ENV` | `production` | Production environment flag |
   | `EMAIL_DELIVERY_MODE` | `local_demo` | Prints verification token on screen |
   | `BUDGET_BREAKDOWN_THRESHOLD` | `10000.0` | Budget review trigger |
   | `PYTHON_VERSION` | `3.11.9` | Stable runtime version |

6. Click **Create Web Service**.
7. Render will build and deploy your application. In ~2 minutes, your live URL will be active at:
   `https://college-event-management-xxxx.onrender.com`

---

## Automatic Database Initialization

When the application boots up for the first time against your new MongoDB Atlas database, `wsgi.py` automatically detects that the collections are empty and runs `seed_database()`. 

This means your live website is **immediately populated** with:
- **Admin**: `admin@college.edu` / `Admin@123`
- **Verified Organizer**: `organizer1@college.edu` / `Organizer@123`
- **Pending Organizer**: `organizer2@college.edu` / `Organizer@123`
- **Students**: `student1@college.edu` and `student2@college.edu` / `Student@123`
- Sample Venues, Hackathons, Cultural Fest, and Past Seminars!

---

## Alternative: Deploy to Railway

1. Go to **[railway.app](https://railway.app)** and sign in with GitHub.
2. Click **New Project** &rarr; **Deploy from GitHub repo**.
3. Select `CollegeEventManagement`.
4. Go to **Variables** tab and add `MONGODB_URI`, `SECRET_KEY`, and `FLASK_ENV=production`.
5. Under **Settings** &rarr; **Networking**, click **Generate Domain**.
6. Railway automatically uses `railway.json` and deploys your service.

---

## Local Production Testing (Windows)

To verify the production WSGI server locally before pushing to the cloud:

```powershell
python run_waitress.py
```
Open **`http://127.0.0.1:8000`** in your browser. This serves the site using the multi-threaded **Waitress WSGI server**.
