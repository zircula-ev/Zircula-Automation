# Zircula Booking Automation

Diese Automation überträgt Buchungsbestätigungen und Stornierungen aus einem
IMAP-Postfach in den gemeinsamen Nextcloud-Kalender **Ausleihen & Buchungen**.

Der frühere Tagesdigest zu Slack oder Nextcloud Talk gehört nicht mehr zum
Zielbild. IntraVox zeigt Kalenderinhalte direkt an.

## Datenfluss

1. Ungelesene Buchungsmail aus dem konfigurierten IMAP-Ordner laden.
2. Absender anhand einer Domain-Allowlist als MyTurn oder CommonsBooking/Lale
   einordnen.
3. Buchungsdaten parsen.
4. Unter einer stabilen UID einen iCalendar-Termin per CalDAV anlegen oder
   aktualisieren.
5. Bei einer Stornierung denselben Termin löschen.
6. Erst nach erfolgreichem CalDAV-Schritt die Mail als gelesen markieren.

Dadurch sind Wiederholungen idempotent und Fehler bleiben für den nächsten Lauf
sichtbar. SQLite und ein zusätzlicher Talk-/Slack-Versand sind nicht notwendig.

## Sicherheit

- `.env` und das Nextcloud-App-Passwort niemals committen.
- Der technische Nextcloud-Account ist `zirculaheute`.
- Das App-Passwort benötigt nur Zugriff auf den freigegebenen Zielkalender.
- Nur explizit konfigurierte Absenderdomains werden verarbeitet.
- Fehlerhafte Mails bleiben ungelesen und werden nicht still verworfen.

## Lokaler Test

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m unittest -v
```

## Konfiguration

```bash
cp .env.example .env
```

Anschließend in `.env` setzen:

- IMAP-Zugang
- tatsächliche Absenderdomains von MyTurn und CommonsBooking
- Nextcloud-Benutzer `zirculaheute`
- dessen App-Passwort
- die vollständige CalDAV-Collection-URL des Kalenders
  **Ausleihen & Buchungen**

Die Collection-URL wird vor dem ersten schreibenden Test mit `PROPFIND`
verifiziert.

## Ausführung

```bash
.venv/bin/python booking_importer.py
```

Für den Serverbetrieb wird ein versionierter systemd-One-Shot-Dienst mit Timer
im Infrastructure-Repository ergänzt. Vor der Aktivierung erfolgt ein Test mit
einer einzelnen echten Mail und die Kontrolle des erzeugten Kalendertermins.
