# Migration: Flask/Django → FastAPI

## Summary

| Before | After |
|--------|------|
| Flask app (app.py) + optional Django (manage.py) | Single FastAPI app (`pbm_research_agent/app/main.py`) |
| Raw SQLite in db.py | SQLAlchemy ORM + optional Alembic; same SQLite path or PostgreSQL |
| Monolithic pbm_agent.py | Modular agents/, graph/, services/ |
| settings.py | Pydantic Settings in app/core/config.py |
| /api/chat/send/, /api/chat/sessions/, /api/chat/history/ | Same paths supported (legacy) + new /api/chat, /api/sessions |

## Steps

1. **Run both in parallel (optional)**  
   Keep the old app on port 8000; run FastAPI on 8001. Point the UI to the new base URL or use a reverse proxy to switch.

2. **Data**  
   - **Chat DB**: Use `data/chat.db` by default (project root is `pbm_research_agent`, so `data/` is `pbm_research_agent/data/`). If you introduce PostgreSQL, set `DATABASE_URL` and run Alembic.  
   - **Knowledge DB**: Use `data/knowledge.db`; copy or generate it into `pbm_research_agent/data/`.

3. **Environment**  
   Reuse `.env`: `OPENAI_API_KEY`, `PORT`, etc. Add if needed: `DATABASE_URL` (for PostgreSQL), `LOG_LEVEL`.

4. **Frontend**  
   No change required: existing chat UI still uses `/api/chat/send/`, `/api/chat/sessions/`, `/api/chat/history/{id}/`. Optionally switch to `POST /api/chat` with `query` and use the new response fields (`latency_ms`, etc.).

5. **Decommission**  
   Once validated, stop the Flask/Django server and run only FastAPI from project root: `cd pbm_research_agent && uvicorn app.main:app`, or use Docker.

## Production deployment

- **Process**: Run with Gunicorn + Uvicorn workers or multiple Uvicorn workers behind a reverse proxy.  
- **Database**: Set `DATABASE_URL` to PostgreSQL; run Alembic migrations; use connection pooling.  
- **Secrets**: Use a secrets manager or vault; inject env (e.g. `OPENAI_API_KEY`) at runtime.  
- **Observability**: Send logs to a central system; optionally add OpenTelemetry for tracing.  
- **Docker**: Use the provided Dockerfile; mount or copy `data` for SQLite, or use external PostgreSQL.
