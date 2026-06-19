import sqlite3

conn = sqlite3.connect("bookings.db")

conn.execute("""
CREATE TABLE IF NOT EXISTS bookings (
    reservation_id TEXT PRIMARY KEY,
    source TEXT,
    status TEXT,
    booking_date TEXT,
    item TEXT,
    notes TEXT,
    raw_subject TEXT,
    imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

conn.commit()
conn.close()

print("Database initialized.")
