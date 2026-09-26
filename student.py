import sqlite3
import hashlib
import hmac
from datetime import datetime


DATABASE = "busmate.db"


def get_connection():
    return sqlite3.connect(DATABASE)


# ==========================================
# STUDENT TABLE
# ==========================================

def setup_student_table():

    connection = get_connection()
    cursor = connection.cursor()

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
# STUDENT REGISTRATION
# ==========================================

def student_registration():

    print("\n======================================")
    print("       STUDENT REGISTRATION")
    print("======================================")

    name = input("\nEnter your name: ").strip()
    student_id = input("Enter student ID: ").strip()
    email = input("Enter email: ").strip()
    password = input("Enter password: ").strip()

    if not name or not student_id or not email or not password:

        print("\nAll fields are required.")
        return

    salt = b"busmate_student_salt_2026"

    password_hash = hash_password(
        password,
        salt
    )

    connection = get_connection()
    cursor = connection.cursor()

    try:

        cursor.execute("""
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

        print("\nRegistration successful!")
        print(f"Welcome, {name}!")

    except sqlite3.IntegrityError:

        print(
            "\nStudent ID or email already registered."
        )

    connection.close()


# ==========================================
# STUDENT LOGIN
# ==========================================

def student_login():

    print("\n======================================")
    print("          STUDENT LOGIN")
    print("======================================")

    login_id = input(
        "\nEnter Student ID or Email: "
    ).strip()

    password = input(
        "Enter Password: "
    ).strip()

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT id,
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
    ))

    student = cursor.fetchone()

    connection.close()

    if not student:

        print(
            "\nInvalid Student ID/Email or password."
        )

        return None

    (
        student_db_id,
        student_id,
        name,
        email,
        stored_hash,
        salt
    ) = student

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
            "id": student_db_id,
            "student_id": student_id,
            "name": name,
            "email": email
        }

    print(
        "\nInvalid Student ID/Email or password."
    )

    return None


# ==========================================
# VIEW BUS ROUTES
# ==========================================

def view_routes():

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

    print("\n========== BUS ROUTES ==========")

    if not buses:

        print("\nNo bus routes available.")
        return

    for (
        bus_id,
        bus_number,
        route_name
    ) in buses:

        print(
            f"{bus_number} | "
            f"{route_name}"
        )


# ==========================================
# TIME TO MINUTES
# ==========================================

def time_to_minutes(time_text):

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

            return (
                time_value.hour * 60
                + time_value.minute
            )

        except ValueError:

            continue

    return None


# ==========================================
# MINUTES TO TIME
# ==========================================

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


# ==========================================
# VIEW MORNING ROUTE
# ==========================================

def view_morning_route():

    print(
        "\n========== MORNING ROUTE =========="
    )

    bus_number = input(
        "Enter bus number (Example: R01): "
    ).strip().upper()

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT id,
               route_name
        FROM buses
        WHERE bus_number = ?
    """, (bus_number,))

    bus = cursor.fetchone()

    if not bus:

        connection.close()

        print("\nBus not found.")

        return

    bus_id, route_name = bus

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

    print(
        f"\n========== {bus_number} =========="
    )

    print(
        f"Morning Route : "
        f"{route_name} -> RIT Campus"
    )

    print("\nBoarding Points:")

    if not stops:

        print(
            "No morning boarding points available."
        )

        return

    for (
        stop_name,
        stop_time,
        stop_order
    ) in stops:

        print(
            f"{stop_order}. "
            f"{stop_name} - "
            f"{stop_time}"
        )


# ==========================================
# CALCULATE RETURN TIMES
# ==========================================

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

    # Reverse morning route
    #
    # Morning:
    # Route -> Stop 1 -> Stop 2 -> RIT
    #
    # Return:
    # RIT -> Stop 2 -> Stop 1 -> Route

    reversed_stops = list(
        reversed(morning_stops)
    )

    estimated_times = []

    current_minutes = departure_minutes

    first_stop_name = (
        reversed_stops[0][0]
    )

    estimated_times.append(
        (
            first_stop_name,
            minutes_to_time(
                current_minutes
            )
        )
    )

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

        previous_morning_time = (
            time_to_minutes(
                previous_stop[1]
            )
        )

        current_morning_time = (
            time_to_minutes(
                current_stop[1]
            )
        )

        gap = 0

        if (
            previous_morning_time is not None
            and current_morning_time is not None
        ):

            gap = abs(
                previous_morning_time
                - current_morning_time
            )

        if gap <= 0:

            gap = 2

        current_minutes += gap

        estimated_times.append(
            (
                current_stop[0],
                minutes_to_time(
                    current_minutes
                )
            )
        )

    return estimated_times


# ==========================================
# VIEW RETURN BUS
# ==========================================

