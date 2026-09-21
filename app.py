from flask import Flask, request, jsonify, send_from_directory, render_template, redirect, url_for
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os
import random
import string
import jwt
from datetime import datetime, timedelta
from functools import wraps


# =====================================================
# FLASK APPLICATION
# =====================================================

app = Flask(__name__)
CORS(app)

# =====================================================
# CONFIGURATION
# =====================================================

app.config["SECRET_KEY"] = "your-super-secret-key-change-this-in-production"
JWT_EXPIRATION_HOURS = 24


@app.route("/")
def home():
    return render_template("index.html")

# =====================================================
# PROJECT DIRECTORIES
# =====================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

HTML_DIR = os.path.join(BASE_DIR, "templates")
CSS_DIR = os.path.join(BASE_DIR, "static", "css")
JS_DIR = os.path.join(BASE_DIR, "static", "js")
IMAGE_DIR = os.path.join(BASE_DIR, "static", "images")

DATABASE = os.path.join(BASE_DIR,  "database.db")
SCHEMA_FILE = os.path.join(BASE_DIR,  "schema.sql")


# =====================================================
# DATABASE HELPERS
# =====================================================

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_database():
    os.makedirs(os.path.dirname(DATABASE), exist_ok=True)

    conn = get_db()
    try:
        if os.path.exists(SCHEMA_FILE):
            with open(SCHEMA_FILE, "r", encoding="utf-8") as f:
                conn.executescript(f.read())
            conn.commit()
            print("Database schema initialized successfully")
        else:
            print(f"WARNING: Schema file not found at {SCHEMA_FILE}")
    finally:
        conn.close()


def generate_otp(length=6):
    return ''.join(random.choices(string.digits, k=length))


# =====================================================
# JWT HELPERS
# =====================================================

def generate_token(user_id, email, name):
    payload = {
        "user_id": user_id,
        "email": email,
        "name": name,
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS),
        "iat": datetime.utcnow()
    }
    return jwt.encode(payload, app.config["SECRET_KEY"], algorithm="HS256")


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        if "Authorization" in request.headers:
            auth_header = request.headers["Authorization"]
            try:
                token = auth_header.split(" ")[1]
            except IndexError:
                return jsonify({
                    "success": False,
                    "message": "Invalid Authorization header. Use: Bearer <token>"
                }), 401

        if not token:
            return jsonify({
                "success": False,
                "message": "Token is missing. Please login first."
            }), 401

        try:
            data = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])
            current_user = {
                "id": data["user_id"],
                "email": data["email"],
                "name": data["name"]
            }
        except jwt.ExpiredSignatureError:
            return jsonify({
                "success": False,
                "message": "Token has expired. Please login again."
            }), 401
        except jwt.InvalidTokenError:
            return jsonify({
                "success": False,
                "message": "Invalid token. Please login again."
            }), 401

        return f(current_user, *args, **kwargs)

    return decorated


# =====================================================
# STATIC FILES
# =====================================================

@app.route("/<page>.html")
def html_pages(page):
    return send_from_directory(HTML_DIR, f"{page}.html")


@app.route("/css/<path:filename>")
def css(filename):
    return send_from_directory(CSS_DIR, filename)


@app.route("/js/<path:filename>")
def javascript(filename):
    return send_from_directory(JS_DIR, filename)


@app.route("/images/<path:filename>")
def images(filename):
    return send_from_directory(IMAGE_DIR, filename)


# =====================================================
# AUTHENTICATION
# =====================================================

@app.route("/api/register", methods=["POST"])
def register():
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "Invalid JSON data"}), 400

    name = data.get("name")
    email = data.get("email")
    password = data.get("password")

    if not name or not email or not password:
        return jsonify({"success": False, "message": "Please enter all fields"}), 400

    hashed_password = generate_password_hash(password)

    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
            (name, email, hashed_password)
        )
        conn.commit()
        return jsonify({"success": True, "message": "Registration successful"})
    except sqlite3.IntegrityError:
        return jsonify({"success": False, "message": "Email already registered"}), 409
    finally:
        conn.close()
