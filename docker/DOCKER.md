# Docker quickstart

This repository includes Dockerfiles and a `docker-compose.yml` to run the
backend, frontend and bot as containers. Quick start:

```bash
# build and start all services (backend:8000, frontend:5173)
docker compose -f docker/docker-compose.yml up --build

# stop
docker compose -f docker/docker-compose.yml down
```

Notes:
- Containers read environment variables from the repository `.env` file (if present).
- The python image uses `docker/Dockerfile.python`; the frontend is built with `docker/Dockerfile.frontend`.
- For production you should run builds on a CI, avoid mounting the full repo as a volume, and supply secrets via an external secret manager.
