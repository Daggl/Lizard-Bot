Query Logs - README
=====================

Kurzbeschreibung
---------------
Dieses kleine Tool hilft beim Durchsuchen und Exportieren der Log‑Datenbank `data/logs/logs.db`.

Datei
-----
- `tools/query_logs.py` — CLI‑Skript mit vordefinierten Abfragen (recent, by-category, by-user, count-by-type, search, raw).

Voraussetzungen
---------------
- Python 3.8+ installiert
- Die Datei `data/logs/logs.db` existiert und wird vom Bot beschrieben

Beispiele
---------
- Zeige die 20 neuesten Logs:

```powershell
python tools\query_logs.py recent
```

- Logs der Kategorie `chat` (max 50):

```powershell
python tools\query_logs.py by-category chat -n 50
```

- Logs eines Nutzers (ID):

```powershell
python tools\query_logs.py by-user 123456789012345678
```

- Zähle Ereignisse gruppiert nach Typ:

```powershell
python tools\query_logs.py count-by-type
```

- Suche Nachrichten nach Begriff (z.B. "password"):

```powershell
python tools\query_logs.py search "password" -n 100
```

- Raw SQL ausführen und als CSV exportieren:

```powershell
python tools\query_logs.py raw "SELECT * FROM logs WHERE category='chat' ORDER BY id DESC LIMIT 100" --export out.csv
```

Hinweis
------
Das Skript ist bewusst einfach gehalten. Falls du vordefinierte Abfragen (z. B. Bans der letzten 30 Tage) möchtest, sag mir kurz welche, dann ergänze ich sie.

Für absolute Anfänger (sehr einfach erklärt)
-----------------------------------------

Wenn du mit Computern und Terminals fast gar keine Erfahrung hast, hier eine Schritt‑für‑Schritt‑Anleitung:

1. Öffne das Programm "PowerShell" auf Windows (oder Terminal auf Mac/Linux).
2. Tippe genau diese Zeile ein und drücke Enter, damit du in den Ordner mit dem Bot wechselst:

```powershell
cd "C:\Users\mahoe\Documents\DC Bot"
```

3. Um eine Liste der neuesten Log‑Einträge zu sehen, kopiere diese Zeile und drücke Enter:

```powershell
python tools\query_logs.py recent
```

4. Wenn du eine bestimmte Suche möchtest (z. B. alle Bans der letzten 30 Tage), benutze das hier:

```powershell
python tools\query_logs.py raw "SELECT * FROM logs WHERE category='mod' AND type='ban' AND timestamp >= datetime('now','-30 days') ORDER BY id DESC"
```

	- Erklärung: Das Programm fragt die Log‑Datenbank ab und zeigt dir alle Ban‑Einträge der letzten 30 Tage.
	- Keine Sorge, das ändert nichts in der Datenbank – es zeigt nur Ergebnisse an.

5. Wenn du die Ergebnisse in einer Datei haben möchtest (z. B. `bans_30d.csv`), füge `--export` hinzu:

```powershell
python tools\query_logs.py raw "SELECT * FROM logs WHERE category='mod' AND type='ban' AND timestamp >= datetime('now','-30 days') ORDER BY id DESC" --export bans_30d.csv
```

	- Danach findest du die Datei `bans_30d.csv` im selben Ordner, die du mit Excel öffnen kannst.

Sicherheitshinweis für Anfänger
-------------------------------
- Nutze die vorgefertigten Befehle (`recent`, `by-category`, `search`) wenn du unsicher bist.
- Verwende `raw` nur, wenn du genau den SQL‑Text aus einer vertrauenswürdigen Quelle kopierst (wie hier oben).

Wenn du möchtest, kann ich die Abfrage "Bans der letzten 30 Tage" direkt als eigenen Befehl in `query_logs.py` hinzufügen, sodass du nur `python tools\query_logs.py bans-30d` tippen musst. Soll ich das machen?
