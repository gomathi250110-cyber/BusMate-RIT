import sqlite3

con = sqlite3.connect("busmate.db")

print("\nTABLES:")
print(
    con.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type='table'
    """).fetchall()
)

print("\nBUSES:")
print(
    con.execute("""
        SELECT * FROM buses
    """).fetchall()
)

print("\nSTOPS:")
print(
    con.execute("""
        SELECT * FROM stops
    """).fetchall()
)

print("\nRETURN BUSES:")
print(
    con.execute("""
        SELECT * FROM return_buses
    """).fetchall()
)

print("\nEXAM BUSES:")
print(
    con.execute("""
        SELECT * FROM exam_afternoon_buses
    """).fetchall()
)

con.close()