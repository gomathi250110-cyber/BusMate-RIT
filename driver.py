import sqlite3
import hashlib
import hmac
from datetime import datetime


DATABASE = "busmate.db"


# ==========================================
# DATABASE CONNECTION
# ==========================================

def get_connection():
    return sqlite3.connect(DATABASE)


# ==========================================
# DRIVER TABLE
# ==========================================

def setup_driver_table():

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS drivers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT UNIQUE NOT NULL,
            password_hash BLOB NOT NULL,
            salt BLOB NOT NULL
        )
    """)

    connection.commit()
    connection.close()


# ==========================================
# PASSWORD HASH
# ==========================================

def hash_password(password, salt):

    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        500000
    )


# ==========================================
# DRIVER REGISTRATION
# ==========================================

def driver_registration():

    print("\n======================================")
    print("          DRIVER REGISTRATION")
    print("======================================")

    name = input("\nEnter driver name: ").strip()

    phone = input(
        "Enter phone number: "
    ).strip()

    password = input(
        "Create password: "
    ).strip()

    if not name or not phone or not password:

        print("\nAll fields are required.")
        return

    salt = (
        b"busmate_driver_salt_2026"
    )

    password_hash = hash_password(
        password,
        salt
    )

    connection = get_connection()
    cursor = connection.cursor()

    try:

        cursor.execute("""
            INSERT INTO drivers
            (
                name,
                phone,
                password_hash,
                salt
            )
            VALUES (?, ?, ?, ?)
        """, (
            name,
            phone,
            password_hash,
            salt
        ))

        connection.commit()

        print("\nDriver registration successful!")
        print(f"Welcome, {name}!")

    except sqlite3.IntegrityError:

        print(
            "\nThis phone number is already registered."
        )

    connection.close()


# ==========================================
# DRIVER LOGIN
# ==========================================

def driver_login():

    print("\n======================================")
    print("             DRIVER LOGIN")
    print("======================================")

    phone = input(
        "\nEnter phone number: "
    ).strip()

    password = input(
        "Enter password: "
    ).strip()

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT id,
               name,
               phone,
               password_hash,
               salt
        FROM drivers
        WHERE phone = ?
    """, (phone,))

    driver = cursor.fetchone()

    connection.close()

    if not driver:

        print(
            "\nInvalid phone number or password."
        )

        return None

    (
        driver_id,
        name,
        phone,
        stored_hash,
        salt
    ) = driver

    password_hash = hash_password(
        password,
        salt
    )

    if hmac.compare_digest(
        password_hash,
        stored_hash
    ):

        print("\nLogin successful!")
        print(f"Welcome, {name}!")

        return {
            "id": driver_id,
            "name": name,
            "phone": phone
        }

    print(
        "\nInvalid phone number or password."
    )

    return None


# ==========================================
# VIEW AVAILABLE BUSES
# ==========================================

def view_available_buses():

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT id,
               bus_number,
               route_name
        FROM buses
        ORDER BY bus_number
    """)

    buses = cursor.fetchall()

    connection.close()

    if not buses:

        print("\nNo buses available.")

        return []

    print("\n========== AVAILABLE BUSES ==========")

    for (
        bus_id,
        bus_number,
        route_name
    ) in buses:

        print(
            f"{bus_number} | "
            f"{route_name}"
        )

    return buses


# ==========================================
# SELECT BUS
# ==========================================

def select_bus():

    print(
        "\n========== SELECT YOUR BUS =========="
    )

    buses = view_available_buses()

    if not buses:

        return None

    bus_number = input(
        "\nEnter your bus number: "
    ).strip().upper()

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT id,
               bus_number,
               route_name
        FROM buses
        WHERE bus_number = ?
    """, (bus_number,))

    bus = cursor.fetchone()

    connection.close()

    if not bus:

        print("\nBus not found.")

        return None

    bus_id, bus_number, route_name = bus

    print("\nBus selected successfully!")

    print(
        f"Bus   : {bus_number}"
    )

    print(
        f"Route : {route_name}"
    )

    return {
        "id": bus_id,
        "bus_number": bus_number,
        "route_name": route_name
    }


# ==========================================
# VIEW BUS BOARDING POINTS
# ==========================================

def view_bus_points(bus_id, bus_number):

    print(
        f"\n========== {bus_number} "
        f"BOARDING POINTS =========="
    )

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT stop_name,
               stop_time,
               stop_order
        FROM stops
        WHERE bus_id = ?
        AND direction = 'MORNING'
        ORDER BY stop_order
    """, (bus_id,))

    stops = cursor.fetchall()

    connection.close()

    if not stops:

        print(
            "\nNo boarding points found "
            "for this bus."
        )

        return

    for (
        stop_name,
        stop_time,
        stop_order
    ) in stops:

        print(
            f"{stop_order}. "
            f"{stop_name} "
            f"- {stop_time}"
        )


# ==========================================
# CREATE LOCATION TABLE
# ==========================================

def setup_location_table():

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bus_locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bus_id INTEGER UNIQUE NOT NULL,
            latitude REAL,
            longitude REAL,
            current_location TEXT,
            next_point TEXT,
            updated_at TEXT,
            is_active INTEGER DEFAULT 0
        )
    """)

    connection.commit()
    connection.close()


# ==========================================
# START LOCATION SHARING
# ==========================================

