import sqlite3

DATABASE = "busmate.db"


def create_database():

    connection = sqlite3.connect(DATABASE)
    cursor = connection.cursor()

    # ==========================================
    # BUS ROUTES TABLE
    # ==========================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS buses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bus_number TEXT NOT NULL UNIQUE,
            route_name TEXT NOT NULL
        )
    """)

    # ==========================================
    # BUS STOPS TABLE
    # ==========================================

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

    # ==========================================
    # RETURN BUSES TABLE
    # ==========================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS return_buses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bus_id INTEGER NOT NULL,
            travel_date TEXT NOT NULL,
            departure_time TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'AVAILABLE',
            FOREIGN KEY (bus_id) REFERENCES buses(id)
        )
    """)

    # ==========================================
    # NOTICES
    # ==========================================

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

    connection.commit()
    connection.close()

    print("BusMate database created successfully!")


if __name__ == "__main__":
    create_database()