from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import sqlite3
import hashlib
import hmac
from datetime import datetime
from pathlib import Path

app = Flask(__name__)

# ============================================================
# APP CONFIGURATION
# ============================================================

app.secret_key = "busmate-secret-key-change-later"

DATABASE = str(Path(__file__).resolve().parent / "busmate.db")

DEFAULT_RETURN_TIME = "3:50 PM"


def get_default_return_time():
    """Return the admin-configured default return time."""
    connection = get_connection()
    row = connection.execute("SELECT setting_value FROM app_settings WHERE setting_key = ?", ("default_return_time",)).fetchone()
    connection.close()
    return row["setting_value"] if row and row["setting_value"] else DEFAULT_RETURN_TIME


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_connection():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


# ============================================================
# DATABASE SETUP
# ============================================================

def setup_database():

    connection = get_connection()
    cursor = connection.cursor()

    # --------------------------------------------------------
    # APP SETTINGS
    # --------------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS app_settings (
            setting_key TEXT PRIMARY KEY,
            setting_value TEXT NOT NULL
        )
    """)

    cursor.execute("""
        INSERT OR IGNORE INTO app_settings (setting_key, setting_value)
        VALUES (?, ?)
    """, ("default_return_time", DEFAULT_RETURN_TIME))

    # --------------------------------------------------------
    # BUSES
    # --------------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS buses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bus_number TEXT NOT NULL UNIQUE,
            route_name TEXT NOT NULL
        )
    """)

    # --------------------------------------------------------
    # STOPS
    # --------------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stops (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bus_id INTEGER NOT NULL,
            stop_name TEXT NOT NULL,
            stop_time TEXT,
            stop_order INTEGER,
            direction TEXT NOT NULL DEFAULT 'MORNING',
            FOREIGN KEY (bus_id) REFERENCES buses(id)
        )
    """)

    # --------------------------------------------------------
    # RETURN BUSES
    # --------------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS return_buses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bus_id INTEGER NOT NULL,
            travel_date TEXT NOT NULL,
            departure_time TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'AVAILABLE',
            UNIQUE(bus_id, travel_date),
            FOREIGN KEY (bus_id) REFERENCES buses(id)
        )
    """)

    # --------------------------------------------------------
    # STUDENTS
    # --------------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash BLOB NOT NULL,
            salt BLOB NOT NULL
        )
    """)

    # --------------------------------------------------------
    # FACULTY
    # --------------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS faculty (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            faculty_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash BLOB NOT NULL,
            salt BLOB NOT NULL
        )
    """)

    # --------------------------------------------------------
    # DRIVERS
    # --------------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS drivers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT UNIQUE NOT NULL,
            password_hash BLOB NOT NULL,
            salt BLOB NOT NULL
        )
    """)

    # Driver assignment/status fields for Admin transport control.
    driver_columns = {row[1] for row in cursor.execute("PRAGMA table_info(drivers)").fetchall()}
    if "assigned_bus_id" not in driver_columns:
        cursor.execute("ALTER TABLE drivers ADD COLUMN assigned_bus_id INTEGER")
    if "driver_status" not in driver_columns:
        cursor.execute("ALTER TABLE drivers ADD COLUMN driver_status TEXT NOT NULL DEFAULT 'OFFLINE'")

    # --------------------------------------------------------
    # BUS LOCATIONS
    # --------------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bus_locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bus_id INTEGER UNIQUE NOT NULL,
            latitude REAL,
            longitude REAL,
            current_location TEXT,
            next_point TEXT,
            updated_at TEXT,
            is_active INTEGER DEFAULT 0,
            bus_status TEXT NOT NULL DEFAULT 'NOT_STARTED',
            FOREIGN KEY (bus_id) REFERENCES buses(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bus_location_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bus_id INTEGER NOT NULL,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            recorded_at TEXT NOT NULL,
            FOREIGN KEY (bus_id) REFERENCES buses(id)
        )
    """)

    # --------------------------------------------------------
    # EXAM AFTERNOON BUSES
    # --------------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS exam_afternoon_buses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bus_id INTEGER NOT NULL,
            travel_date TEXT NOT NULL,
            departure_time TEXT NOT NULL,
            destination TEXT NOT NULL,
            UNIQUE(bus_id, travel_date),
            FOREIGN KEY (bus_id) REFERENCES buses(id)
        )
    """)

    # --------------------------------------------------------
    # NOTICES
    # --------------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            priority TEXT NOT NULL DEFAULT 'NORMAL',
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL
        )
    """)

    # Backward-compatible migration for existing databases.
    location_columns = {row[1] for row in cursor.execute("PRAGMA table_info(bus_locations)").fetchall()}
    if "bus_status" not in location_columns:
        cursor.execute("ALTER TABLE bus_locations ADD COLUMN bus_status TEXT NOT NULL DEFAULT 'NOT_STARTED'")
    if "driver_id" not in location_columns:
        cursor.execute("ALTER TABLE bus_locations ADD COLUMN driver_id INTEGER")
    if "sharing_expires_at" not in location_columns:
        cursor.execute("ALTER TABLE bus_locations ADD COLUMN sharing_expires_at TEXT")

    connection.commit()
    connection.close()


# ============================================================
# PASSWORD FUNCTIONS
# ============================================================

def hash_password(password, salt):

    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        500000
    )


def verify_password(password, salt, stored_hash):

    password_hash = hash_password(
        password,
        salt
    )

    return hmac.compare_digest(
        password_hash,
        stored_hash
    )


# ============================================================
# TIME FUNCTIONS
# ============================================================

def normalize_time(time_text):

    if not time_text:
        return None

    time_text = time_text.strip().upper()

    formats = [
        "%I:%M %p",
        "%I:%M%p",
        "%H:%M"
    ]

    for time_format in formats:

        try:

            time_value = datetime.strptime(
                time_text,
                time_format
            )

            return time_value.strftime(
                "%I:%M %p"
            ).lstrip("0")

        except ValueError:
            continue

    return None
def normalize_date(date_text):
    """
    Accept both:
    YYYY-MM-DD  -> HTML date input
    DD-MM-YYYY  -> database format
    Return DD-MM-YYYY
    """
    if not date_text:
        return None

    date_text = date_text.strip()

    for fmt in ("%d-%m-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(
                date_text, fmt
            ).strftime("%d-%m-%Y")
        except ValueError:
            continue

    return None


def time_to_minutes(time_text):

    normalized = normalize_time(
        time_text
    )

    if not normalized:
        return None

    time_value = datetime.strptime(
        normalized,
        "%I:%M %p"
    )

    return (
        time_value.hour * 60
        + time_value.minute
    )


def minutes_to_time(total_minutes):

    total_minutes = (
        total_minutes % (24 * 60)
    )

    hours = total_minutes // 60
    minutes = total_minutes % 60

    period = "AM"

    if hours >= 12:
        period = "PM"

    display_hour = hours % 12

    if display_hour == 0:
        display_hour = 12

    return (
        f"{display_hour}:"
        f"{minutes:02d} "
        f"{period}"
    )


# ============================================================
# RETURN STOP TIME CALCULATION
# ============================================================

def calculate_return_times(
    departure_time,
    morning_stops
):

    departure_minutes = time_to_minutes(
        departure_time
    )

    if departure_minutes is None:
        return None

    if not morning_stops:
        return None

    reversed_stops = list(
        reversed(morning_stops)
    )

    estimated_times = []

    current_minutes = departure_minutes

    first_stop_name = (
        reversed_stops[0]["stop_name"]
    )

    estimated_times.append({
        "stop_name": first_stop_name,
        "estimated_time":
            minutes_to_time(
                current_minutes
            )
    })

    for index in range(
        1,
        len(reversed_stops)
    ):

        previous_stop = (
            reversed_stops[index - 1]
        )

        current_stop = (
            reversed_stops[index]
        )

        previous_time = time_to_minutes(
            previous_stop["stop_time"]
        )

        current_time = time_to_minutes(
            current_stop["stop_time"]
        )

        gap = 0

        if (
            previous_time is not None
            and current_time is not None
        ):

            gap = abs(
                previous_time
                - current_time
            )

        if gap <= 0:
            gap = 2

        current_minutes += gap

        estimated_times.append({
            "stop_name":
                current_stop["stop_name"],
            "estimated_time":
                minutes_to_time(
                    current_minutes
                )
        })

    return estimated_times


