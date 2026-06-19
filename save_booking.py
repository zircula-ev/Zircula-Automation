import sqlite3


def save_booking(data):

    conn = sqlite3.connect("bookings.db")

    conn.execute("""
INSERT OR REPLACE INTO bookings (
    reservation_id,
    source,
    status,
    booking_date,
    item,
    notes,
    raw_subject,
    resource_type,
    room,
    start_time,
    end_time,
    pickup_time,
    return_time,
    return_date,
    location
)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
""", (
    data.get("reservation_id"),
    data.get("source", "myturn"),
    data.get("status"),
    data.get("booking_date"),
    data.get("item"),
    data.get("notes"),
    data.get("raw_subject"),
    data.get("resource_type"),
    data.get("room"),
    data.get("start_time"),
    data.get("end_time"),
    data.get("pickup_time"),
    data.get("return_time"),
    data.get("return_date"),
    data.get("location")
))

    conn.commit()
    conn.close()