def view_return_bus():

    print(
        "\n========== RETURN BUS =========="
    )

    travel_date = input(
        "Enter date (DD-MM-YYYY): "
    ).strip()

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT buses.id,
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
    ))
    buses = cursor.fetchall()

    if not buses:

        connection.close()

        print(
            "\nNo bus routes available."
        )

        return

    print(
        f"\n========== RETURN BUSES - "
        f"{travel_date} =========="
    )

    for (
        bus_id,
        bus_number,
        route_name,
        special_departure_time
    ) in buses:

        # Default return time
        departure_time = "3:50 PM"

        # Admin late-bus override
        if special_departure_time:

            departure_time = (
                special_departure_time
            )

        print(
            "\n----------------------------------------"
        )

        print(
            f"Bus       : "
            f"{bus_number}"
        )

        print(
            f"Route     : "
            f"RIT Campus -> {route_name}"
        )

        print(
            f"Departure : "
            f"{departure_time}"
        )

        # --------------------------------------
        # GET MORNING BOARDING POINTS
        # --------------------------------------

        cursor.execute("""
            SELECT stop_name,
                   stop_time,
                   stop_order
            FROM stops
            WHERE bus_id = ?
            AND direction = 'MORNING'
            ORDER BY stop_order
        """, (bus_id,))

        morning_stops = cursor.fetchall()

        print("\nReturn Stops:")

        if not morning_stops:

            print(
                "No boarding points available."
            )

            continue

        # --------------------------------------
        # CALCULATE RETURN TIMES
        # --------------------------------------

        return_times = (
            calculate_return_times(
                departure_time,
                morning_stops
            )
        )

        if return_times is None:

            for index, stop in enumerate(
                reversed(morning_stops),
                start=1
            ):

                print(
                    f"{index}. "
                    f"{stop[0]} - Approximate"
                )

            continue

        for index, (
            stop_name,
            estimated_time
        ) in enumerate(
            return_times,
            start=1
        ):

            print(
                f"{index}. "
                f"{stop_name} "
                f"- ~{estimated_time}"
            )

    connection.close()

    print(
        "\nNote: Return stop times are approximate."
    )

    print(
        "Actual arrival time may vary due to traffic."
    )


# ==========================================
# SEARCH BUS BY BOARDING POINT
# ==========================================

def search_bus():

    print(
        "\n========== SEARCH BUS BY "
        "BOARDING POINT =========="
    )

    stop_name = input(
        "Enter your boarding point: "
    ).strip()

    if not stop_name:

        print(
            "\nPlease enter a boarding point."
        )

        return

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT buses.bus_number,
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
    ))

    results = cursor.fetchall()

    connection.close()

    if not results:

        print(
            "\nSorry! No bus found "
            "for this boarding point."
        )

        return

    print(
        "\n========== BUSES FOUND =========="
    )

    for (
        bus_number,
        route_name,
        stop,
        stop_time
    ) in results:

        print(
            "\n----------------------------------------"
        )

        print(
            f"Bus Number : "
            f"{bus_number}"
        )

        print(
            f"Route      : "
            f"{route_name} -> RIT Campus"
        )

        print(
            f"Boarding   : "
            f"{stop}"
        )

        print(
            f"Time       : "
            f"{stop_time}"
        )
# ==========================================
# VIEW EXAM AFTERNOON BUSES
# ==========================================

def view_exam_afternoon_buses():

    print(
        "\n========== EXAM AFTERNOON BUSES =========="
    )

    travel_date = input(
        "Enter exam date (DD-MM-YYYY): "
    ).strip()

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT buses.bus_number,
               buses.route_name,
               exam_afternoon_buses.departure_time,
               exam_afternoon_buses.destination
        FROM exam_afternoon_buses

        JOIN buses
        ON exam_afternoon_buses.bus_id = buses.id

        WHERE exam_afternoon_buses.travel_date = ?

        ORDER BY exam_afternoon_buses.departure_time,
                 buses.bus_number
    """, (travel_date,))

    buses = cursor.fetchall()

    connection.close()

    if not buses:

        print(
            "\nNo exam afternoon buses "
            "available for this date."
        )

        return

    print(
        f"\n========== EXAM BUSES - "
        f"{travel_date} =========="
    )

    for (
        bus_number,
        route_name,
        departure_time,
        destination
    ) in buses:

        print(
            "\n----------------------------------------"
        )

        print(
            f"Bus Number : {bus_number}"
        )

        print(
            f"Departure  : {departure_time}"
        )

        print(
            f"Destination: {destination}"
        )

        print(
            f"Route      : RIT Campus -> {destination}"
        )

        print(
            "Boarding Points: Not applicable"
        )

# ==========================================
# STUDENT MENU
# ==========================================

def student_menu(student):

    while True:

        print(
            "\n======================================"
        )

        print(
            "          BUSMATE STUDENT"
        )

        print(
            "======================================"
        )

        print(
            f"\nWelcome, {student['name']}!"
        )

        print(
            "\n1. View Bus Routes"
        )

        print(
            "2. View Morning Route"
        )

        print(
            "3. View Return Bus"
        )

        print(
            "4. Search Bus by Boarding Point"
        )

        print(
            "5. View Exam Afternoon Buses"
        )
        print(
            "6.Logout"
        )

        choice = input(
            "\nEnter your choice: "
        ).strip()

        if choice == "1":

            view_routes()

        elif choice == "2":

            view_morning_route()

        elif choice == "3":

            view_return_bus()

        elif choice == "4":

            search_bus()

        elif choice == "5":

            print(
                view_exam_afternoon_buses()
            )
        elif choice == "6":

            print(
                "\nLogging out..."
            )

            break

        else:

            print(
                "\nInvalid choice."
            )


# ==========================================
# START STUDENT PORTAL
# ==========================================

def main():

    setup_student_table()

    while True:

        print(
            "\n======================================"
        )

        print(
            "          BUSMATE STUDENT"
        )

        print(
            "======================================"
        )

        print(
            "\n1. Student Registration"
        )

        print(
            "2. Student Login"
        )

        print(
            "3. Exit"
        )

        choice = input(
            "\nEnter your choice: "
        ).strip()

        if choice == "1":

            student_registration()

        elif choice == "2":

            student = student_login()

            if student:

                student_menu(student)

        elif choice == "3":

            print(
                "\nExiting Student Portal..."
            )

            break

        else:

            print(
                "\nInvalid choice."
            )


if __name__ == "__main__":

    main()