def start_location_sharing(
    driver,
    bus
):

    print(
        "\n======================================"
    )

    print(
        "       START LOCATION SHARING"
    )

    print(
        "======================================"
    )

    print(
        f"\nDriver : {driver['name']}"
    )

    print(
        f"Bus    : {bus['bus_number']}"
    )

    print(
        "\nLocation sharing started."
    )

    print(
        "For now this version accepts "
        "manual GPS coordinates."
    )

    print(
        "Real phone GPS + live Google-map "
        "tracking will be connected next."
    )

    while True:

        print(
            "\n--------------------------------------"
        )

        print(
            "1. Update Current Location"
        )

        print(
            "2. Stop Location Sharing"
        )

        choice = input(
            "\nEnter choice: "
        ).strip()

        if choice == "1":

            update_location(bus)

        elif choice == "2":

            stop_location_sharing(bus)

            break

        else:

            print(
                "\nInvalid choice."
            )


# ==========================================
# UPDATE LOCATION
# ==========================================

def update_location(bus):

    print(
        "\n========== UPDATE LOCATION =========="
    )

    latitude_text = input(
        "Enter latitude: "
    ).strip()

    longitude_text = input(
        "Enter longitude: "
    ).strip()

    current_location = input(
        "Enter current location name: "
    ).strip()

    next_point = input(
        "Enter next boarding point: "
    ).strip()

    try:

        latitude = float(
            latitude_text
        )

        longitude = float(
            longitude_text
        )

    except ValueError:

        print(
            "\nInvalid latitude or longitude."
        )

        return

    updated_at = datetime.now().strftime(
        "%d-%m-%Y %I:%M:%S %p"
    )

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO bus_locations
        (
            bus_id,
            latitude,
            longitude,
            current_location,
            next_point,
            updated_at,
            is_active
        )
        VALUES (?, ?, ?, ?, ?, ?, 1)

        ON CONFLICT(bus_id)
        DO UPDATE SET
            latitude = excluded.latitude,
            longitude = excluded.longitude,
            current_location = excluded.current_location,
            next_point = excluded.next_point,
            updated_at = excluded.updated_at,
            is_active = 1
    """, (
        bus["id"],
        latitude,
        longitude,
        current_location,
        next_point,
        updated_at
    ))

    connection.commit()
    connection.close()

    print(
        "\nLocation updated successfully!"
    )

    print(
        f"Current : {current_location}"
    )

    print(
        f"Next    : {next_point}"
    )

    print(
        f"Time    : {updated_at}"
    )


# ==========================================
# STOP LOCATION SHARING
# ==========================================

def stop_location_sharing(bus):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        UPDATE bus_locations
        SET is_active = 0
        WHERE bus_id = ?
    """, (bus["id"],))

    connection.commit()
    connection.close()

    print(
        "\nLocation sharing stopped."
    )


# ==========================================
# DRIVER DASHBOARD
# ==========================================

def driver_dashboard(driver):

    selected_bus = None

    while True:

        print(
            "\n======================================"
        )

        print(
            "           DRIVER DASHBOARD"
        )

        print(
            "======================================"
        )

        print(
            f"\nDriver: {driver['name']}"
        )

        print(
            "\n1. Select Bus"
        )

        print(
            "2. View Bus Boarding Points"
        )

        print(
            "3. Start / Share Location"
        )

        print(
            "4. Logout"
        )

        choice = input(
            "\nEnter your choice: "
        ).strip()

        # --------------------------------------
        # SELECT BUS
        # --------------------------------------

        if choice == "1":

            selected_bus = select_bus()

        # --------------------------------------
        # VIEW POINTS
        # --------------------------------------

        elif choice == "2":

            if not selected_bus:

                print(
                    "\nPlease select your bus first."
                )

                continue

            view_bus_points(
                selected_bus["id"],
                selected_bus["bus_number"]
            )

        # --------------------------------------
        # LOCATION SHARING
        # --------------------------------------

        elif choice == "3":

            if not selected_bus:

                print(
                    "\nPlease select your bus first."
                )

                continue

            view_bus_points(
                selected_bus["id"],
                selected_bus["bus_number"]
            )

            start_location_sharing(
                driver,
                selected_bus
            )

        # --------------------------------------
        # LOGOUT
        # --------------------------------------

        elif choice == "4":

            print(
                "\nLogging out..."
            )

            break

        else:

            print(
                "\nInvalid choice."
            )


# ==========================================
# DRIVER PORTAL
# ==========================================

def driver_portal():

    setup_driver_table()
    setup_location_table()

    while True:

        print(
            "\n======================================"
        )

        print(
            "            BUSMATE DRIVER"
        )

        print(
            "======================================"
        )

        print(
            "\n1. Driver Registration"
        )

        print(
            "2. Driver Login"
        )

        print(
            "3. Exit"
        )

        choice = input(
            "\nEnter your choice: "
        ).strip()

        if choice == "1":

            driver_registration()

        elif choice == "2":

            driver = driver_login()

            if driver:

                driver_dashboard(driver)

        elif choice == "3":

            print(
                "\nExiting Driver Portal..."
            )

            break

        else:

            print(
                "\nInvalid choice."
            )


# ==========================================
# START DRIVER PROGRAM
# ==========================================

if __name__ == "__main__":

    driver_portal()