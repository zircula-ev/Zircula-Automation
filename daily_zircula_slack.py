import requests
from ics import Calendar
from datetime import datetime
import pytz
import os
import sqlite3
from dotenv import load_dotenv
ICS_URLS = [
    "https://nextcloud.zircula.org/remote.php/dav/public-calendars/2QANrakA3wBbyxmt?export",
    "https://pretix.eu/werk/events/ical/?locale=de",
    "https://easyverein.com/event/subscription/Zolli/20c60380-63bb-42ea-95cd-8b44358f3330/calendar.ics"
]
load_dotenv()

SLACK_WEBHOOK = os.getenv("SLACK_WEBHOOK")

if not SLACK_WEBHOOK:
    raise Exception("Webhook ist NICHT gesetzt!")

TIMEZONE = "Europe/Berlin"

tz = pytz.timezone(TIMEZONE)
now = datetime.now(tz)
today = now.date()
today_str = today.strftime("%d.%m.%Y")

def get_today_bookings():

    conn = sqlite3.connect(
        "/home/timo/booking-import/bookings.db"
    )

    rows = conn.execute("""
        SELECT
            resource_type,
            item,
            room,
            start_time,
            end_time,
            notes,
            pickup_time,
            return_time,
            booking_date,
            return_date,
            location
        FROM bookings
        WHERE (
            booking_date = ?
            OR return_date = ?
        )
        AND status = 'confirmed'
    """, (today_str, today_str)).fetchall()

    conn.close()

    return rows

events_today = []

bookings_today = get_today_bookings()

start_of_day = tz.localize(datetime.combine(today, datetime.min.time()))
end_of_day = tz.localize(datetime.combine(today, datetime.max.time()))

for url in ICS_URLS:
    try:
        response = requests.get(url, timeout=10)
        response.encoding = "utf-8"
        cal = Calendar(response.text)

        for event in cal.events:
            if not event.begin:
                continue

            event_time = event.begin.to(TIMEZONE).datetime

            if start_of_day <= event_time <= end_of_day:
                events_today.append({
                    "name": event.name,
                    "time": event_time.strftime("%H:%M"),
                    "location": event.location or "",
                    "url": event.url or ""
                })

    except Exception as e:
        print(f"Fehler bei {url}: {e}")

events_today.sort(key=lambda x: x["time"])

seen = set()
unique_events = []

for e in events_today:
    key = (e["name"], e["time"])
    if key not in seen:
        seen.add(key)
        unique_events.append(e)

if unique_events:
    text = "📅 *Zircula – Heute:*\n\n"

    for e in unique_events:
        text += f"• *{e['time']}* – {e['name']}\n"

        if e["location"]:
            text += f"   📍 {e['location']}\n"

        if e["url"]:
            text += f"   🔗 {e['url']}\n"

else:
    text = "📅 *Zircula – Heute:*\n\nKeine Termine 🎉"

if bookings_today:

    room_bookings = [
        b for b in bookings_today
        if b[0] == "room"
    ]

    tool_bookings = [
        b for b in bookings_today
        if b[0] == "tool"
    ]

    bike_bookings = [
        b for b in bookings_today
        if b[0] == "cargo_bike"
    ]

    if room_bookings:

        text += "\n🏠 *Raumbuchungen*\n\n"

    for b in room_bookings:

        text += f"• {b[2]}\n"

        text += f"  🕒 {b[3]}–{b[4]}\n"

        if b[5]:
            text += f"  📝 {b[5]}\n"

        text += "\n"

    if tool_bookings:

        text += "\n🛠️ *Werkzeugausleihe*\n\n"

    for b in tool_bookings:

        text += f"• {b[1]}\n"

        if b[8] == today_str:
            text += "  🟢 Ausgabe heute\n"

        if b[9] == today_str:
            text += "  🔁 Rückgabe heute\n"

        if b[6]:
            text += f"  🕒 Abholung {b[6]}\n"

        if b[5]:
            text += f"  📝 {b[5]}\n"

        text += "\n"

    if bike_bookings:

        text += "\n🚲 *Lastenräder*\n\n"

        for b in bike_bookings:

            text += f"• {b[1]}\n"

            if b[8] == today_str:
                text += "  🟢 Ausgabe heute\n"

            if b[9] == today_str:
                text += "  🔁 Rückgabe heute\n"

            if b[6]:
                text += f"  🕒 Abholung: {b[6]}\n"

            if b[7]:
                text += f"  🔄 Rückgabe: {b[7]}\n"

            if b[10]:
                text += f"  📍 {b[10]}\n"

            text += "\n"

payload = {"text": text}

response = requests.post(SLACK_WEBHOOK, json=payload)

response.raise_for_status()

print("✅ Zircula Tagesübersicht gesendet")