# ============================================================
# HOME / LOGIN
# ============================================================

@app.route("/")
def home():

    return render_template(
        "login.html"
    )


@app.route("/login",methods=["GET", "POST"])
def login_page():

    return render_template(
        "login.html"
    )


# ============================================================
# LOGOUT
# ============================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(
        url_for("home")
    )


# ============================================================
# STUDENT REGISTRATION
# ============================================================

@app.route(
    "/student/register",
    methods=["GET", "POST"]
)
def student_register():

    if request.method == "GET":

        return render_template(
            "student.html",
            mode="register"
        )

    data = request.form

    name = data.get(
        "name",
        ""
    ).strip()

    student_id = data.get(
        "student_id",
        ""
    ).strip()

    email = data.get(
        "email",
        ""
    ).strip()

    password = data.get(
        "password",
        ""
    ).strip()

    if not all([
        name,
        student_id,
        email,
        password
    ]):

        return jsonify({
            "success": False,
            "message":
                "All fields are required."
        }), 400

    salt = b"busmate_student_salt_2026"

    password_hash = hash_password(
        password,
        salt
    )

    connection = get_connection()

    try:

        connection.execute("""
            INSERT INTO students
            (
                student_id,
                name,
                email,
                password_hash,
                salt
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            student_id,
            name,
            email,
            password_hash,
            salt
        ))

        connection.commit()

    except sqlite3.IntegrityError:

        connection.close()

        return jsonify({
            "success": False,
            "message":
                "Student ID or email already registered."
        }), 409

    connection.close()

    return jsonify({
        "success": True,
        "message":
            "Student registration successful."
    })


# ============================================================
# STUDENT LOGIN
# ============================================================

@app.route(
    "/student/login",
    methods=["POST"]
)
def student_login():

    login_id = request.form.get(
        "login_id",
        ""
    ).strip()

    password = request.form.get(
        "password",
        ""
    ).strip()

    connection = get_connection()

    student = connection.execute("""
        SELECT
            id,
            student_id,
            name,
            email,
            password_hash,
            salt
        FROM students
        WHERE student_id = ?
        OR email = ?
    """, (
        login_id,
        login_id
    )).fetchone()

    connection.close()

    if not student:

        return jsonify({
            "success": False,
            "message":
                "Invalid Student ID/Email or password."
        }), 401

    if not verify_password(
        password,
        student["salt"],
        student["password_hash"]
    ):

        return jsonify({
            "success": False,
            "message":
                "Invalid Student ID/Email or password."
        }), 401

    session["user_type"] = "student"
    session["user_id"] = student["id"]
    session["user_name"] = student["name"]

    return jsonify({
        "success": True,
        "redirect": "/student"
    })


# ============================================================
# STUDENT PORTAL
# ============================================================

@app.route("/student")
def student():

    if session.get("user_type") != "student":

        return redirect(
            url_for("login_page")
        )

    return render_template(
        "student.html",
        portal_type="Student",
        user_name=session.get(
            "user_name"
        )
    )


# ============================================================
# FACULTY REGISTRATION
# ============================================================

@app.route(
    "/faculty/register",
    methods=["GET", "POST"]
)
def faculty_register():

    if request.method == "GET":

        return render_template(
            "faculty.html",
            mode="register"
        )

    data = request.form

    name = data.get(
        "name",
        ""
    ).strip()

    faculty_id = data.get(
        "faculty_id",
        ""
    ).strip()

    email = data.get(
        "email",
        ""
    ).strip()

    password = data.get(
        "password",
        ""
    ).strip()

    if not all([
        name,
        faculty_id,
        email,
        password
    ]):

        return jsonify({
            "success": False,
            "message":
                "All fields are required."
        }), 400

    salt = b"busmate_faculty_salt_2026"

    password_hash = hash_password(
        password,
        salt
    )

    connection = get_connection()

    try:

        connection.execute("""
            INSERT INTO faculty
            (
                faculty_id,
                name,
                email,
                password_hash,
                salt
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            faculty_id,
            name,
            email,
            password_hash,
            salt
        ))

        connection.commit()

    except sqlite3.IntegrityError:

        connection.close()

        return jsonify({
            "success": False,
            "message":
                "Faculty ID or email already registered."
        }), 409

    connection.close()

    return jsonify({
        "success": True,
        "message":
            "Faculty registration successful."
    })


# ============================================================
# FACULTY LOGIN
# ============================================================

@app.route(
    "/faculty/login",
    methods=["POST"]
)
def faculty_login():

    login_id = request.form.get(
        "login_id",
        ""
    ).strip()

    password = request.form.get(
        "password",
        ""
    ).strip()

    connection = get_connection()

    faculty = connection.execute("""
        SELECT
            id,
            faculty_id,
            name,
            email,
            password_hash,
            salt
        FROM faculty
        WHERE faculty_id = ?
        OR email = ?
    """, (
        login_id,
        login_id
    )).fetchone()

    connection.close()

    if not faculty:

        return jsonify({
            "success": False,
            "message":
                "Invalid Faculty ID/Email or password."
        }), 401

    if not verify_password(
        password,
        faculty["salt"],
        faculty["password_hash"]
    ):

        return jsonify({
            "success": False,
            "message":
                "Invalid Faculty ID/Email or password."
        }), 401

    session["user_type"] = "faculty"
    session["user_id"] = faculty["id"]
    session["user_name"] = faculty["name"]

    return jsonify({
        "success": True,
        "redirect": "/faculty"
    })


# ============================================================
# FACULTY PORTAL
# ============================================================

@app.route("/faculty")
def faculty():

    if session.get("user_type") != "faculty":

        return redirect(
            url_for("login_page")
        )

    return render_template(
        "faculty.html",
        portal_type="Faculty",
        user_name=session.get(
            "user_name"
        )
    )


# ============================================================
# DRIVER REGISTRATION
# ============================================================

@app.route(
    "/driver/register",
    methods=["GET", "POST"]
)
def driver_register():

    if request.method == "GET":
        return render_template("driver_register.html")

    data = request.form
    name = data.get("name", "").strip()
    phone = data.get("phone", "").strip()

    if not name or not phone:
        return jsonify({
            "success": False,
            "message": "Driver name and phone number are required."
        }), 400

    # Keep the existing database columns intact, but do not expose or
    # require a fixed/shared password.  The driver's phone is stored as
    # the internal credential value; the UI login uses name + phone.
    salt = b"busmate_driver_salt_2026"
    password_hash = hash_password(phone, salt)

    connection = get_connection()
    try:
        connection.execute("""
            INSERT INTO drivers
            (name, phone, password_hash, salt, assigned_bus_id)
            VALUES (?, ?, ?, ?, NULL)
        """, (name, phone, password_hash, salt))
        connection.commit()
    except sqlite3.IntegrityError:
        connection.close()
        return jsonify({
            "success": False,
            "message": "This phone number is already registered."
        }), 409

    connection.close()
    return jsonify({
        "success": True,
        "message": "Driver registration successful. You can now login with your driver name and phone number."
    })


# ============================================================
# DRIVER LOGIN
# ============================================================

