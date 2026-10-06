import os
import re
import uuid
from datetime import datetime, timedelta
from PIL import Image
from werkzeug.utils import secure_filename

# Valid Constants
VALID_CATEGORIES = ["Academic", "Cultural", "Sports", "Social", "Workshop", "Seminar"]
VALID_REG_STATUSES = ["registered", "waitlisted", "checked-in", "cancelled", "no-show"]
VALID_ROLES = ["admin", "organizer", "student"]
ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5 MB


def validate_email(email):
    """Validate email format."""
    if not email or not isinstance(email, str):
        return False, "Email address is required."
    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    if not re.match(pattern, email.strip()):
        return False, "Invalid email address format."
    return True, email.strip().lower()


def validate_phone(phone):
    """Phone number: 10–15 digits, with optional international + prefix."""
    if not phone or not isinstance(phone, str):
        return False, "Phone number is required."
    cleaned = phone.strip()
    pattern = r"^\+?[0-9]{10,15}$"
    if not re.match(pattern, cleaned):
        return False, "Phone number must be 10 to 15 digits, optionally prefixed with '+'."
    return True, cleaned


def validate_event_data(data, is_update=False):
    """
    Validate event creation and update fields:
    - Title: 2-200 chars
    - Description: min 50 chars
    - Category: must be in VALID_CATEGORIES
    - Start must be in the future (for new events or changed start dates)
    - End must be after start by at least 1 hour
    - Budget: non-negative, breakdown required if > threshold
    - Capacity: positive integer
    """
    errors = []
    
    # Title
    title = str(data.get("title", "")).strip()
    if len(title) < 2 or len(title) > 200:
        errors.append("Event title must be between 2 and 200 characters.")
        
    # Category
    category = str(data.get("category", "")).strip()
    if category not in VALID_CATEGORIES:
        errors.append(f"Category must be one of: {', '.join(VALID_CATEGORIES)}.")
        
    # Description
    description = str(data.get("description", "")).strip()
    if len(description) < 50:
        errors.append("Event description must be at least 50 characters long.")
        
    # Capacity
    try:
        capacity = int(data.get("capacity", 0))
        if capacity <= 0:
            errors.append("Capacity must be a positive integer greater than zero.")
    except (ValueError, TypeError):
        errors.append("Capacity must be a valid positive integer.")
        capacity = 0

    # Start and End Times
    start_time_val = data.get("start_time")
    end_time_val = data.get("end_time")
    start_dt = None
    end_dt = None
    
    if isinstance(start_time_val, str):
        try:
            start_dt = datetime.fromisoformat(start_time_val)
        except ValueError:
            errors.append("Invalid start time format. Expected YYYY-MM-DDTHH:MM.")
    elif isinstance(start_time_val, datetime):
        start_dt = start_time_val
        
    if isinstance(end_time_val, str):
        try:
            end_dt = datetime.fromisoformat(end_time_val)
        except ValueError:
            errors.append("Invalid end time format. Expected YYYY-MM-DDTHH:MM.")
    elif isinstance(end_time_val, datetime):
        end_dt = end_time_val

    if start_dt and end_dt:
        now = datetime.utcnow()
        if not is_update and start_dt <= now:
            errors.append("Event start time must be in the future.")
        if end_dt <= start_dt:
            errors.append("Event end time must be after the start time.")
        elif (end_dt - start_dt) < timedelta(hours=1):
            errors.append("Event duration must be at least 1 hour.")
    else:
        errors.append("Both start time and end time are required.")

    # Budget
    try:
        budget_total = float(data.get("budget_total", 0.0))
        if budget_total < 0:
            errors.append("Budget cannot be negative.")
        threshold = float(data.get("budget_threshold", 10000.0))
        breakdown = data.get("budget_breakdown", [])
        if budget_total > threshold and (not breakdown or len(breakdown) == 0):
            errors.append(f"A detailed budget breakdown is required for budgets exceeding ₹{threshold:,.0f}.")
    except (ValueError, TypeError):
        errors.append("Invalid budget format.")

    return len(errors) == 0, errors


def validate_and_process_image(file_storage, target_folder):
    """
    Validate uploaded image:
    - Allowed extensions: JPG, PNG, WEBP
    - Max size: 5MB
    - Validate actual file content with Pillow
    - Resize/compress to max dimensions (1200x800) maintaining aspect ratio
    - Generate unique safe filename
    """
    if not file_storage or file_storage.filename == "":
        return False, "No file selected.", None

    filename = file_storage.filename
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        return False, f"File format not allowed. Allowed formats: {', '.join(ALLOWED_IMAGE_EXTENSIONS)}.", None

    # Check file size by reading stream
    file_storage.seek(0, os.SEEK_END)
    size = file_storage.tell()
    file_storage.seek(0)
    
    if size > MAX_IMAGE_SIZE:
        return False, f"Image size exceeds 5MB limit ({size / (1024*1024):.2f} MB).", None

    try:
        image = Image.open(file_storage)
        image.verify()  # Verify it's genuinely an image
        file_storage.seek(0)
        image = Image.open(file_storage)
        
        # Convert RGBA/P to RGB for JPEG compatibility if saving as JPEG or WEBP
        if image.mode in ("RGBA", "P"):
            image = image.convert("RGB")
            
        # Resize if dimensions exceed 1200x800
        image.thumbnail((1200, 800), Image.Resampling.LANCZOS)
        
        safe_name = f"{uuid.uuid4().hex[:12]}_{secure_filename(filename)}"
        os.makedirs(target_folder, exist_ok=True)
        save_path = os.path.join(target_folder, safe_name)
        image.save(save_path, quality=85, optimize=True)
        
        return True, "Image uploaded and processed successfully.", safe_name
    except Exception as e:
        return False, f"Invalid or corrupted image file: {str(e)}", None


def sanitize_markdown(text):
    """
    Sanitize markdown/HTML string to prevent XSS attacks while allowing basic formatting.
    """
    if not text:
        return ""
    import html
    # Escape dangerous HTML entities
    escaped = html.escape(str(text))
    return escaped


def validate_feedback_data(rating, comment):
    """Validate student feedback: rating 1-5, comment up to 1000 characters."""
    errors = []
    try:
        rating_int = int(rating)
        if rating_int < 1 or rating_int > 5:
            errors.append("Rating must be an integer between 1 and 5.")
    except (ValueError, TypeError):
        errors.append("Invalid rating. Must be an integer between 1 and 5.")

    comment_str = str(comment or "").strip()
    if len(comment_str) > 1000:
        errors.append("Feedback comment cannot exceed 1000 characters.")

    return len(errors) == 0, errors
