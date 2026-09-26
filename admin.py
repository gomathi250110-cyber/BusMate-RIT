import sqlite3
import hashlib
import hmac
from datetime import datetime


DATABASE = "busmate.db"


def get_connection():
    return sqlite3.connect(DATABASE)


# ==========================================
# ADMIN LOGIN
# ==========================================

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "busmate123"


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


def admin_login():

    print("\n======================================")
    print("          BUSMATE ADMIN LOGIN")
    print("======================================")

    username = input("\nUsername: ").strip()
    password = input("Password: ").strip()

    if username != ADMIN_USERNAME:
        print("\nInvalid username or password.")
        return False

    salt = b"busmate_admin_salt_2026"

    stored_hash = hash_password(
        ADMIN_PASSWORD,
        salt
    )

    if verify_password(
        password,
        salt,
        stored_hash
    ):
        print("\nLogin successful!")
        return True

    print("\nInvalid username or password.")
    return False


# ==========================================
# VIEW BUS ROUTES
# ==========================================

def view_routes():

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT id, bus_number, route_name
        FROM buses
        ORDER BY bus_number
    """)

    buses = cursor.fetchall()
    connection.close()

    if not buses:
        print("\nNo bus routes available.")
        return []

    print("\n========== BUS ROUTES ==========")

    for bus_id, bus_number, route_name in buses:
        print(
            f"{bus_number} | {route_name}"
        )

    return buses


# ==========================================
# VALIDATE DATE
# ==========================================

def validate_date(date_text):

    try:
        datetime.strptime(
            date_text,
            "%d-%m-%Y"
        )
        return True

    except ValueError:
        return False


# ==========================================
# NORMALIZE TIME
# ==========================================

def normalize_time(time_text):

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


# ==========================================
# TIME TO MINUTES
# ==========================================

def time_to_minutes(time_text):

    normalized = normalize_time(time_text)

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


# ==========================================
# ADD / UPDATE LATE BUS
# ==========================================

def add_late_bus():

    print("\n========== MANAGE LATE BUS ==========")

    travel_date = input(
        "Enter date (DD-MM-YYYY): "
    ).strip()

    if not validate_date(travel_date):

        print("\nInvalid date.")
        print("Use format: DD-MM-YYYY")
        return

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT return_buses.id,
               buses.bus_number,
               buses.route_name,
               return_buses.departure_time
        FROM return_buses
        JOIN buses
        ON return_buses.bus_id = buses.id
        WHERE return_buses.travel_date = ?
        AND return_buses.status = 'AVAILABLE'
        ORDER BY return_buses.departure_time
    """, (travel_date,))

    late_buses = cursor.fetchall()

    print(
        f"\n========== LATE BUSES - "
        f"{travel_date} =========="
    )

    if late_buses:

        for (
            return_id,
            bus_number,
            route_name,
            departure_time
        ) in late_buses:

            print(
                f"{bus_number} | "
                f"{route_name} | "
                f"{departure_time}"
            )

    else:

        print("No late buses added yet.")

    cursor.execute("""
        SELECT id, bus_number, route_name
        FROM buses
        ORDER BY bus_number
    """)

    buses = cursor.fetchall()

    print("\n========== BUS ROUTES ==========")

    for bus_id, bus_number, route_name in buses:

        print(
            f"{bus_number} | {route_name}"
        )

    bus_number = input(
        "\nEnter late bus number: "
    ).strip().upper()

    cursor.execute("""
        SELECT id, route_name
        FROM buses
        WHERE bus_number = ?
    """, (bus_number,))

    bus = cursor.fetchone()

    if not bus:

        connection.close()

        print("\nBus not found.")
        return

    bus_id, route_name = bus

    departure_time = input(
        "Enter departure time "
        "(Example: 5:00 PM): "
    ).strip()

    departure_time = normalize_time(
        departure_time
    )

    if not departure_time:

        connection.close()

        print("\nInvalid time.")
        return

    departure_minutes = time_to_minutes(
        departure_time
    )

    five_pm = 17 * 60

    if departure_minutes < five_pm:

        connection.close()

        print(
            "\nThis section is only for "
            "5:00 PM or later buses."
        )

        print(
            "Normal buses automatically use 3:50 PM."
        )

        return

    cursor.execute("""
        SELECT id
        FROM return_buses
        WHERE bus_id = ?
        AND travel_date = ?
    """, (
        bus_id,
        travel_date
    ))

    existing = cursor.fetchone()

    if existing:

        return_bus_id = existing[0]

        cursor.execute("""
            UPDATE return_buses
            SET departure_time = ?,
                status = 'AVAILABLE'
            WHERE id = ?
        """, (
            departure_time,
            return_bus_id
        ))

        print("\nLate bus updated successfully!")

    else:

        cursor.execute("""
            INSERT INTO return_buses
            (
                bus_id,
                travel_date,
                departure_time,
                status
            )
            VALUES (?, ?, ?, ?)
        """, (
            bus_id,
            travel_date,
            departure_time,
            "AVAILABLE"
        ))

        print("\nLate bus added successfully!")

    connection.commit()
    connection.close()

    print(f"\nBus   : {bus_number}")
    print(f"Route : RIT Campus -> {route_name}")
    print(f"Date  : {travel_date}")
    print(f"Time  : {departure_time}")