@app.route(
    "/driver/login",
    methods=["POST"]
)
def driver_login():

    name = request.form.get("driver_name", "").strip()
    phone = request.form.get("phone", "").strip()

    if not name or not phone:
        # Keep compatibility with the older client field name.
        phone = phone or request.form.get("username", "").strip()

    if not name or not phone:
        return jsonify({
            "success": False,
            "message": "Driver name and phone number are required."
        }), 400

    connection = get_connection()
    driver_row = connection.execute("""
        SELECT id, name, phone, assigned_bus_id
        FROM drivers
        WHERE lower(trim(name)) = lower(trim(?)) AND phone = ?
    """, (name, phone)).fetchone()
    connection.close()

    if not driver_row:
        return jsonify({
            "success": False,
            "message": "Invalid driver name or phone number."
        }), 401

    session.clear()
    session["user_type"] = "driver"
    session["user_id"] = driver_row["id"]
    session["user_name"] = driver_row["name"]
    session["driver_phone"] = driver_row["phone"]
    session["assigned_bus_id"] = driver_row["assigned_bus_id"]

    return jsonify({
        "success": True,
        "redirect": "/driver"
    })


# ============================================================
# DRIVER PORTAL
# ============================================================

@app.route("/driver")
def driver():

    if session.get("user_type") != "driver":

        return redirect(
            url_for("login_page")
        )

    return render_template(
        "driver.html",
        user_name=session.get(
            "user_name"
        )
    )


# ============================================================
# ADMIN LOGIN
# ============================================================

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "busmate123"


@app.route(
    "/admin/login",
    methods=["GET", "POST"]
)
def admin_login():

    if request.method == "GET":

        return render_template(
            "admin.html",
            mode="login"
        )

    username = request.form.get(
        "username",
        ""
    ).strip()

    password = request.form.get(
        "password",
        ""
    ).strip()

    if (
        username == ADMIN_USERNAME
        and password == ADMIN_PASSWORD
    ):

        session["user_type"] = "admin"
        session["user_name"] = "Administrator"

        return jsonify({
            "success": True,
            "redirect": "/admin"
        })

    return jsonify({
        "success": False,
        "message":
            "Invalid username or password."
    }), 401


# ============================================================
# ADMIN PORTAL
# ============================================================

@app.route("/admin")
def admin():

    if session.get("user_type") != "admin":

        return redirect(
            url_for("admin_login")
        )

    return render_template(
        "admin.html",
        mode="dashboard"
    )


# ============================================================
# API - ALL BUS ROUTES
# ============================================================

@app.route("/api/buses")
def get_buses():

    connection = get_connection()

    buses = connection.execute("""
        SELECT
            id,
            bus_number,
            route_name
        FROM buses
        ORDER BY bus_number
    """).fetchall()

    connection.close()

    return jsonify({
        "success": True,
        "buses": [
            {
                "id": row["id"],
                "bus_number": row["bus_number"],
                "route_name": row["route_name"]
            }
            for row in buses
        ]
    })


# ============================================================
# API - PUBLIC NOTICES
# ============================================================

@app.route("/api/notices")
def get_notices():

    connection = get_connection()

    notices = connection.execute("""
        SELECT id, title, message, priority, created_at
        FROM notices
        WHERE is_active = 1
        ORDER BY
            CASE priority
                WHEN 'URGENT' THEN 1
                WHEN 'IMPORTANT' THEN 2
                ELSE 3
            END,
            id DESC
        LIMIT 20
    """).fetchall()

    connection.close()

    return jsonify({
        "success": True,
        "notices": [
            {
                "id": row["id"],
                "title": row["title"],
                "message": row["message"],
                "priority": row["priority"],
                "created_at": row["created_at"]
            }
            for row in notices
        ]
    })


# ============================================================
# API - MORNING STOPS
# ============================================================

@app.route(
    "/api/bus/<bus_number>/stops"
)
def get_bus_stops(bus_number):

    bus_number = (
        bus_number.strip().upper()
    )

    connection = get_connection()

    bus = connection.execute("""
        SELECT
            id,
            bus_number,
            route_name
        FROM buses
        WHERE bus_number = ?
    """, (
        bus_number,
    )).fetchone()

    if not bus:

        connection.close()

        return jsonify({
            "success": False,
            "message": "Bus not found"
        }), 404

    stops = connection.execute("""
        SELECT
            stop_name,
            stop_time,
            stop_order
        FROM stops
        WHERE bus_id = ?
        AND direction = 'MORNING'
        ORDER BY stop_order
    """, (
        bus["id"],
    )).fetchall()

    connection.close()

    return jsonify({
        "success": True,
        "bus_number":
            bus["bus_number"],
        "route_name":
            bus["route_name"],
        "stops": [
            {
                "stop_name":
                    row["stop_name"],
                "stop_time":
                    row["stop_time"],
                "stop_order":
                    row["stop_order"]
            }
            for row in stops
        ]
    })


# ============================================================
# API - SEARCH BUS BY BOARDING POINT
# ============================================================

@app.route("/api/search")
def search_bus():

    stop_name = request.args.get(
        "stop",
        ""
    ).strip()

    if not stop_name:

        return jsonify({
            "success": False,
            "message":
                "Boarding point is required."
        }), 400

    connection = get_connection()

    results = connection.execute("""
        SELECT
            buses.bus_number,
            buses.route_name,
            stops.stop_name,
            stops.stop_time
        FROM stops

        JOIN buses
        ON stops.bus_id = buses.id

        WHERE stops.stop_name LIKE ?
        AND stops.direction = 'MORNING'

        ORDER BY buses.bus_number
    """, (
        f"%{stop_name}%",
    )).fetchall()

    connection.close()

    return jsonify({
        "success": True,
        "results": [
            {
                "bus_number":
                    row["bus_number"],
                "route_name":
                    row["route_name"],
                "stop_name":
                    row["stop_name"],
                "stop_time":
                    row["stop_time"]
            }
            for row in results
        ]
    })


# ============================================================
# API - RETURN BUS FOR ONE BUS
# ============================================================

@app.route(
    "/api/bus/<bus_number>/return"
)
def get_return_bus(bus_number):

    bus_number = (
        bus_number.strip().upper()
    )

    travel_date = request.args.get(
        "date"
    )

    if not travel_date:

        travel_date = datetime.now().strftime(
            "%d-%m-%Y"
        )

    connection = get_connection()

    bus = connection.execute("""
        SELECT
            id,
            bus_number,
            route_name
        FROM buses
        WHERE bus_number = ?
    """, (
        bus_number,
    )).fetchone()

    if not bus:

        connection.close()

        return jsonify({
            "success": False,
            "message":
                "Bus not found."
        }), 404

    special = connection.execute("""
        SELECT
            departure_time
        FROM return_buses

        WHERE bus_id = ?
        AND travel_date = ?
        AND status = 'AVAILABLE'
    """, (
        bus["id"],
        travel_date
    )).fetchone()

    connection.close()

    if special:

        departure_time = (
            special["departure_time"]
        )

        is_special = True

    else:

        departure_time = (
            get_default_return_time()
        )

        is_special = False

    return jsonify({
        "success": True,
        "bus_number":
            bus["bus_number"],
        "route_name":
            bus["route_name"],
        "date":
            travel_date,
        "departure_time":
            departure_time,
        "is_special":
            is_special,
        "message":
            "Admin updated late bus time"
            if is_special
            else "Default return time"
    })


# ============================================================
# API - ALL RETURN BUSES
# ============================================================

@app.route("/api/return-buses")
def get_all_return_buses():

    travel_date = request.args.get(
        "date"
    )

    if not travel_date:

        travel_date = datetime.now().strftime(
            "%d-%m-%Y"
        )

    connection = get_connection()

    buses = connection.execute("""
        SELECT
            buses.id,
            buses.bus_number,
            buses.route_name,
            return_buses.departure_time

        FROM buses

        LEFT JOIN return_buses

        ON buses.id = return_buses.bus_id

        AND return_buses.travel_date = ?

        AND return_buses.status = 'AVAILABLE'

        WHERE buses.id NOT IN (

            SELECT bus_id

            FROM exam_afternoon_buses

            WHERE travel_date = ?

        )

        ORDER BY buses.bus_number
    """, (
        travel_date,
        travel_date
    )).fetchall()

    connection.close()

    return jsonify({
        "success": True,
        "date":
            travel_date,
        "default_time":
            get_default_return_time(),
        "buses": [
            {
                "bus_number":
                    row["bus_number"],
                "route_name":
                    row["route_name"],
                "departure_time":
                    row["departure_time"]
                    if row["departure_time"]
                    else get_default_return_time(),
                "is_special":
                    bool(row["departure_time"])
            }
            for row in buses
        ]
    })


