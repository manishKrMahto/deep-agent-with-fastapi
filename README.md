# PBM Research Agent — FastAPI

Production-style FastAPI backend for the PBM Deep Research Agent: multi-agent LangGraph Hybrid RAG with session persistence, observability, and enterprise structure.

**Project root**: this directory (`pbm_research_agent`). All commands below assume you are in this directory:

```bash
cd pbm_research_agent
```

## Architecture

- **API**: FastAPI with async endpoints, Pydantic schemas, dependency injection, OpenAPI at `/docs`.
- **Agents**: Orchestrator → Router → Direct LLM or Hybrid RAG (SQL Agent → Guardrail → DB → Report → Formatter → Judge).
- **State**: Single `AgentState` (LangGraph) with `query`, `route`, `sql_query`, `db_result`, `history`, `answer`, `sources`, `confidence`, `reasoning`, etc.
- **DB**: SQLAlchemy ORM for chat (sessions/messages) + per-request logs in `agent_run_logs`; SQLite in `data/` by default, PostgreSQL via `DATABASE_URL`.
- **Knowledge DB**: SQLite in `data/knowledge.db` for PBM claims (table `dataset`); schema introspection and read-only execution in services.

## Project structure

```
pbm_research_agent/          ← project root (you are here)
├── app/
│   ├── api/
│   │   ├── routes/         # chat, health, sessions
│   │   ├── deps.py         # get_db, repositories
│   │   └── router.py
│   ├── core/               # config, logging, security
│   ├── agents/             # router, direct_llm, sql, report, judge, formatter, doc_tool
│   ├── graph/              # agent_state, langgraph_builder
│   ├── db/                 # database, models, repository, migrations
│   ├── services/           # chat_service, knowledge_db_service, knowledge_db_init
│   ├── scripts/            # init_knowledge_db
│   ├── schemas/            # chat_schema (request/response)
│   └── main.py
├── data/                   # chat.db, knowledge.db, optional CSV for claims
├── templates/chat/         # Chat UI
├── tests/
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── alembic.ini
└── README.md
```

## Setup

1. **Virtual env and install**

   ```bash
   cd pbm_research_agent
   python -m venv .venv
   .venv\Scripts\activate   # Windows
   # source .venv/bin/activate   # macOS/Linux
   pip install -r requirements.txt
   ```

2. **Environment**

   Create `.env` in the project root (`pbm_research_agent/.env`):

   ```env
   OPENAI_API_KEY=your_key
   PORT=8000
   LOG_LEVEL=INFO
   # Optional: DATABASE_URL=postgresql://user:pass@host/db  (default: SQLite at data/chat.db)
   ```

3. **Data**

   - **Chat DB**: Created automatically at `data/chat.db` on first run (or use `DATABASE_URL` for PostgreSQL).
   - **Knowledge DB**: The app expects `data/knowledge.db` for Hybrid RAG SQL queries.
     - If `pbm_claims_full.csv` exists in the project root, the app will **auto-create** `data/knowledge.db` on startup (table: `dataset`).
     - You can also build it manually:

       ```bash
       python -m app.scripts.init_knowledge_db --recreate
       ```

     - Optional env overrides:
       - `AUTO_INIT_KNOWLEDGE_DB=true|false`
       - `KNOWLEDGE_CSV_PATH=path/to/pbm_claims_full.csv`

4. **Migrations (optional)**

   From project root:

   ```bash
   alembic upgrade head
   ```

## Run

From the project root (`pbm_research_agent`):

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Then open:

- **Chat UI**: http://127.0.0.1:8000/
- **OpenAPI**: http://127.0.0.1:8000/docs

## API

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Liveness/readiness |
| POST | `/api/chat` | Send message (body: `query`) — session is managed by the backend |
| POST | `/api/chat/send/` | Legacy chat (body: `message`) used by the bundled UI |
| GET | `/api/sessions` | List sessions |
| GET | `/api/sessions/{id}/history` | Messages for session |
| GET | `/api/chat/sessions/` | Legacy session list |
| GET | `/api/chat/history/{id}/` | Legacy history |

Response for chat includes: `answer`, `sources`, `confidence`, `reasoning`, `latency_ms`, `session_id`, and optionally `final_report` / `agent_message` for the UI.

## Observability

- **Request ID**: `X-Request-ID` on request/response; set automatically if missing.
- **Latency**: `X-Response-Time-Ms` and structured logs with `request_id` and `latency_ms`.
- **Logging**: Configured in `app.core.logging_config`; level via `LOG_LEVEL`.
- **Per-request agent logs**: `data/chat.db` contains an `agent_run_logs` table with one row per agent run (`user_query`, `route`, `sql_query`, `db_row_count`, `sources`, `confidence`, `latency_ms`, `reasoning`) for audit and debugging.

## Docker

From project root:

```bash
docker-compose up --build
```

API at http://localhost:8000. The compose file mounts `./data` for persistent SQLite; ensure `data/knowledge.db` exists if you use Hybrid RAG.

## Tests

From project root:

```bash
pytest
```

## Migration from Flask/Django app

- **Chat**: Use `POST /api/chat` with `query` or keep using `POST /api/chat/send/` with `message`.
- **Sessions**: Use `GET /api/sessions` or legacy `GET /api/chat/sessions/` and `GET /api/chat/history/{id}/`.
- **DB**: Use default SQLite at `data/chat.db`, or set `DATABASE_URL` and run Alembic for PostgreSQL.
- **Knowledge DB**: Use `data/knowledge.db`; copy or generate it from your claims data into this project’s `data/` folder.

See `docs/MIGRATION.md` for more detail.