# ==========================================
# VIEW DAILY RETURN SETUP
# ==========================================

def view_daily_return():

    print(
        "\n========== DAILY RETURN SETUP =========="
    )

    travel_date = input(
        "Enter date (DD-MM-YYYY): "
    ).strip()

    if not validate_date(travel_date):

        print("\nInvalid date.")
        return

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT buses.bus_number,
               buses.route_name,
               return_buses.departure_time
        FROM buses
        LEFT JOIN return_buses
        ON buses.id = return_buses.bus_id
        AND return_buses.travel_date = ?
        AND return_buses.status = 'AVAILABLE'
        ORDER BY buses.bus_number
    """, (travel_date,))

    buses = cursor.fetchall()
    connection.close()

    if not buses:

        print("\nNo buses available.")
        return

    print(
        f"\n========== RETURN BUSES - "
        f"{travel_date} =========="
    )

    for (
        bus_number,
        route_name,
        special_time
    ) in buses:

        if special_time:

            display_time = special_time

        else:

            display_time = "3:50 PM"

        print(
            f"{bus_number:<6} | "
            f"{route_name:<25} | "
            f"{display_time}"
        )

    print(
        "\nDefault return time: 3:50 PM"
    )

    print(
        "Only buses entered as late buses "
        "have a different time."
    )


# ==========================================
# REMOVE LATE BUS
# ==========================================

def remove_late_bus():

    print(
        "\n========== REMOVE LATE BUS =========="
    )

    travel_date = input(
        "Enter date (DD-MM-YYYY): "
    ).strip()

    if not validate_date(travel_date):

        print("\nInvalid date.")
        return

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT return_buses.id,
               buses.bus_number,
               buses.route_name,
               return_buses.departure_time
        FROM return_buses
        JOIN buses
        ON return_buses.bus_id = buses.id
        WHERE return_buses.travel_date = ?
        AND return_buses.status = 'AVAILABLE'
        ORDER BY return_buses.departure_time
    """, (travel_date,))

    late_buses = cursor.fetchall()

    if not late_buses:

        connection.close()

        print(
            "\nNo late buses found for this date."
        )

        return

    print(
        f"\n========== LATE BUSES - "
        f"{travel_date} =========="
    )

    for (
        return_id,
        bus_number,
        route_name,
        departure_time
    ) in late_buses:

        print(
            f"ID {return_id} | "
            f"{bus_number} | "
            f"{route_name} | "
            f"{departure_time}"
        )

    return_bus_id = input(
        "\nEnter ID to remove: "
    ).strip()

    cursor.execute("""
        SELECT id
        FROM return_buses
        WHERE id = ?
    """, (return_bus_id,))

    result = cursor.fetchone()

    if not result:

        connection.close()

        print("\nLate bus not found.")
        return

    cursor.execute("""
        DELETE FROM return_buses
        WHERE id = ?
    """, (return_bus_id,))

    connection.commit()
    connection.close()

    print("\nLate bus removed successfully!")

    print(
        "That bus will now automatically "
        "return to the default 3:50 PM."
    )


# ==========================================
# ADD / UPDATE EXAM AFTERNOON BUS
# ==========================================

