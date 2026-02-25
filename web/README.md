# Web Workspace

Dieses Verzeichnis enthält das Dashboard in zwei Teilen:

- `backend/` — FastAPI API für Config- und Upload-Endpunkte
- `frontend/` — React + Vite UI

## Lokaler Start

### Backend

```powershell
.\.venv\Scripts\python -m uvicorn web.backend.main:app --host 127.0.0.1 --port 8000
```

### Frontend

```powershell
npm --prefix web/frontend install
npm --prefix web/frontend run dev
```

## Wichtige Umgebungsvariablen

- `WEB_INTERNAL_TOKEN` — optionaler Schutz für interne Backend-Endpunkte

## Weitere Doku

- Backend-Details: [backend/README.md](backend/README.md)
- Frontend-Details: [frontend/README.md](frontend/README.md)