# ============================================================
# ADMIN - BUS / BOARDING POINT MANAGEMENT
# ============================================================

def admin_required():
    return session.get("user_type") == "admin"


@app.route("/api/admin/bus", methods=["POST"])
def admin_add_bus():
    if not admin_required():
        return jsonify({"success": False, "message": "Admin login required."}), 403
    data = request.get_json(silent=True) or {}
    bus_number = str(data.get("bus_number") or "").strip().upper()
    route_name = str(data.get("route_name") or "").strip()
    if not bus_number or not route_name:
        return jsonify({"success": False, "message": "Bus number and route name are required."}), 400
    db = get_connection()
    try:
        cur = db.execute("INSERT INTO buses (bus_number, route_name) VALUES (?, ?)", (bus_number, route_name))
        db.execute("INSERT OR IGNORE INTO bus_locations (bus_id, is_active) VALUES (?, 0)", (cur.lastrowid,))
        db.commit()
        bus_id = cur.lastrowid
    except sqlite3.IntegrityError:
        db.close()
        return jsonify({"success": False, "message": "This bus number already exists."}), 409
    db.close()
    return jsonify({"success": True, "message": "Bus added successfully.", "id": bus_id})


@app.route("/api/admin/bus/<int:bus_id>", methods=["DELETE"])
def admin_remove_bus(bus_id):
    if not admin_required():
        return jsonify({"success": False, "message": "Admin login required."}), 403
    db = get_connection()
    bus = db.execute("SELECT bus_number FROM buses WHERE id = ?", (bus_id,)).fetchone()
    if not bus:
        db.close()
        return jsonify({"success": False, "message": "Bus not found."}), 404
    # Delete dependent rows first because SQLite foreign keys are enabled.
    for table in ("stops", "return_buses", "exam_afternoon_buses", "bus_locations", "bus_location_history"):
        db.execute(f"DELETE FROM {table} WHERE bus_id = ?", (bus_id,))
    db.execute("DELETE FROM buses WHERE id = ?", (bus_id,))
    db.commit(); db.close()
    return jsonify({"success": True, "message": f"Bus {bus['bus_number']} removed successfully."})


@app.route("/api/admin/stop", methods=["POST"])
def admin_add_stop():
    if not admin_required():
        return jsonify({"success": False, "message": "Admin login required."}), 403
    data = request.get_json(silent=True) or {}
    try: bus_id = int(data.get("bus_id"))
    except (TypeError, ValueError): bus_id = 0
    stop_name = str(data.get("stop_name") or "").strip()
    stop_time = str(data.get("stop_time") or "").strip()
    # Admin transport management is intentionally morning-only.
    direction = "MORNING"
    if not bus_id or not stop_name:
        return jsonify({"success": False, "message": "Select a bus and enter a boarding point."}), 400
    db = get_connection()
    if not db.execute("SELECT id FROM buses WHERE id = ?", (bus_id,)).fetchone():
        db.close(); return jsonify({"success": False, "message": "Bus not found."}), 404
    row = db.execute("SELECT COALESCE(MAX(stop_order),0)+1 AS n FROM stops WHERE bus_id=? AND direction=?", (bus_id,direction)).fetchone()
    db.execute("INSERT INTO stops (bus_id, stop_name, stop_time, stop_order, direction) VALUES (?,?,?,?,?)", (bus_id,stop_name,stop_time or None,row["n"],direction))
    db.commit(); db.close()
    return jsonify({"success": True, "message": "Boarding point added successfully."})


@app.route("/api/admin/stop/<int:stop_id>", methods=["DELETE"])
def admin_remove_stop(stop_id):
    if not admin_required():
        return jsonify({"success": False, "message": "Admin login required."}), 403
    db = get_connection(); row = db.execute("SELECT stop_name FROM stops WHERE id=?",(stop_id,)).fetchone()
    if not row:
        db.close(); return jsonify({"success": False, "message": "Boarding point not found."}), 404
    db.execute("DELETE FROM stops WHERE id=?",(stop_id,)); db.commit(); db.close()
    return jsonify({"success": True, "message": "Boarding point removed successfully."})


@app.route("/api/admin/stops")
def admin_list_stops():
    if not admin_required():
        return jsonify({"success": False, "message": "Admin login required."}), 403
    db=get_connection()
    bus_id = request.args.get("bus_id", type=int)

    if bus_id:
        rows = db.execute("""SELECT stops.id, stops.bus_id, buses.bus_number, buses.route_name,
            stops.stop_name, stops.stop_time, stops.stop_order, stops.direction
            FROM stops JOIN buses ON buses.id=stops.bus_id
            WHERE stops.bus_id = ? AND stops.direction = 'MORNING'
            ORDER BY stops.stop_order""", (bus_id,)).fetchall()
    else:
        rows = db.execute("""SELECT stops.id, stops.bus_id, buses.bus_number, buses.route_name,
            stops.stop_name, stops.stop_time, stops.stop_order, stops.direction
            FROM stops JOIN buses ON buses.id=stops.bus_id
            WHERE stops.direction = 'MORNING'
            ORDER BY buses.bus_number, stops.stop_order""").fetchall()
    db.close()
    return jsonify({"success":True,"stops":[dict(r) for r in rows]})


# ============================================================
# ADMIN - DEFAULT RETURN TIME
# ============================================================

@app.route("/api/admin/default-return-time", methods=["GET", "POST"])
def admin_default_return_time():
    if not admin_required():
        return jsonify({"success": False, "message": "Admin login required."}), 403

    if request.method == "GET":
        return jsonify({"success": True, "default_return_time": get_default_return_time()})

    data = request.get_json(silent=True) or {}
    value = normalize_time(str(data.get("default_return_time") or "").strip())
    if not value:
        return jsonify({"success": False, "message": "Enter a valid time, for example 3:50 PM."}), 400

    connection = get_connection()
    connection.execute("""
        INSERT INTO app_settings(setting_key, setting_value) VALUES(?, ?)
        ON CONFLICT(setting_key) DO UPDATE SET setting_value = excluded.setting_value
    """, ("default_return_time", value))
    connection.commit()
    connection.close()

    return jsonify({"success": True, "default_return_time": value, "message": "Default return time updated successfully."})


# ============================================================
# ADMIN - ADD / UPDATE LATE BUS
# ============================================================

