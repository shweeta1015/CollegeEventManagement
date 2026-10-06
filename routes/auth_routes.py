from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app
from bson import ObjectId
from datetime import datetime

from services.auth_service import (
    register_user, authenticate_user, verify_email_token, deactivate_user_account
)
from routes.decorators import login_required
from database import create_audit_log

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        role = session.get("role")
        if role == "admin":
            return redirect(url_for("admin.dashboard"))
        elif role == "organizer":
            return redirect(url_for("organizer.dashboard"))
        return redirect(url_for("student.dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        ip_addr = request.remote_addr or "127.0.0.1"

        db = current_app.config["DB"]
        success, message, user = authenticate_user(db, email, password, ip_address=ip_addr)

        if not success:
            flash(message, "danger")
            return render_template("auth/login.html", email=email)

        # Establish secure session
        session.clear()
        session["user_id"] = str(user["_id"])
        session["email"] = user.get("email")
        session["full_name"] = user.get("full_name")
        session["role"] = user.get("role", "student")
        session["email_verified"] = user.get("email_verified", False)

        flash(f"Welcome back, {user.get('full_name')}!", "success")

        next_url = request.args.get("next")
        if next_url and next_url.startswith("/"):
            return redirect(next_url)

        if user.get("role") == "admin":
            return redirect(url_for("admin.dashboard"))
        elif user.get("role") == "organizer":
            return redirect(url_for("organizer.dashboard"))
        else:
            return redirect(url_for("student.dashboard"))

    return render_template("auth/login.html")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        return redirect(url_for("main.index"))

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        full_name = request.form.get("full_name", "").strip()
        role = request.form.get("role", "student")
        phone = request.form.get("phone", "").strip()
        reg_no = request.form.get("reg_no", "").strip()
        department = request.form.get("department", "").strip()

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template("auth/register.html", email=email, full_name=full_name, phone=phone, role=role)

        db = current_app.config["DB"]
        ip_addr = request.remote_addr or "127.0.0.1"
        success, message, user_id = register_user(
            db, email=email, password=password, full_name=full_name,
            role=role, phone=phone, ip_address=ip_addr,
            reg_no=reg_no, department=department
        )

        if not success:
            flash(message, "danger")
            return render_template("auth/register.html", email=email, full_name=full_name, phone=phone, role=role)

        # Fetch token for local demo assistance
        created_user = db.users.find_one({"_id": user_id})
        token = created_user.get("verification_token", "")

        flash(
            f"Registration successful! For local demo: Your email verification token is '{token}'. You may verify below or sign in now.", 
            "success"
        )
        return redirect(url_for("auth.verify_email", token=token))

    return render_template("auth/register.html")


@auth_bp.route("/verify-email", methods=["GET", "POST"])
def verify_email():
    token = request.args.get("token", "")

    if request.method == "POST":
        token = request.form.get("token", "").strip()
        db = current_app.config["DB"]
        success, message = verify_email_token(db, token)
        if success:
            if session.get("user_id"):
                session["email_verified"] = True
            flash("Email successfully verified! You can now log in.", "success")
            return redirect(url_for("auth.login"))
        else:
            flash(message, "danger")

    return render_template("auth/verify.html", token=token)


@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("You have been signed out.", "info")
    return redirect(url_for("main.index"))


@auth_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    db = current_app.config["DB"]
    user_id = session.get("user_id")
    user = db.users.find_one({"_id": ObjectId(user_id)})

    org_verif = None
    if user.get("role") == "organizer":
        org_verif = db.organizer_verifications.find_one({"user_id": ObjectId(user_id)})

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        phone = request.form.get("phone", "").strip()

        update_dict = {"updated_at": datetime.utcnow()}
        if full_name:
            update_dict["full_name"] = full_name
            session["full_name"] = full_name
        if phone:
            update_dict["phone"] = phone

        db.users.update_one({"_id": ObjectId(user_id)}, {"$set": update_dict})

        # Update organizer verification details if organizer
        if user.get("role") == "organizer":
            reg_no = request.form.get("reg_no", "").strip()
            dept = request.form.get("department", "").strip()
            advisor = request.form.get("faculty_advisor", "").strip()
            db.organizer_verifications.update_one(
                {"user_id": ObjectId(user_id)},
                {"$set": {
                    "college_reg_no": reg_no,
                    "department": dept,
                    "faculty_advisor": advisor,
                    "status": "pending",  # reset to pending review on edit
                    "updated_at": datetime.utcnow()
                }},
                upsert=True
            )

        flash("Profile updated successfully.", "success")
        return redirect(url_for("auth.profile"))

    return render_template("auth/profile.html", user=user, org_verif=org_verif)


@auth_bp.route("/deactivate-account", methods=["POST"])
@login_required
def deactivate():
    db = current_app.config["DB"]
    user_id = session.get("user_id")
    actor_role = session.get("role")

    success, msg = deactivate_user_account(db, user_id, user_id, actor_role)
    if success:
        session.clear()
        flash("Your account has been deactivated.", "info")
        return redirect(url_for("main.index"))
    else:
        flash(msg, "danger")
        return redirect(url_for("auth.profile"))