@app.route("/api/login", methods=["POST"])
def login():

    data = request.get_json()

    if not data:
        return jsonify({
            "success": False,
            "message": "Invalid JSON data"
        }), 400

    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({
            "success": False,
            "message": "Email and password are required"
        }), 400

    conn = get_db()

    try:

        cursor = conn.execute(
            """
            SELECT id, name, email, password
            FROM users
            WHERE email = ?
            """,
            (email,)
        )

        user = cursor.fetchone()

        if user is None:
            return jsonify({
                "success": False,
                "message": "Email is not registered"
            }), 401

        # Check entered password against hashed password
        if not check_password_hash(user["password"], password):
            return jsonify({
                "success": False,
                "message": "Incorrect password"
            }), 401

        return jsonify({
            "success": True,
            "message": "Login successful",
            "user": {
                "id": user["id"],
                "name": user["name"],
                "email": user["email"]
            }
        }), 200

    finally:
        conn.close()

def generate_otp():
    return str(random.randint(100000, 999999))
# =========================================================
# FORGOT PASSWORD - SEND OTP
# =========================================================

@app.route("/api/forgot-password", methods=["POST"])
def forgot_password():

    data = request.get_json()

    if not data:
        return jsonify({
            "success": False,
            "message": "Invalid JSON data"
        }), 400

    email = data.get("email", "").strip()

    if not email:
        return jsonify({
            "success": False,
            "message": "Email is required"
        }), 400

    conn = get_db()

    try:

        # Check whether email exists
        user = conn.execute(
            """
            SELECT id
            FROM users
            WHERE email = ?
            """,
            (email,)
        ).fetchone()

        if user is None:
            return jsonify({
                "success": False,
                "message": "Email not registered"
            }), 404

        # Generate 6-digit OTP
        otp = generate_otp()

        # OTP valid for 10 minutes
        expires_at = (
            datetime.now() + timedelta(minutes=10)
        ).strftime("%Y-%m-%d %H:%M:%S")

        # Delete previous OTP
        conn.execute(
            """
            DELETE FROM password_resets
            WHERE email = ?
            """,
            (email,)
        )

        # Save new OTP
        conn.execute(
            """
            INSERT INTO password_resets
            (email, otp, expires_at)
            VALUES (?, ?, ?)
            """,
            (email, otp, expires_at)
        )

        conn.commit()

        print("OTP for", email, "is:", otp)

        return jsonify({
            "success": True,
            "message": "OTP sent successfully",
            "otp": otp
        }), 200

    finally:
        conn.close()


# =========================================================
# VERIFY OTP
# =========================================================

@app.route("/api/verify-otp", methods=["POST"])
def verify_otp():

    data = request.get_json()

    if not data:
        return jsonify({
            "success": False,
            "message": "Invalid JSON data"
        }), 400

    email = data.get("email", "").strip()
    otp = data.get("otp", "").strip()

    if not email or not otp:
        return jsonify({
            "success": False,
            "message": "Email and OTP are required"
        }), 400

    conn = get_db()

    try:

        record = conn.execute(
            """
            SELECT otp, expires_at
            FROM password_resets
            WHERE email = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (email,)
        ).fetchone()

        if record is None:
            return jsonify({
                "success": False,
                "message": "No OTP found. Please request a new OTP."
            }), 400

        # Check OTP expiry
        expires_at = datetime.strptime(
            record["expires_at"],
            "%Y-%m-%d %H:%M:%S"
        )

        if datetime.now() > expires_at:

            return jsonify({
                "success": False,
                "message": "OTP has expired. Please request a new OTP."
            }), 400

        # Check OTP
        if record["otp"] != otp:

            return jsonify({
                "success": False,
                "message": "Invalid OTP"
            }), 400

        return jsonify({
            "success": True,
            "message": "OTP verified successfully"
        }), 200

    finally:
        conn.close()


# =========================================================
# RESET PASSWORD
# =========================================================

@app.route("/api/reset-password", methods=["POST"])
def reset_password():

    data = request.get_json()

    if not data:
        return jsonify({
            "success": False,
            "message": "Invalid JSON data"
        }), 400

    email = data.get("email", "").strip()
    otp = data.get("otp", "").strip()
    new_password = data.get("new_password")

    if not email or not otp or not new_password:

        return jsonify({
            "success": False,
            "message": "All fields are required"
        }), 400

    if len(new_password) < 6:

        return jsonify({
            "success": False,
            "message": "Password must be at least 6 characters"
        }), 400

    conn = get_db()

    try:

        # Get OTP record
        record = conn.execute(
            """
            SELECT otp, expires_at
            FROM password_resets
            WHERE email = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (email,)
        ).fetchone()

        if record is None:

            return jsonify({
                "success": False,
                "message": "No OTP found. Please request a new OTP."
            }), 400

        # Check expiry
        expires_at = datetime.strptime(
            record["expires_at"],
            "%Y-%m-%d %H:%M:%S"
        )

        if datetime.now() > expires_at:

            return jsonify({
                "success": False,
                "message": "OTP has expired. Please request a new OTP."
            }), 400

        # Check OTP
        if record["otp"] != otp:

            return jsonify({
                "success": False,
                "message": "Invalid OTP"
            }), 400

        # Hash the new password
        hashed_password = generate_password_hash(
            new_password
        )

        # Update password
        cursor = conn.execute(
            """
            UPDATE users
            SET password = ?
            WHERE email = ?
            """,
            (hashed_password, email)
        )

        if cursor.rowcount == 0:

            return jsonify({
                "success": False,
                "message": "User not found"
            }), 404

        # Delete used OTP
        conn.execute(
            """
            DELETE FROM password_resets
            WHERE email = ?
            """,
            (email,)
        )

        conn.commit()

        return jsonify({
            "success": True,
            "message": "Password reset successfully"
        }), 200

    finally:
        conn.close()


