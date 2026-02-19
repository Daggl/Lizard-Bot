Query Logs - README
=====================

Kurzbeschreibung
---------------
Dieses kleine Tool hilft beim Durchsuchen und Exportieren der Log‑Datenbank `data/db/logs.db`.

Datei
-----
- `tools/query_logs.py` — CLI‑Skript mit vordefinierten Abfragen (recent, by-category, by-user, count-by-type, search, raw).

Voraussetzungen
---------------
- Python 3.8+ installiert
- Die Datei `data/db/logs.db` existiert und wird vom Bot beschrieben

Beispiele
---------
- Zeige die 20 neuesten Logs:

```markdown
# tools/query_logs.py — Quick Beginner Guide

This tool helps you inspect and export the bot's centralized log database (`data/db/logs.db`). Use the prebuilt commands if you are unsure; only use `raw` SQL when you know what you are doing.

Prerequisites
-------------
- Python 3.8+ installed
- The bot has previously created `data/db/logs.db` (run the bot at least once)

Basic usage (PowerShell)
------------------------
Open PowerShell in the project folder (or run `cd "C:\Users\mahoe\Documents\DC Bot"`) and then:

Show the 20 newest logs:

```powershell
python tools\query_logs.py recent
```

Show logs from category `chat` (max 50):

```powershell
python tools\query_logs.py by-category chat -n 50
```

Show logs for a specific user (replace ID):

```powershell
python tools\query_logs.py by-user 123456789012345678
```

Count events grouped by type:

```powershell
python tools\query_logs.py count-by-type
```

Search for a text term (e.g. "password"):

```powershell
python tools\query_logs.py search "password" -n 100
```

Run a raw SQL query (advanced) and export as CSV:

```powershell
python tools\query_logs.py raw "SELECT * FROM logs WHERE category='chat' ORDER BY id DESC LIMIT 100" --export out.csv
```

Notes for beginners
-------------------
- Use the built-in commands (`recent`, `by-category`, `by-user`, `search`) if you are not comfortable with SQL.
- `raw` runs the SQL you provide directly against the database — it is for advanced users only.
- Exported CSV files appear in the current folder and can be opened in Excel.

Extra help
----------
If you want, I can add custom convenience commands (for example `bans-30d`) so you don't need to type raw SQL. Tell me which frequently-used queries you want and I'll add them.

```

