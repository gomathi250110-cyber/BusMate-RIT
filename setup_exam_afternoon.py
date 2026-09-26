import sqlite3


DATABASE = "busmate.db"


connection = sqlite3.connect(DATABASE)
cursor = connection.cursor()


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


connection.commit()
connection.close()


print("Exam afternoon bus table ready!")