# =====================================================
# APPLIANCES
# =====================================================

@app.route("/api/appliances", methods=["POST"])
@token_required
def add_appliance(current_user):
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "Invalid JSON data"}), 400

    name = data.get("name")
    category = data.get("category")
    brand = data.get("brand")
    price = data.get("price")
    rating = data.get("rating")
    description = data.get("description")

    if not name or not category:
        return jsonify({"success": False, "message": "Name and category are required"}), 400

    conn = get_db()
    try:
        conn.execute(
            """
            INSERT INTO appliances (name, category, brand, price, rating, description)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (name, category, brand, price, rating, description)
        )
        conn.commit()
        return jsonify({"success": True, "message": "Appliance added successfully"})
    finally:
        conn.close()


@app.route("/api/appliances", methods=["GET"])
def get_appliances():
    conn = get_db()
    try:
        appliances = conn.execute(
            "SELECT * FROM appliances ORDER BY id DESC"
        ).fetchall()
        return jsonify([dict(a) for a in appliances])
    finally:
        conn.close()


@app.route("/api/appliances/search", methods=["GET"])
def search_appliances():
    keyword = request.args.get("keyword", "")

    conn = get_db()
    try:
        appliances = conn.execute(
            """
            SELECT * FROM appliances
            WHERE name LIKE ? OR category LIKE ? OR brand LIKE ?
            ORDER BY price ASC
            """,
            (f"%{keyword}%", f"%{keyword}%", f"%{keyword}%")
        ).fetchall()
        return jsonify([dict(a) for a in appliances])
    finally:
        conn.close()


@app.route("/api/appliances/comparison", methods=["GET"])
def compare_appliances():
    ids = request.args.get("ids", "")
    if not ids:
        return jsonify({"success": False, "message": "Please provide appliance IDs"}), 400

    try:
        id_list = [int(x) for x in ids.split(",")]
    except ValueError:
        return jsonify({"success": False, "message": "Invalid appliance IDs"}), 400

    placeholders = ",".join("?" * len(id_list))

    conn = get_db()
    try:
        appliances = conn.execute(
            f"SELECT * FROM appliances WHERE id IN ({placeholders})",
            id_list
        ).fetchall()
        return jsonify([dict(a) for a in appliances])
    finally:
        conn.close()


# =====================================================
# BOOKINGS (Updated with phone, person, address)
# =====================================================

@app.route("/api/booking", methods=["POST"])
def create_booking():
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "Invalid JSON data"}), 400

    name = data.get("name")
    email = data.get("email")
    phone = data.get("phone")
    person = data.get("person", "")
    service = data.get("service")
    booking_date = data.get("booking_date")
    address = data.get("address", "")
    message = data.get("message", "")

    if not name or not email or not service or not booking_date:
        return jsonify({
            "success": False,
            "message": "Please fill all required fields (name, email, service, date)"
        }), 400

    conn = get_db()
    try:
        cursor = conn.execute(
            """
            INSERT INTO bookings 
            (name, email, phone, person, service, booking_date, address, message)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (name, email, phone, person, service, booking_date, address, message)
        )
        conn.commit()

        return jsonify({
            "success": True,
            "message": "Booking submitted successfully",
            "booking_id": cursor.lastrowid
        })
    except Exception as e:
        conn.rollback()
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        conn.close()


