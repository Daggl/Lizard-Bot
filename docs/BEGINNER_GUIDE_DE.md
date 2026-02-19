BEGINNER GUIDE — Einfache Schritt‑für‑Schritt Anleitung (Deutsch)
=============================================================

Diese Anleitung führt dich durch das Starten und die grundlegende Nutzung des Bots. Keine Programmierkenntnisse nötig — folge einfach den Schritten.

1) Voraussetzungen
-------------------
- Windows-PC mit installiertem Python 3.10+ (du hast Python bereits installiert).
- Grundlegende PowerShell‑Kenntnisse: Dateien öffnen, Befehle kopieren und einfügen.

2) Projektordner verstehen
--------------------------
- Der Bot liegt im Ordner, den du geöffnet hast: `C:\Users\mahoe\Documents\DC Bot`
- Wichtige Ordner/Dateien:
  - `bot.py` → Startet den Bot.
  - `start.ps1` / `start.bat` → Einfache Startskripte (PowerShell / CMD).
  - `config.example.json` → Vorlage für server‑/kanal‑IDs. Beim ersten Start werden daraus Dateien in `config/` erzeugt.
  - `data/db/` → Hier liegen die SQLite‑Datenbanken (z. B. `logs.db`, `tickets.db`).
  - `data/tickets/transcripts/` → Ticket‑Transkripte (Textdateien) werden hier gespeichert.

3) Bot starten (einfachste Methode)
---------------------------------
Öffne PowerShell, wechsle in den Projektordner und starte den Bot:

```powershell
cd "C:\Users\mahoe\Documents\DC Bot"
.\n+# Einmalig (wenn du die Abhängigkeiten noch nicht installiert hast):
python -m pip install -r requirements.txt

# Bot starten (zeigt Ausgaben in der Konsole):
python bot.py
```

Alternativ: Doppel‑Klick auf `start.bat` oder `.\start.ps1` (PowerShell). `start.ps1 -Detach` startet den Bot im Hintergrund.

4) Token eintragen (wichtig!)
-----------------------------
Der Bot braucht ein Token, damit er sich bei Discord einloggen kann.

- Erstelle eine Datei namens `.env` im Projekt‑Ordner `C:\Users\mahoe\Documents\DC Bot`.
- Öffne die Datei mit Editor und füge eine Zeile ein:

```
DISCORD_TOKEN=DEIN_BOT_TOKEN_HIER
```

Ersetze `DEIN_BOT_TOKEN_HIER` mit dem Token, das du im Discord Developer Portal bekommst.

5) Configs anpassen (IDs eintragen)
----------------------------------
Beim ersten Start erzeugt der Bot automatisch Dateien in `config/` (aus `config.example.json`). Dort stehen Platzhalter (0).

So findest du die richtigen Zahlen (IDs) in Discord:
1. Öffne Discord → Einstellungen → Erweitert → Developer Mode einschalten.
2. Rechtsklick auf Server/Channel/Role → „ID kopieren“.
3. Öffne z.B. `config/tickets.json` mit Editor und setze die richtigen IDs ein (ohne Anführungszeichen).

Wichtige Felder (Beispiele):
- `TICKET_CATEGORY_ID`: Kategorie, in der Ticket‑Channels angelegt werden.
- `SUPPORT_ROLE_ID`: Rolle, die Tickets sehen darf (Support-Team).
- `TICKET_LOG_CHANNEL_ID`: Kanal, in den Ticket‑Ereignisse geloggt werden.

6) Gängige Befehle (im Discord‑Chat)
----------------------------------
- `*ping` → Prüft, ob der Bot antwortet.
- `*help` → Zeigt das Hilfemenü mit allen Funktionen.
- `*ticketpanel` (Admin) → Postet das Ticket‑Panel, damit Nutzer Tickets öffnen können.
- Klicken auf den Button „Create Ticket“ → Ein privater Ticket‑Channel wird erstellt.
- In einem Ticket‑Channel: Buttons `Claim`, `Close`, `Transcript` verwenden.
- `*poll <frage>` → Erstellt eine Umfrage (folgen den Anweisungen im Chat).

7) Logs & Transkripte
---------------------
- Logs (Datenbank): `data/db/logs.db`.
- Tickets (Datenbank): `data/db/tickets.db`.
- Transkripte (Text): `data/tickets/transcripts/<channel_id>.txt`.
- Tools zum Abfragen: `python tools\query_logs.py recent` etc.

8) Fehlerbehebung (häufige Probleme)
-----------------------------------
- Bot startet nicht / Token fehlt → Stelle sicher, dass `.env` vorhanden ist und `DISCORD_TOKEN` richtig gesetzt ist.
- Fehlende Abhängigkeiten → innerhalb des Projektordners ausführen:

```powershell
python -m pip install -r requirements.txt
```

- Der Bot meldet Import‑Fehler → Starte den Bot neu (manchmal nach Dateiansagen nötig):

```powershell
# Prozess beenden (falls Konsole offen bleibt):
Get-Process -Name python | Stop-Process -Force

# Neu starten:
python bot.py
```

- Probleme mit Berechtigungen in Channels (Tickets nicht sichtbar): Stelle sicher, dass die `SUPPORT_ROLE_ID` korrekt ist und die Rolle Administrator‑ oder Sichtrechte hat.

9) Wie ich dir weiterhelfe
-------------------------
- Wenn du willst, kann ich:
  - Schritt für Schritt per Ferndiagnose prüfen, wenn du mir Konsoleausgaben zeigst.
  - Für dich eine Beispiel‑`config/tickets.json` mit Platzhaltern erstellen (du musst nur IDs eintragen).
  - Die wichtigsten Befehle im Discord testen (Ticket öffnen, Poll erstellen) — sag kurz, welche Tests du möchtest.

Datei im Projekt: `docs/BEGINNER_GUIDE_DE.md`

Wenn du möchtest, mache ich jetzt eine Beispiel‑`config/tickets.json` mit kommentierten Feldern und zeige dir, wie du die IDs einträgst. Soll ich das tun? 
