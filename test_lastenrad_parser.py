from parser_lastenrad import parse_lastenrad

subject = (
    "Deine Buchung von Siebträger Tandem "
    "(Hase Pino) am Standort WERK. "
    "von 19. Juni 2026 bis 20. Juni 2026"
)

text = """
Hallo Timo,

vielen Dank für deine Buchung von Siebträger Tandem
(Hase Pino) von 19. Juni 2026 bis 20. Juni 2026.

Abholung: 19. Juni 2026 0:00 - 23:59
Rückgabe: 20. Juni 2026 0:00 - 0:00

Standort
WERK.
Bürgermeister-Smidt-Straße 218
27568 Bremerhaven
"""

data = parse_lastenrad(text, subject)

print(data)