@app.route(
    "/api/admin/late-bus",
    methods=["POST"]
)
def admin_late_bus():

    if session.get("user_type") != "admin":

        return jsonify({
            "success": False,
            "message":
                "Admin login required."
        }), 403

    data = request.get_json() or {}

    bus_number = (
        data.get("bus_number")
        or ""
    ).strip().upper()

    travel_date = (
        data.get("travel_date")
        or ""
    ).strip()

    departure_time = (
        data.get("departure_time")
        or ""
    ).strip()

    if not all([
        bus_number,
        travel_date,
        departure_time
    ]):

        return jsonify({
            "success": False,
            "message":
                "Bus number, date and time are required."
        }), 400

    try:

        datetime.strptime(
            travel_date,
            "%d-%m-%Y"
        )

    except ValueError:

        return jsonify({
            "success": False,
            "message":
                "Date must be DD-MM-YYYY."
        }), 400

    departure_time = normalize_time(
        departure_time
    )

    if not departure_time:

        return jsonify({
            "success": False,
            "message":
                "Invalid departure time."
        }), 400

    departure_minutes = time_to_minutes(
        departure_time
    )

    if departure_minutes < 17 * 60:

        return jsonify({
            "success": False,
            "message":
                "Late bus time must be 5:00 PM or later."
        }), 400

    connection = get_connection()

    bus = connection.execute("""
        SELECT
            id,
            route_name
        FROM buses
        WHERE bus_number = ?
    """, (
        bus_number,
    )).fetchone()

    if not bus:

        connection.close()

        return jsonify({
            "success": False,
            "message":
                "Bus not found."
        }), 404

    # Exam-time buses are special buses, not late buses.
    exam_existing = connection.execute("""
        SELECT id
        FROM exam_afternoon_buses
        WHERE bus_id = ? AND travel_date = ?
    """, (bus["id"], travel_date)).fetchone()

    if exam_existing:
        connection.close()
        return jsonify({
            "success": False,
            "message": "This bus is already configured as an Exam Time Bus for this date. It cannot be added as a Late Bus."
        }), 409

    existing = connection.execute("""
        SELECT
            id
        FROM return_buses

        WHERE bus_id = ?

        AND travel_date = ?
    """, (
        bus["id"],
        travel_date
    )).fetchone()

    if existing:

        connection.execute("""
            UPDATE return_buses

            SET
                departure_time = ?,
                status = 'AVAILABLE'

            WHERE id = ?
        """, (
            departure_time,
            existing["id"]
        ))

        message = (
            "Late bus updated successfully."
        )

    else:

        connection.execute("""
            INSERT INTO return_buses
            (
                bus_id,
                travel_date,
                departure_time,
                status
            )
            VALUES (?, ?, ?, 'AVAILABLE')
        """, (
            bus["id"],
            travel_date,
            departure_time
        ))

        message = (
            "Late bus added successfully."
        )

    connection.commit()
    connection.close()

    return jsonify({
        "success": True,
        "message":
            message,
        "bus_number":
            bus_number,
        "route_name":
            bus["route_name"],
        "travel_date":
            travel_date,
        "departure_time":
            departure_time
    })


# ============================================================
# ADMIN - VIEW DAILY RETURN SETUP
# ============================================================

# ============================================================
# ADMIN - VIEW DAILY RETURN SETUP
# EXAM BUS TIME TAKES PRIORITY
# ============================================================

@app.route("/api/admin/daily-return")
def admin_daily_return():

    if session.get("user_type") != "admin":

        return jsonify({
            "success": False,
            "message": "Admin login required."
        }), 403

    travel_date = request.args.get("date")

    if not travel_date:
        travel_date = datetime.now().strftime("%d-%m-%Y")

    connection = get_connection()

    buses = connection.execute("""
        SELECT
            buses.id,
            buses.bus_number,
            buses.route_name,

            return_buses.id
                AS return_id,

            return_buses.departure_time
                AS return_departure_time,

            exam_afternoon_buses.id
                AS exam_id,

            exam_afternoon_buses.departure_time
                AS exam_departure_time,

            exam_afternoon_buses.destination
                AS exam_destination

        FROM buses

        LEFT JOIN return_buses
        ON buses.id = return_buses.bus_id
        AND return_buses.travel_date = ?
        AND return_buses.status = 'AVAILABLE'

        LEFT JOIN exam_afternoon_buses
        ON buses.id = exam_afternoon_buses.bus_id
        AND exam_afternoon_buses.travel_date = ?

        ORDER BY buses.bus_number

    """, (
        travel_date,
        travel_date
    )).fetchall()

    connection.close()

    result = []

    for row in buses:

        # ----------------------------------------------------
        # EXAM BUS HAS HIGHEST PRIORITY
        # ----------------------------------------------------

        if row["exam_departure_time"]:

            departure_time = row["exam_departure_time"]

            bus_type = "EXAM"

            destination = row["exam_destination"]

            is_special = True

        # ----------------------------------------------------
        # NORMAL LATE BUS
        # ----------------------------------------------------

        elif row["return_departure_time"]:

            departure_time = row["return_departure_time"]

            bus_type = "LATE"

            destination = None

            is_special = True

        # ----------------------------------------------------
        # DEFAULT RETURN BUS
        # ----------------------------------------------------

        else:

            departure_time = get_default_return_time()

            bus_type = "DEFAULT"

            destination = None

            is_special = False


        result.append({

            "bus_number":
                row["bus_number"],

            "return_id":
                row["return_id"] if "return_id" in row.keys() else None,

            "exam_id":
                row["exam_id"] if "exam_id" in row.keys() else None,

            "route_name":
                row["route_name"],

            "departure_time":
                departure_time,

            "bus_type":
                bus_type,

            "destination":
                destination,

            "is_exam":
                bus_type == "EXAM",

            "is_special":
                is_special

        })


    return jsonify({

        "success": True,

        "date":
            travel_date,

        "default_return_time":
            get_default_return_time(),

        "buses":
            result

    })


# ============================================================
# ADMIN - REMOVE LATE BUS
# ============================================================

@app.route(
    "/api/admin/late-bus/<int:return_id>",
    methods=["DELETE"]
)
def remove_late_bus(return_id):

    if session.get("user_type") != "admin":

        return jsonify({
            "success": False,
            "message":
                "Admin login required."
        }), 403

    connection = get_connection()

    result = connection.execute("""
        SELECT
            id, bus_id, travel_date, status
        FROM return_buses
        WHERE id = ?
    """, (
        return_id,
    )).fetchone()

    if not result:

        connection.close()

        return jsonify({
            "success": False,
            "message":
                "Late bus not found."
        }), 404

    connection.execute("""
        DELETE FROM return_buses
        WHERE id = ?
        AND status = 'AVAILABLE'
    """, (
        return_id,
    ))

    connection.commit()
    connection.close()

    return jsonify({
        "success": True,
        "message":
            "Late bus removed. Default 3:50 PM restored."
    })


# ============================================================
# API - EXAM TIME BUSES
# ============================================================

@app.route("/api/exam-buses")
def get_exam_buses():

    raw_date = request.args.get("date", "").strip()

    travel_date = normalize_date(raw_date)

    if not travel_date:
        return jsonify({
            "success": False,
            "message": "Invalid exam date."
        }), 400

    connection = get_connection()

    buses = connection.execute("""
        SELECT
            exam_afternoon_buses.id,
            buses.bus_number,
            buses.route_name,
            exam_afternoon_buses.travel_date,
            exam_afternoon_buses.departure_time,
            exam_afternoon_buses.destination
        FROM exam_afternoon_buses
        JOIN buses
            ON exam_afternoon_buses.bus_id = buses.id
        WHERE exam_afternoon_buses.travel_date = ?
        ORDER BY
            exam_afternoon_buses.departure_time,
            buses.bus_number
    """, (travel_date,)).fetchall()

    connection.close()

    return jsonify({
        "success": True,
        "date": travel_date,
        "buses": [
            {
                "id": row["id"],
                "bus_number": row["bus_number"],
                "route_name": row["route_name"],
                "travel_date": row["travel_date"],
                "departure_time": row["departure_time"],
                "destination": row["destination"]
            }
            for row in buses
        ]
    })


# ============================================================
# ADMIN - ADD / UPDATE EXAM AFTERNOON BUS
# ============================================================

