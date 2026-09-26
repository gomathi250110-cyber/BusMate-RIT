import sqlite3

DATABASE = "busmate.db"


def add_evening_stops(cursor, bus_number, stops):

    cursor.execute(
        "SELECT id FROM buses WHERE bus_number = ?",
        (bus_number,)
    )

    result = cursor.fetchone()

    if result is None:
        print(f"{bus_number} not found")
        return

    bus_id = result[0]

    for order, (stop_name, stop_time) in enumerate(stops, start=1):

        cursor.execute(
            """
            INSERT INTO stops
            (bus_id, stop_name, stop_time, stop_order, direction)
            VALUES (?, ?, ?, ?, ?)
            """,
            (bus_id, stop_name, stop_time, order, "EVENING")
        )


def add_evening_routes():

    connection = sqlite3.connect(DATABASE)
    cursor = connection.cursor()

    # R01 - Ennore
    r01 = [
        ("RIT Campus", "4:30 PM"),
        ("Toll Gate", "5:20 PM"),
        ("Raja Kadai", "5:22 PM"),
        ("Ellaimman Koil", "5:24 PM"),
        ("Theradi", "5:26 PM"),
        ("Thiruvortiyur Market", "5:28 PM"),
        ("Periyar Nagar", "5:33 PM"),
        ("Ajax", "5:36 PM"),
        ("Wimco Market", "5:41 PM"),
        ("Ennore Lift Gate", "5:46 PM")
    ]

    # R02 - Triplicane
    r02 = [
        ("RIT Campus", "4:30 PM"),
        ("Maduravoyal Murugan Store", "5:10 PM"),
        ("NSK", "5:13 PM"),
        ("Arumbakkam Panchaliamman Koil", "5:15 PM"),
        ("Anna Arch", "5:18 PM"),
        ("Choolaimedu Bus Stop", "5:23 PM"),
        ("Choolaimedu Subway", "5:25 PM"),
        ("Sterling Road", "5:28 PM"),
        ("Royapettah New College", "5:32 PM"),
        ("Meersahibpet Market", "5:36 PM"),
        ("Ice House Police Station", "5:39 PM"),
        ("Triplicane High Road", "5:42 PM"),
        ("D1 Police Station", "5:46 PM"),
        ("Chintadripet Post Office", "5:51 PM")
    ]

    # R07 - Santhome
    r07 = [
        ("RIT Campus", "4:30 PM"),
        ("Ayyapanthangal", "5:05 PM"),
        ("Porur", "5:08 PM"),
        ("Chennai Trade Centre", "5:13 PM"),
        ("Butt Road", "5:25 PM"),
        ("Guindy", "5:31 PM"),
        ("Saidapet Bus Stop", "5:33 PM"),
        ("Saidapet Vetrinary Hospital", "5:38 PM"),
        ("Nanthanam Signal", "5:43 PM"),
        ("SIET College", "5:48 PM"),
        ("P.S.Sivasamy Road", "5:53 PM"),
        ("Luz Corner", "5:55 PM"),
        ("Kutchery Road", "6:00 PM"),
        ("Pattinapakkam", "6:05 PM"),
        ("Mandaveli Bus Depot", "6:10 PM")
    ]

    # R11 - Chengalpattu
    r11 = [
        ("RIT Campus", "4:30 PM"),
        ("Kattankulathur", "5:20 PM"),
        ("MM Nagar Bus Stand", "5:23 PM"),
        ("MM Nagar Samiyar Gate", "5:28 PM"),
        ("SP Kovil", "5:33 PM"),
        ("Chengalpattu Bypass", "5:45 PM"),
        ("Old Bus Stand", "5:48 PM"),
        ("New Bus Stand", "5:50 PM"),
        ("Chengalpattu Rattinakinaru", "5:53 PM")
    ]

    add_evening_stops(cursor, "R01", r01)
    add_evening_stops(cursor, "R02", r02)
    add_evening_stops(cursor, "R07", r07)
    add_evening_stops(cursor, "R11", r11)

    connection.commit()
    connection.close()

    print("RIT evening routes added successfully!")


if __name__ == "__main__":
    add_evening_routes()