def add_exam_afternoon_bus():

    print(
        "\n========== EXAM AFTERNOON BUS =========="
    )

    travel_date = input(
        "Enter exam date (DD-MM-YYYY): "
    ).strip()

    if not validate_date(travel_date):

        print("\nInvalid date.")
        print("Use format: DD-MM-YYYY")
        return

    connection = get_connection()
    cursor = connection.cursor()

    # ------------------------------------------
    # SHOW EXISTING EXAM AFTERNOON BUSES
    # ------------------------------------------

    cursor.execute("""
        SELECT exam_afternoon_buses.id,
               buses.bus_number,
               exam_afternoon_buses.departure_time,
               exam_afternoon_buses.destination
        FROM exam_afternoon_buses
        JOIN buses
        ON exam_afternoon_buses.bus_id = buses.id
        WHERE exam_afternoon_buses.travel_date = ?
        ORDER BY exam_afternoon_buses.departure_time
    """, (travel_date,))

    existing_buses = cursor.fetchall()

    print(
        f"\n========== EXAM BUSES - "
        f"{travel_date} =========="
    )

    if existing_buses:

        for (
            exam_id,
            bus_number,
            departure_time,
            destination
        ) in existing_buses:

            print(
                f"ID {exam_id} | "
                f"{bus_number} | "
                f"{departure_time} | "
                f"{destination}"
            )

    else:

        print("No exam afternoon buses added yet.")

    # ------------------------------------------
    # SHOW ALL BUSES
    # ------------------------------------------

    cursor.execute("""
        SELECT id, bus_number, route_name
        FROM buses
        ORDER BY bus_number
    """)

    buses = cursor.fetchall()

    print("\n========== BUS ROUTES ==========")

    for bus_id, bus_number, route_name in buses:

        print(
            f"{bus_number} | {route_name}"
        )

    # ------------------------------------------
    # SELECT BUS
    # ------------------------------------------

    bus_number = input(
        "\nEnter exam afternoon bus number: "
    ).strip().upper()

    cursor.execute("""
        SELECT id, route_name
        FROM buses
        WHERE bus_number = ?
    """, (bus_number,))

    bus = cursor.fetchone()

    if not bus:

        connection.close()

        print("\nBus not found.")
        return

    bus_id, route_name = bus

    # ------------------------------------------
    # DEPARTURE TIME
    # ------------------------------------------

    departure_time = input(
        "Enter departure time "
        "(Example: 1:30 PM): "
    ).strip()

    departure_time = normalize_time(
        departure_time
    )

    if not departure_time:

        connection.close()

        print("\nInvalid time.")
        return

    departure_minutes = time_to_minutes(
        departure_time
    )

    # Exam afternoon window:
    # 12:00 PM to 4:00 PM

    if (
        departure_minutes < 12 * 60
        or departure_minutes > 16 * 60
    ):

        connection.close()

        print(
            "\nExam afternoon buses must "
            "be between 12:00 PM and 4:00 PM."
        )

        return

    # ------------------------------------------
    # FINAL DESTINATION
    # ------------------------------------------

    destination = input(
        "Enter final destination: "
    ).strip()

    if not destination:

        connection.close()

        print("\nDestination is required.")
        return

    # ------------------------------------------
    # CHECK EXISTING BUS FOR THIS DATE
    # ------------------------------------------

    cursor.execute("""
        SELECT id
        FROM exam_afternoon_buses
        WHERE bus_id = ?
        AND travel_date = ?
    """, (
        bus_id,
        travel_date
    ))

    existing = cursor.fetchone()

    if existing:

        exam_id = existing[0]

        cursor.execute("""
            UPDATE exam_afternoon_buses
            SET departure_time = ?,
                destination = ?
            WHERE id = ?
        """, (
            departure_time,
            destination,
            exam_id
        ))

        print(
            "\nExam afternoon bus updated successfully!"
        )

    else:

        cursor.execute("""
            INSERT INTO exam_afternoon_buses
            (
                bus_id,
                travel_date,
                departure_time,
                destination
            )
            VALUES (?, ?, ?, ?)
        """, (
            bus_id,
            travel_date,
            departure_time,
            destination
        ))

        print(
            "\nExam afternoon bus added successfully!"
        )

    connection.commit()
    connection.close()

    print(
        f"\nBus         : {bus_number}"
    )

    print(
        f"Date        : {travel_date}"
    )

    print(
        f"Departure   : {departure_time}"
    )

    print(
        f"Destination : {destination}"
    )

    print(
        "\nNo boarding points are required "
        "for exam afternoon buses."
    )


# ==========================================
# VIEW EXAM AFTERNOON BUSES
# ==========================================