@app.route(
    "/api/admin/exam-bus",
    methods=["POST"]
)
def admin_exam_bus():

    if session.get("user_type") != "admin":

        return jsonify({
            "success": False,
            "message":
                "Admin login required."
        }), 403

    data = request.get_json() or {}

    bus_number = (
        data.get("bus_number")
        or ""
    ).strip().upper()

    travel_date = (
        data.get("travel_date")
        or ""
    ).strip()

    departure_time = (
        data.get("departure_time")
        or ""
    ).strip()

    destination = (
        data.get("destination")
        or ""
    ).strip()

    if not all([
        bus_number,
        travel_date,
        departure_time,
        destination
    ]):

        return jsonify({
            "success": False,
            "message":
                "All exam bus fields are required."
        }), 400

    try:

        datetime.strptime(
            travel_date,
            "%d-%m-%Y"
        )

    except ValueError:

        return jsonify({
            "success": False,
            "message":
                "Date must be DD-MM-YYYY."
        }), 400

    departure_time = normalize_time(
        departure_time
    )

    if not departure_time:

        return jsonify({
            "success": False,
            "message":
                "Invalid time."
        }), 400

    connection = get_connection()

    bus = connection.execute("""
        SELECT
            id,
            route_name
        FROM buses
        WHERE bus_number = ?
    """, (
        bus_number,
    )).fetchone()

    if not bus:

        connection.close()

        return jsonify({
            "success": False,
            "message":
                "Bus not found."
        }), 404

    # An exam-time bus is a special bus. Remove any old late-bus
    # override for the same bus/date so it cannot be shown as LATE BUS.
    connection.execute("""
        DELETE FROM return_buses
        WHERE bus_id = ? AND travel_date = ?
    """, (bus["id"], travel_date))

    existing = connection.execute("""
        SELECT
            id
        FROM exam_afternoon_buses

        WHERE bus_id = ?

        AND travel_date = ?
    """, (
        bus["id"],
        travel_date
    )).fetchone()

    if existing:

        connection.execute("""
            UPDATE exam_afternoon_buses

            SET
                departure_time = ?,
                destination = ?

            WHERE id = ?
        """, (
            departure_time,
            destination,
            existing["id"]
        ))

        message = (
            "Exam time bus updated successfully."
        )

    else:

        connection.execute("""
            INSERT INTO exam_afternoon_buses
            (
                bus_id,
                travel_date,
                departure_time,
                destination
            )
            VALUES (?, ?, ?, ?)
        """, (
            bus["id"],
            travel_date,
            departure_time,
            destination
        ))

        message = (
            "Exam time bus added successfully."
        )

    connection.commit()
    connection.close()

    return jsonify({
        "success": True,
        "message":
            message,
        "bus_number":
            bus_number,
        "date":
            travel_date,
        "departure_time":
            departure_time,
        "destination":
            destination
    })


# ============================================================
# ADMIN - NOTICE MANAGEMENT
# ============================================================

@app.route("/api/admin/notices")
def admin_get_notices():

    if not admin_required():
        return jsonify({"success": False, "message": "Admin login required."}), 403

    connection = get_connection()
    notices = connection.execute("""
        SELECT id, title, message, priority, is_active, created_at
        FROM notices
        ORDER BY id DESC
    """).fetchall()
    connection.close()

    return jsonify({
        "success": True,
        "notices": [dict(row) for row in notices]
    })


@app.route("/api/admin/notice", methods=["POST"])
def admin_save_notice():

    if not admin_required():
        return jsonify({"success": False, "message": "Admin login required."}), 403

    data = request.get_json(silent=True) or {}
    title = str(data.get("title") or "").strip()
    message = str(data.get("message") or "").strip()
    priority = str(data.get("priority") or "NORMAL").strip().upper()
    notice_id = data.get("id")

    if priority not in ("NORMAL", "IMPORTANT", "URGENT"):
        priority = "NORMAL"

    if not title or not message:
        return jsonify({
            "success": False,
            "message": "Notice title and message are required."
        }), 400

    connection = get_connection()

    if notice_id:
        try:
            notice_id = int(notice_id)
        except (TypeError, ValueError):
            notice_id = 0

        if not notice_id or not connection.execute(
            "SELECT id FROM notices WHERE id = ?", (notice_id,)
        ).fetchone():
            connection.close()
            return jsonify({
                "success": False,
                "message": "Notice not found."
            }), 404

        connection.execute("""
            UPDATE notices
            SET title = ?, message = ?, priority = ?, is_active = 1
            WHERE id = ?
        """, (title, message, priority, notice_id))
        action = "updated"
    else:
        created_at = datetime.now().strftime("%d-%m-%Y %I:%M %p").lstrip("0")
        cur = connection.execute("""
            INSERT INTO notices
            (title, message, priority, is_active, created_at)
            VALUES (?, ?, ?, 1, ?)
        """, (title, message, priority, created_at))
        notice_id = cur.lastrowid
        action = "published"

    connection.commit()
    connection.close()

    return jsonify({
        "success": True,
        "message": f"Notice {action} successfully.",
        "id": notice_id
    })


@app.route("/api/admin/notice/<int:notice_id>", methods=["DELETE"])
def admin_delete_notice(notice_id):

    if not admin_required():
        return jsonify({"success": False, "message": "Admin login required."}), 403

    connection = get_connection()
    result = connection.execute(
        "DELETE FROM notices WHERE id = ?", (notice_id,)
    )
    connection.commit()
    connection.close()

    if result.rowcount == 0:
        return jsonify({
            "success": False,
            "message": "Notice not found."
        }), 404

    return jsonify({
        "success": True,
        "message": "Notice removed successfully."
    })


# ============================================================
# ADMIN - DELETE EXAM TIME BUS
# ============================================================

@app.route(
    "/api/admin/exam-bus/<int:exam_id>",
    methods=["DELETE"]
)
def remove_exam_bus(exam_id):

    if session.get("user_type") != "admin":

        return jsonify({
            "success": False,
            "message":
                "Admin login required."
        }), 403

    connection = get_connection()

    result = connection.execute("""
        SELECT
            id
        FROM exam_afternoon_buses
        WHERE id = ?
    """, (
        exam_id,
    )).fetchone()

    if not result:

        connection.close()

        return jsonify({
            "success": False,
            "message":
                "Exam time bus not found."
        }), 404

    connection.execute("""
        DELETE FROM exam_afternoon_buses
        WHERE id = ?
    """, (
        exam_id,
    ))

    connection.commit()
    connection.close()

    return jsonify({
        "success": True,
        "message":
            "Exam time bus removed successfully."
    })


# ============================================================
# ADMIN - DRIVER ASSIGNMENT & STATUS
# ============================================================

@app.route("/api/admin/drivers")
def admin_drivers():
    if session.get("user_type") != "admin":
        return jsonify({"success": False, "message": "Admin login required."}), 401

    connection = get_connection()
    rows = connection.execute("""
        SELECT
            d.id, d.name, d.phone, d.assigned_bus_id,
            b.bus_number AS assigned_bus_number,
            b.route_name AS assigned_route,
            COALESCE(bl.bus_status, 'NOT_STARTED') AS bus_status,
            COALESCE(bl.is_active, 0) AS location_active,
            bl.updated_at
        FROM drivers d
        LEFT JOIN buses b ON b.id = d.assigned_bus_id
        LEFT JOIN bus_locations bl ON bl.bus_id = d.assigned_bus_id
        ORDER BY d.id
    """).fetchall()
    connection.close()

    def driver_state(row):
        return "ACTIVE" if row["location_active"] else "OFFLINE"

    return jsonify({
        "success": True,
        "drivers": [{
            "id": r["id"], "name": r["name"], "phone": r["phone"],
            "assigned_bus_id": r["assigned_bus_id"],
            "assigned_bus_number": r["assigned_bus_number"],
            "assigned_route": r["assigned_route"],
            "driver_status": driver_state(r),
            "bus_status": r["bus_status"],
            "location_active": bool(r["location_active"]),
            "updated_at": r["updated_at"]
        } for r in rows]
    })


@app.route("/api/admin/driver/<int:driver_id>/assign", methods=["POST"])
def admin_assign_driver(driver_id):
    if session.get("user_type") != "admin":
        return jsonify({"success": False, "message": "Admin login required."}), 401

    data = request.get_json(silent=True) or {}
    raw_bus_id = data.get("bus_id")
    bus_id = None if raw_bus_id in (None, "", "null") else int(raw_bus_id)

    connection = get_connection()
    driver = connection.execute("SELECT id FROM drivers WHERE id = ?", (driver_id,)).fetchone()
    if not driver:
        connection.close()
        return jsonify({"success": False, "message": "Driver not found."}), 404

    if bus_id is not None:
        bus = connection.execute("SELECT id FROM buses WHERE id = ?", (bus_id,)).fetchone()
        if not bus:
            connection.close()
            return jsonify({"success": False, "message": "Bus not found."}), 404

    # One bus should have one driver assignment at a time.
    if bus_id is not None:
        connection.execute("UPDATE drivers SET assigned_bus_id = NULL WHERE assigned_bus_id = ? AND id != ?", (bus_id, driver_id))
    connection.execute("UPDATE drivers SET assigned_bus_id = ? WHERE id = ?", (bus_id, driver_id))
    connection.commit()
    connection.close()
    return jsonify({"success": True, "message": "Driver assignment updated."})


