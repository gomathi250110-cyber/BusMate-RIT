import sqlite3
from datetime import datetime


DATABASE = "busmate.db"


def get_connection():
    return sqlite3.connect(DATABASE)


# ==========================================
# VIEW ALL BUS ROUTES
# ==========================================

def view_routes():

    print("\n========== RIT BUS ROUTES ==========")

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT bus_number, route_name
        FROM buses
        ORDER BY bus_number
    """)

    buses = cursor.fetchall()
    connection.close()

    if not buses:
        print("\nNo bus routes available.")
        return

    for bus_number, route_name in buses:

        print(
            f"{bus_number} | "
            f"{route_name} -> RIT Campus"
        )


# ==========================================
# VIEW MORNING ROUTE
# ==========================================

def view_morning_route():

    print("\n========== MORNING ROUTE ==========")

    bus_number = input(
        "Enter bus number (Example: R01): "
    ).strip().upper()

    connection = get_connection()
    cursor = connection.cursor()

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
        f"\n========== {bus_number} - "
        f"{route_name} =========="
    )

    print(
        f"Direction: "
        f"{route_name} -> RIT Campus"
    )

    print("\nStops:")

    if not stops:

        print(
            "No morning stops available."
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
# CONVERT TIME TO MINUTES
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
# FORMAT MINUTES TO TIME
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
# CALCULATE RETURN STOP TIMES
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

    # Reverse morning stops.
    #
    # Example:
    #
    # Morning:
    # Ennore
    # Wimco
    # Ajax
    # ...
    # RIT Campus
    #
    # Return:
    # RIT Campus
    # Ajax
    # Wimco
    # Ennore
    #
    reversed_stops = list(
        reversed(morning_stops)
    )

    estimated_times = []

    current_minutes = departure_minutes

    # ------------------------------------------
    # RIT Campus
    # ------------------------------------------

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

    # ------------------------------------------
    # Calculate reverse travel gaps
    # ------------------------------------------

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

        # Fallback if time is missing
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

    print("\n========== RETURN BUS ==========")

    travel_date = input(
        "Enter date (DD-MM-YYYY): "
    ).strip()

    connection = get_connection()
    cursor = connection.cursor()

    # ------------------------------------------
    # GET ALL BUSES
    #
    # Every bus is automatically 3:50 PM.
    # Late buses stored in return_buses
    # will override 3:50 PM.
    # ------------------------------------------

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

        ORDER BY buses.bus_number
    """, (travel_date,))

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

    # ------------------------------------------
    # DISPLAY EVERY BUS
    # ------------------------------------------

    for (
        bus_id,
        bus_number,
        route_name,
        special_departure_time
    ) in buses:

        # --------------------------------------
        # DEFAULT TIME
        # --------------------------------------

        departure_time = "3:50 PM"

        # --------------------------------------
        # LATE BUS OVERRIDE
        # --------------------------------------

        if special_departure_time:

            departure_time = (
                special_departure_time
            )

        print(
            "\n----------------------------------------"
        )

        print(
            f"Bus        : "
            f"{bus_number}"
        )

        print(
            f"Route      : "
            f"RIT Campus -> "
            f"{route_name}"
        )

        print(
            f"Departure  : "
            f"{departure_time}"
        )

        # --------------------------------------
        # GET MORNING STOPS
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
                "No stops available."
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
                    f"{stop[0]} - "
                    f"Approximate"
                )

            continue

        # --------------------------------------
        # DISPLAY RETURN STOPS
        # --------------------------------------

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
# SEARCH MORNING BUS BY BOARDING POINT
# ==========================================

def search_bus():

    print(
        "\n========== SEARCH MORNING BUS =========="
    )

    stop_name = input(
        "Enter your boarding point: "
    ).strip()

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
    """, (f"%{stop_name}%",))

    results = cursor.fetchall()

    connection.close()

    if not results:

        print(
            "\nSorry! No bus found."
        )

        return

    print(
        "\n========== AVAILABLE BUSES =========="
    )

    for (
        bus_number,
        route_name,
        stop,
        stop_time
    ) in results:

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

        print(
            "-" * 40
        )


# ==========================================
# MAIN MENU
# ==========================================

def main():

    while True:

        print(
            "\n======================================"
        )

        print(
            "          WELCOME TO BUSMATE"
        )

        print(
            "======================================"
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
            "5. Exit"
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
                "\nThank you for using BusMate!"
            )

            break

        else:

            print(
                "\nInvalid choice. "
                "Please try again."
            )


# ==========================================
# START PROGRAM
# ==========================================

if __name__ == "__main__":

    main()