def view_exam_afternoon_buses():

    print(
        "\n========== VIEW EXAM AFTERNOON BUSES =========="
    )

    travel_date = input(
        "Enter exam date (DD-MM-YYYY): "
    ).strip()

    if not validate_date(travel_date):

        print("\nInvalid date.")
        return

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT exam_afternoon_buses.id,
               buses.bus_number,
               exam_afternoon_buses.departure_time,
               exam_afternoon_buses.destination
        FROM exam_afternoon_buses
        JOIN buses
        ON exam_afternoon_buses.bus_id = buses.id
        WHERE exam_afternoon_buses.travel_date = ?
        ORDER BY exam_afternoon_buses.departure_time
    """, (travel_date,))

    buses = cursor.fetchall()

    connection.close()

    if not buses:

        print(
            "\nNo exam afternoon buses "
            "configured for this date."
        )

        return

    print(
        f"\n========== EXAM AFTERNOON BUSES - "
        f"{travel_date} =========="
    )

    for (
        exam_id,
        bus_number,
        departure_time,
        destination
    ) in buses:

        print(
            "\n----------------------------------------"
        )

        print(
            f"Bus         : {bus_number}"
        )

        print(
            f"Departure   : {departure_time}"
        )

        print(
            f"Destination : {destination}"
        )


# ==========================================
# REMOVE EXAM AFTERNOON BUS
# ==========================================

def remove_exam_afternoon_bus():

    print(
        "\n========== REMOVE EXAM AFTERNOON BUS =========="
    )

    travel_date = input(
        "Enter exam date (DD-MM-YYYY): "
    ).strip()

    if not validate_date(travel_date):

        print("\nInvalid date.")
        return

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT exam_afternoon_buses.id,
               buses.bus_number,
               exam_afternoon_buses.departure_time,
               exam_afternoon_buses.destination
        FROM exam_afternoon_buses
        JOIN buses
        ON exam_afternoon_buses.bus_id = buses.id
        WHERE exam_afternoon_buses.travel_date = ?
        ORDER BY exam_afternoon_buses.departure_time
    """, (travel_date,))

    buses = cursor.fetchall()

    if not buses:

        connection.close()

        print(
            "\nNo exam afternoon buses found "
            "for this date."
        )

        return

    print(
        f"\n========== EXAM BUSES - "
        f"{travel_date} =========="
    )

    for (
        exam_id,
        bus_number,
        departure_time,
        destination
    ) in buses:

        print(
            f"ID {exam_id} | "
            f"{bus_number} | "
            f"{departure_time} | "
            f"{destination}"
        )

    exam_id = input(
        "\nEnter ID to remove: "
    ).strip()

    cursor.execute("""
        SELECT id
        FROM exam_afternoon_buses
        WHERE id = ?
    """, (exam_id,))

    result = cursor.fetchone()

    if not result:

        connection.close()

        print(
            "\nExam afternoon bus not found."
        )

        return

    cursor.execute("""
        DELETE FROM exam_afternoon_buses
        WHERE id = ?
    """, (exam_id,))

    connection.commit()
    connection.close()

    print(
        "\nExam afternoon bus removed successfully!"
    )

def exam_afternoon_menu():
    while True:
        print(
            "\n======================================"
        )

        print(
            "       EXAM AFTERNOON BUS MANAGEMENT"
        )

        print(
            "======================================"
        )

        print(
            "\n1. Add / Update Exam Afternoon Bus"
        )

        print(
            "2. View Exam Afternoon Buses"
        )

        print(
            "3. Remove Exam Afternoon Bus"
        )

        print(
            "4. Back to Admin Menu"
        )

        choice = input(
            "\nEnter your choice: "
        ).strip()

        if choice == "1":

            add_exam_afternoon_bus()

        elif choice == "2":

            view_exam_afternoon_buses()

        elif choice == "3":

            remove_exam_afternoon_bus()

        elif choice == "4":

            break

        else:

            print(
                "\nInvalid choice. Please try again."
            )


# ==========================================
# ADMIN MENU
# ==========================================

def admin_menu():

    while True:

        print(
            "\n======================================"
        )

        print(
            "          BUSMATE ADMIN"
        )

        print(
            "======================================"
        )

        print(
            "\n1. View Bus Routes"
        )

        print(
            "2. Manage Late Buses")
        print(
            "3. View Daily Return Setup"
        )

        print(
            "4. Remove Late Bus"
        )

        print(
            "5. Manage Exam Afternoon Buses"
        )

        print(
            "6. Exit"
        )

        choice = input(
            "\nEnter your choice: "
        ).strip()

        if choice == "1":

            view_routes()

        elif choice == "2":

            add_late_bus()

        elif choice == "3":

            view_daily_return()

        elif choice == "4":

            remove_late_bus()

        elif choice == "5":

            exam_afternoon_menu()

        elif choice == "6":

            print(
                "\nExiting Admin Panel..."
            )

            break

        else:

            print(
                "\nInvalid choice. Please try again."
            )

    # ==========================================
    # EXAM AFTERNOON BUS MENU
    # ==========================================


    # ==========================================
    # START PROGRAM
    # ==========================================

if __name__ == "__main__":

    if admin_login():

        admin_menu()