# ============================================================
# DRIVER - AVAILABLE BUSES / BUS SELECTION
# ============================================================

@app.route("/api/driver/buses")
def driver_buses():
    if session.get("user_type") != "driver":
        return jsonify({"success": False, "message": "Driver login required."}), 401

    connection = get_connection()
    driver = connection.execute(
        "SELECT assigned_bus_id FROM drivers WHERE id = ?",
        (session.get("user_id"),)
    ).fetchone()

    selected_bus_id = driver["assigned_bus_id"] if driver else None
    rows = connection.execute(
        "SELECT id, bus_number, route_name FROM buses ORDER BY bus_number"
    ).fetchall()
    connection.close()

    return jsonify({
        "success": True,
        "assigned_bus_id": selected_bus_id,
        "buses": [
            {
                "id": row["id"],
                "bus_number": row["bus_number"],
                "route_name": row["route_name"],
                "assigned": row["id"] == selected_bus_id
            }
            for row in rows
        ]
    })


@app.route("/api/driver/select-bus", methods=["POST"])
def driver_select_bus():
    if session.get("user_type") != "driver":
        return jsonify({"success": False, "message": "Driver login required."}), 401

    data = request.get_json(silent=True) or {}
    try:
        bus_id = int(data.get("bus_id"))
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "Please select a valid bus."}), 400

    connection = get_connection()
    driver_id = session.get("user_id")
    driver = connection.execute(
        "SELECT assigned_bus_id FROM drivers WHERE id = ?",
        (driver_id,)
    ).fetchone()
    bus = connection.execute(
        "SELECT id, bus_number, route_name FROM buses WHERE id = ?",
        (bus_id,)
    ).fetchone()
    if not bus:
        connection.close()
        return jsonify({"success": False, "message": "Bus not found."}), 404

    # The driver can change buses on a different day. Remove this driver's
    # old live session so that the old bus never continues showing their name.
    previous_bus_id = driver["assigned_bus_id"] if driver else None
    if previous_bus_id and previous_bus_id != bus_id:
        connection.execute("""
            UPDATE bus_locations
            SET is_active = 0, driver_id = NULL, sharing_expires_at = NULL,
                bus_status = 'COMPLETED'
            WHERE bus_id = ? AND driver_id = ?
        """, (previous_bus_id, driver_id))

    # Selecting a bus starts a fresh session for that bus. Old driver details
    # are cleared immediately and the new driver appears only after GPS starts.
    connection.execute("""
        UPDATE bus_locations
        SET is_active = 0, driver_id = NULL, sharing_expires_at = NULL,
            bus_status = 'NOT_STARTED'
        WHERE bus_id = ?
    """, (bus_id,))
    connection.execute("DELETE FROM bus_location_history WHERE bus_id = ?", (bus_id,))

    connection.execute(
        "UPDATE drivers SET assigned_bus_id = ? WHERE id = ?",
        (bus_id, driver_id)
    )
    connection.commit()
    connection.close()
    session["assigned_bus_id"] = bus_id
    return jsonify({
        "success": True,
        "bus_id": bus["id"],
        "bus_number": bus["bus_number"],
        "route_name": bus["route_name"],
        "message": f"{bus['bus_number']} selected successfully."
    })


# ============================================================
# DRIVER GPS UPDATE
# ============================================================

@app.route(
    "/api/location/update",
    methods=["POST"]
)
def update_location():

    data = request.get_json()

    if not data:

        return jsonify({
            "success": False,
            "message":
                "No location data received."
        }), 400

    bus_number = (
        data.get("bus_number")
        or ""
    ).strip().upper()

    latitude = data.get(
        "latitude"
    )

    longitude = data.get(
        "longitude"
    )

    current_location = (
        data.get("current_location")
        or ""
    ).strip()

    next_point = (
        data.get("next_point")
        or ""
    ).strip()

    bus_status = str(data.get("bus_status") or "ON_ROUTE").strip().upper()
    allowed_statuses = {"NOT_STARTED", "ON_ROUTE", "DELAYED", "BREAKDOWN", "COMPLETED"}
    if bus_status not in allowed_statuses:
        bus_status = "ON_ROUTE"

    sharing_expires_at = (data.get("sharing_expires_at") or "").strip() or None

    if not bus_number:

        return jsonify({
            "success": False,
            "message":
                "Bus number is required."
        }), 400

    if latitude is None or longitude is None:

        return jsonify({
            "success": False,
            "message":
                "Latitude and longitude are required."
        }), 400

    try:

        latitude = float(latitude)
        longitude = float(longitude)

    except (TypeError, ValueError):

        return jsonify({
            "success": False,
            "message":
                "Invalid GPS coordinates."
        }), 400

    if not (
        -90 <= latitude <= 90
        and -180 <= longitude <= 180
    ):

        return jsonify({
            "success": False,
            "message":
                "GPS coordinates are out of range."
        }), 400

    if session.get("user_type") != "driver":
        return jsonify({"success": False, "message": "Driver login required."}), 401

    driver_id = session.get("user_id")
    connection = get_connection()
    driver = connection.execute("SELECT id, assigned_bus_id FROM drivers WHERE id = ?", (driver_id,)).fetchone()
    if not driver or not driver["assigned_bus_id"]:
        connection.close()
        return jsonify({"success": False, "message": "No bus is assigned to this driver."}), 403

    bus = connection.execute("""
        SELECT
            id,
            bus_number,
            route_name
        FROM buses
        WHERE bus_number = ?
    """, (
        bus_number,
    )).fetchone()

    if not bus:

        connection.close()

        return jsonify({
            "success": False,
            "message":
                "Bus not found."
        }), 404

    if bus["id"] != driver["assigned_bus_id"]:
        connection.close()
        return jsonify({"success": False, "message": "You can update only your assigned bus."}), 403

    previous = connection.execute(
        "SELECT is_active FROM bus_locations WHERE bus_id = ?",
        (bus["id"],)
    ).fetchone()
    was_active = bool(previous["is_active"]) if previous else False

    updated_at = datetime.now().strftime(
        "%d-%m-%Y %I:%M:%S %p"
    )

    connection.execute("""
        INSERT INTO bus_locations
        (
            bus_id,
            latitude,
            longitude,
            current_location,
            next_point,
            updated_at,
            is_active,
            bus_status,
            driver_id,
            sharing_expires_at
        )

        VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?, ?)

        ON CONFLICT(bus_id)

        DO UPDATE SET

            latitude = excluded.latitude,

            longitude = excluded.longitude,

            current_location =
                excluded.current_location,

            next_point =
                excluded.next_point,

            updated_at =
                excluded.updated_at,

            is_active = 1,

            bus_status =
                excluded.bus_status,

            driver_id =
                excluded.driver_id,

            sharing_expires_at =
                excluded.sharing_expires_at
    """, (
        bus["id"],
        latitude,
        longitude,
        current_location,
        next_point,
        updated_at,
        bus_status,
        driver_id,
        sharing_expires_at
    ))

    # Start a fresh trail when a driver starts a new sharing session.
    if not was_active:
        connection.execute(
            "DELETE FROM bus_location_history WHERE bus_id = ?",
            (bus["id"],)
        )

    connection.execute("""
        INSERT INTO bus_location_history (bus_id, latitude, longitude, recorded_at)
        VALUES (?, ?, ?, ?)
    """, (bus["id"], latitude, longitude, updated_at))
    connection.execute("""
        DELETE FROM bus_location_history
        WHERE bus_id = ? AND id NOT IN (
            SELECT id FROM bus_location_history WHERE bus_id = ? ORDER BY id DESC LIMIT 500
        )
    """, (bus["id"], bus["id"]))
    connection.commit()
    connection.close()

    return jsonify({
        "success": True,
        "message":
            "Location updated successfully.",
        "bus_number":
            bus_number,
        "latitude":
            latitude,
        "longitude":
            longitude,
        "updated_at":
            updated_at,
        "bus_status":
            bus_status
    })