@app.route("/api/booking", methods=["GET"])
@token_required
def get_bookings(current_user):
    conn = get_db()
    try:
        bookings = conn.execute(
            "SELECT * FROM bookings ORDER BY id DESC"
        ).fetchall()
        return jsonify([dict(b) for b in bookings])
    finally:
        conn.close()


# =====================================================
# CONTACT
# =====================================================

@app.route("/api/contact", methods=["POST"])
def contact():
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "Invalid JSON data"}), 400

    name = data.get("name")
    email = data.get("email")
    subject = data.get("subject", "")
    message = data.get("message")

    if not name or not email or not message:
        return jsonify({"success": False, "message": "Please fill all required fields"}), 400

    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO contacts (name, email, subject, message) VALUES (?, ?, ?, ?)",
            (name, email, subject, message)
        )
        conn.commit()
        return jsonify({"success": True, "message": "Message sent successfully"})
    finally:
        conn.close()


@app.route("/api/contacts", methods=["GET"])
@token_required
def get_contacts(current_user):
    conn = get_db()
    try:
        contacts = conn.execute(
            "SELECT * FROM contacts ORDER BY id DESC"
        ).fetchall()
        return jsonify([dict(c) for c in contacts])
    finally:
        conn.close()


# =====================================================
# REVIEWS
# =====================================================

@app.route("/api/review", methods=["POST"])
def add_review():
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "Invalid JSON data"}), 400

    name = data.get("name")
    rating = data.get("rating")
    comment = data.get("comment")

    if not name or rating is None or not comment:
        return jsonify({"success": False, "message": "Please fill all fields"}), 400

    try:
        rating = int(rating)
    except (ValueError, TypeError):
        return jsonify({"success": False, "message": "Rating must be a number"}), 400

    if rating < 1 or rating > 5:
        return jsonify({"success": False, "message": "Rating must be between 1 and 5"}), 400

    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO reviews (name, rating, comment) VALUES (?, ?, ?)",
            (name, rating, comment)
        )
        conn.commit()
        return jsonify({"success": True, "message": "Review submitted successfully"})
    except sqlite3.Error as e:
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        conn.close()


@app.route("/api/reviews", methods=["GET"])
def get_reviews():
    conn = get_db()
    try:
        reviews = conn.execute(
            "SELECT * FROM reviews ORDER BY id DESC"
        ).fetchall()
        return jsonify([dict(r) for r in reviews])
    finally:
        conn.close()

@app.route('/submit_review', methods=['POST'])
def submit_review():

    try:
        name = request.form.get('name')
        rating = request.form.get('rating')
        comment = request.form.get('comment')

        conn = get_db()

        conn.execute(
            "INSERT INTO reviews (name, rating, comment) VALUES (?, ?, ?)",
            (name, int(rating), comment)
        )

        conn.commit()
        conn.close()

        return "Review submitted successfully", 200

    except Exception as e:
        print("REVIEW ERROR:", e)
        return str(e), 500


# =====================================================
# ANALYTICS
# =====================================================

@app.route("/api/analytics", methods=["GET"])
@token_required
def analytics(current_user):
    conn = get_db()
    try:
        total_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        total_appliances = conn.execute("SELECT COUNT(*) FROM appliances").fetchone()[0]
        total_bookings = conn.execute("SELECT COUNT(*) FROM bookings").fetchone()[0]
        total_reviews = conn.execute("SELECT COUNT(*) FROM reviews").fetchone()[0]
        total_contacts = conn.execute("SELECT COUNT(*) FROM contacts").fetchone()[0]
        avg_rating = conn.execute("SELECT AVG(rating) FROM reviews").fetchone()[0]

        return jsonify({
            "total_users": total_users,
            "total_appliances": total_appliances,
            "total_bookings": total_bookings,
            "total_reviews": total_reviews,
            "total_contacts": total_contacts,
            "average_rating": round(avg_rating or 0, 2)
        })
    finally:
        conn.close()


# =====================================================
# START SERVER
# =====================================================

if __name__ == "__main__":
    initialize_database()

    print("=" * 55)
    print("  INSPIRED HOME SOLUTIONS - SERVER STARTED")
    print(f"  DATABASE : {DATABASE}")
    print("=" * 55)

    app.run(host="127.0.0.1", port=5000, debug=True)

 