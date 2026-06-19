from save_booking import save_booking

booking = {
    "reservation_id": "846828",
    "status": "cancelled",
    "booking_date": "19.06.2026",
    "item": "Besprechungsraum (09:30-15:00)",
    "notes": "Buchung Andrea 10-12 Uhr",
    "raw_subject": "Reservation request canceled - Timo Hecken"
}

save_booking(booking)

print("Saved.")