# ============================================================
# DRIVER - UPDATE BUS STATUS WITHOUT GPS
# ============================================================

@app.route("/api/location/status/<bus_number>", methods=["POST"])
def update_bus_status(bus_number):
    if session.get("user_type") != "driver":
        return jsonify({"success": False, "message": "Driver login required."}), 401
    bus_number = bus_number.strip().upper()
    data = request.get_json(silent=True) or {}
    bus_status = str(data.get("bus_status") or "").strip().upper()
    allowed_statuses = {"NOT_STARTED", "ON_ROUTE", "DELAYED", "BREAKDOWN", "COMPLETED"}
    if bus_status not in allowed_statuses:
        return jsonify({"success": False, "message": "Invalid bus status."}), 400

    connection = get_connection()
    bus = connection.execute("SELECT id FROM buses WHERE bus_number = ?", (bus_number,)).fetchone()
    driver = connection.execute("SELECT assigned_bus_id FROM drivers WHERE id = ?", (session.get("user_id"),)).fetchone()
    if not bus:
        connection.close()
        return jsonify({"success": False, "message": "Bus not found."}), 404

    if not driver or driver["assigned_bus_id"] != bus["id"]:
        connection.close()
        return jsonify({"success": False, "message": "You can update only your assigned bus."}), 403

    existing = connection.execute("SELECT id FROM bus_locations WHERE bus_id = ?", (bus["id"],)).fetchone()
    now = datetime.now().strftime("%d-%m-%Y %I:%M:%S %p")
    if existing:
        connection.execute("UPDATE bus_locations SET bus_status = ?, updated_at = ? WHERE bus_id = ?", (bus_status, now, bus["id"]))
    else:
        connection.execute("INSERT INTO bus_locations (bus_id, updated_at, is_active, bus_status) VALUES (?, ?, 0, ?)", (bus["id"], now, bus_status))
    connection.commit()
    connection.close()
    return jsonify({"success": True, "bus_number": bus_number, "bus_status": bus_status, "updated_at": now})


# ============================================================
# DRIVER - STOP LOCATION SHARING
# ============================================================

@app.route(
    "/api/location/stop/<bus_number>",
    methods=["POST"]
)
def stop_location(bus_number):

    if session.get("user_type") != "driver":
        return jsonify({"success": False, "message": "Driver login required."}), 401

    bus_number = (
        bus_number.strip().upper()
    )

    connection = get_connection()

    bus = connection.execute("""
        SELECT
            id
        FROM buses
        WHERE bus_number = ?
    """, (
        bus_number,
    )).fetchone()

    if not bus:

        connection.close()

        return jsonify({
            "success": False,
            "message":
                "Bus not found."
        }), 404

    driver = connection.execute("SELECT assigned_bus_id FROM drivers WHERE id = ?", (session.get("user_id"),)).fetchone()
    if not driver or driver["assigned_bus_id"] != bus["id"]:
        connection.close()
        return jsonify({"success": False, "message": "You can stop only your assigned bus."}), 403

    connection.execute("""
        UPDATE bus_locations
        SET is_active = 0,
            bus_status = 'COMPLETED',
            driver_id = NULL,
            sharing_expires_at = NULL
        WHERE bus_id = ?
    """, (
        bus["id"],
    ))

    connection.commit()
    connection.close()

    return jsonify({
        "success": True,
        "message":
            "Location sharing stopped."
    })


# ============================================================
# LIVE BUS LOCATION
# ============================================================

@app.route(
    "/api/bus-location/<bus_number>"
)
def get_bus_location(bus_number):

    bus_number = (
        bus_number.strip().upper()
    )

    connection = get_connection()

    bus = connection.execute("""
        SELECT
            id,
            bus_number,
            route_name
        FROM buses
        WHERE bus_number = ?
    """, (
        bus_number,
    )).fetchone()

    if not bus:

        connection.close()

        return jsonify({
            "success": False,
            "message":
                "Bus not found."
        }), 404

    location = connection.execute("""
        SELECT
            latitude,
            longitude,
            current_location,
            next_point,
            updated_at,
            is_active,
            bus_status,
            driver_id,
            sharing_expires_at
        FROM bus_locations
        WHERE bus_id = ?
    """, (
        bus["id"],
    )).fetchone()

    history = connection.execute("""
        SELECT latitude, longitude, recorded_at
        FROM bus_location_history
        WHERE bus_id = ?
        ORDER BY id ASC
    """, (bus["id"],)).fetchall()

    # Driver details belong only to the current active live-location session.
    # Do not fall back to drivers.assigned_bus_id, because that can expose a
    # driver's details from a previous day/session.
    active = bool(location["is_active"]) if location else False
    expires_at = location["sharing_expires_at"] if location else None
    if active and expires_at:
        try:
            active = datetime.fromisoformat(expires_at).timestamp() > datetime.now().timestamp()
        except ValueError:
            active = True

    driver = None
    if active and location and location["driver_id"]:
        driver = connection.execute(
            "SELECT name, phone FROM drivers WHERE id = ?",
            (location["driver_id"],)
        ).fetchone()

    # A location without a current driver session is not a live session.
    if active and not driver:
        active = False

    if not location:
        connection.close()
        return jsonify({
            "success": True,
            "bus_number": bus["bus_number"],
            "route_name": bus["route_name"],
            "location_shared": False,
            "driver_name": None,
            "driver_phone": None,
            "bus_status": "NOT_STARTED",
            "message": "Driver has not shared location yet."
        })

    if not active:
        connection.execute("""
            UPDATE bus_locations
            SET is_active = 0, driver_id = NULL, sharing_expires_at = NULL
            WHERE bus_id = ?
        """, (bus["id"],))
        connection.commit()

    if not active:
        connection.close()
        return jsonify({
            "success": True,
            "bus_number": bus["bus_number"],
            "route_name": bus["route_name"],
            "location_shared": False,
            "driver_name": None,
            "driver_phone": None,
            "bus_status": "NOT_STARTED",
            "message": "Driver has not shared location yet."
        })

    # Return the current active sharing session.  The previous version
    # accidentally returned location_shared=False even for an active session,
    # which made Student/Faculty show "not shared" continuously.
    connection.close()

    return jsonify({
        "success": True,
        "bus_number":
            bus["bus_number"],
        "route_name":
            bus["route_name"],
        "location_shared": active,
        "driver_name": driver["name"] if driver else None,
        "driver_phone": driver["phone"] if driver else None,
        "sharing_expires_at": expires_at,
        "latitude":
            location["latitude"],
        "longitude":
            location["longitude"],
        "current_location":
            location["current_location"],
        "next_point":
            location["next_point"],
        "updated_at":
            location["updated_at"],
        "bus_status":
            location["bus_status"] or "NOT_STARTED",
        "history": [
            {"latitude": r["latitude"], "longitude": r["longitude"], "recorded_at": r["recorded_at"]}
            for r in history
        ]
    })


# ============================================================
# LIVE MAP PAGE
# ============================================================

@app.route("/live-map")
def live_map():

    return render_template(
        "live_map.html"
    )


# Also supports direct HTML-style URL
@app.route("/live-map.html")
def live_map_html():

    return render_template(
        "live_map.html"
    )


# ============================================================
# ROUTES PAGE
# ============================================================

@app.route("/routes")
def routes_page():

    return render_template(
        "routes.html"
    )


# ============================================================
# STOPS PAGE
# ============================================================

@app.route("/stops")
def stops_page():

    return render_template(
        "stops.html"
    )


# ============================================================
# DATABASE INITIALIZATION
# ============================================================

setup_database()


# ============================================================
# RUN APPLICATION
# ============================================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )