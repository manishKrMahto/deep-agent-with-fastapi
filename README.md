# PBM Research Agent — FastAPI

Production-style FastAPI backend for the PBM Deep Research Agent: multi-agent LangGraph Hybrid RAG with session persistence, observability, and enterprise structure.

## Features

- **Django → FastAPI**: Migrated from Django to FastAPI with a frontend page that consumes the API (chat UI at `/`, sessions, history, streaming).
- **Memory persistence**: The agent keeps short-term memory of past conversations in the session; recent turns are passed into the pipeline so it can reference prior context.
- **Live streaming of agent steps**: Backend state is streamed to the frontend so users see which steps are running in real time. The flow is dynamically driven by LangGraph, not static:
  ```
  User Query → FastAPI Endpoint → LangGraph Execution
       → emit agent_step events → SSE Stream → Frontend UI updates live → Final Answer displayed
  ```
- **Output validation**: The notebook `test_query.ipynb` validates agent answers by computing expected results with pandas against the same data, calling the API at `http://localhost:8000`, and comparing outputs. Results are marked as **correct** or **partial correct** in the notebook.
- **Charts on request**: When the user asks to generate a chart or image (e.g. “create a chart for total rebate by region”), the agent can respond with both **text and a chart image** (base64 PNG in the response, rendered in the chat UI).
- **Chart image persistence**: Chart images are stored in the database (`messages.chart_image_base64`) so they appear in chat history after refresh and in exported PDFs.
- **PDF export**: Chat history can be exported to PDF with text and images, matching the frontend layout (bubbles, Markdown, charts). Use the **Export PDF** button in the chat header or `GET /api/sessions/{id}/export/pdf`.
- **Knowledge DB from Django**: The PBM claims database was extracted from the original Django app and integrated into this FastAPI project as `data/knowledge.db`; the app uses it for Hybrid RAG SQL queries and chart data.

## Architecture

- **API**: FastAPI with async endpoints, Pydantic schemas, dependency injection, OpenAPI at `/docs`.
- **Agents**: Orchestrator → Router → Direct LLM or Hybrid RAG (SQL Agent → Guardrail → DB → Report → Formatter → Judge).
- **State**: Single `AgentState` (LangGraph) with `query`, `route`, `sql_query`, `db_result`, `history`, `answer`, `sources`, `confidence`, `reasoning`, etc.
- **DB**: SQLAlchemy ORM for chat (sessions/messages with optional `chart_image_base64`) + per-request data-retriever logs in `query_logs`; SQLite in `data/` by default, PostgreSQL via `DATABASE_URL`.
- **Knowledge DB**: SQLite in `data/knowledge.db` for PBM claims (table `dataset`); schema introspection and read-only execution in services.

## Project structure

```
pbm_research_agent/          ← project root (you are here)
├── app/
│   ├── api/
│   │   ├── routes/         # chat, health, sessions, auth
│   │   ├── deps.py         # get_db, repositories
│   │   └── router.py
│   ├── core/               # config, logging, security
│   ├── agents/             # router, direct_llm, sql, report, judge, formatter, doc_tool
│   ├── graph/              # agent_state, langgraph_builder
│   ├── db/                 # database, models, repository, migrations
│   ├── services/           # chat_service, pdf_export_service, knowledge_db_service, knowledge_db_init
│   ├── scripts/            # init_knowledge_db
│   ├── schemas/            # chat_schema (request/response)
│   └── main.py
├── data/                   # chat.db, knowledge.db, optional CSV for claims
├── templates/chat/         # Chat UI
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── alembic.ini
└── README.md
```

## Setup

1. **Virtual env and install**

   ```bash
   git clone https://github.com/manishKrMahto/deep-agent-with-fastapi.git
   cd deep-agent-with-fastapi
   python -m venv .venv
   .venv\Scripts\activate   # Windows
   # source .venv/bin/activate   # macOS/Linux
   pip install -r requirements.txt
   ```

2. **Environment**

   Create `.env` or rename `.env.example` in the project root (`.env`):

   ```env
   OPENAI_API_KEY=your_key
   PORT=8000
   LOG_LEVEL=INFO
   # Optional: DATABASE_URL=postgresql://user:pass@host/db  (default: SQLite at data/chat.db)
   ```

3. **Database migrations**

   Run Alembic to apply migrations (e.g. add `chart_image_base64` to messages):

   ```bash
   alembic upgrade head
   ```

4. **Data**

   - **Chat DB**: Created automatically at `data/chat.db` on first run (or use `DATABASE_URL` for PostgreSQL).
   - **Knowledge DB**: The app expects `data/knowledge.db` for Hybrid RAG SQL queries.
     - If `pbm_claims_full.csv` exists in the project root, the app will **auto-create** `data/knowledge.db` on startup (table: `dataset`).
     - **Optional** You can also build it manually:

       ```bash
       python -m app.scripts.init_knowledge_db --recreate
       ```

     - **Optional** env overrides:
       - `AUTO_INIT_KNOWLEDGE_DB=true|false`
       - `KNOWLEDGE_CSV_PATH=path/to/pbm_claims_full.csv`

## Run

From the project root (`deep-agent-with-fastapi`):

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Then open:

- **Chat UI**: http://127.0.0.1:8000/
- **OpenAPI**: http://127.0.0.1:8000/docs

- **Run FastAPI locally**:

  ```bash
  uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
  ```

- **View recent SQL queries and logs**:

  - `http://127.0.0.1:8000/api/logs?limit=20`

### Example queries

- **Text + image (chart) examples**  
  These will run the Hybrid RAG + chart node and display a chart alongside the narrative:

  - `Create a chart for how many claims were filled each month?`
  - `Can you create a chart for the total rebate for each region?`
  - `create an chart for How has the usage of Erlotinib changed over time, month wise?`

- **Text-only examples**  
  These return text-only (no chart) and exercise the SQL + reporting pipeline:

  - `How has the usage of Erlotinib changed over time?`
  - `Can you show the total rebate for each region?` — correct
  - `Can you show the total copay amount for each drug in each region?` — correct
  - `What is the total pharmacy spending in each region?` — correct
  - `Which drugs generate the highest total cost for the health plan?` — correct
  - `Which therapeutic classes contribute the most to overall drug spending?` — correct
  - `Which pharmacy types (Retail, Mail Order, Specialty) process the most prescriptions?` — partial correct

## API

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Liveness/readiness |
| POST | `/api/auth/signup` | Create a user with email, full name, and password (case-insensitive unique email) |
| POST | `/api/auth/login` | Log in with email and password; returns basic user info |
| PUT | `/api/auth/profile/name` | Update a user's full name (body: `id`, `full_name`) |
| POST | `/api/chat` | Send message (body: `query`) — session is managed by the backend |
| POST | `/api/chat/send/` | Legacy chat (body: `message`) used by the bundled UI |
| POST | `/api/chat/send/stream` | SSE stream: agent steps live, then `done` with final answer |
| GET | `/api/sessions` | List sessions |
| GET | `/api/sessions/{id}/history` | Messages for session (includes `chart_image_base64` when present) |
| GET | `/api/sessions/{id}/export/pdf` | Download chat history as PDF (text + images) |
| GET | `/api/chat/sessions/` | Legacy session list |
| GET | `/api/chat/history/{id}/` | Legacy history |
| GET | `/api/chat/history/{id}/export/pdf` | Legacy PDF export |
| GET | `/api/logs` | Recent query logs (`query_logs`): query, SQL, response, latency |

Response for chat includes: `answer`, `sources`, `confidence`, `reasoning`, `latency_ms`, `session_id`, and optionally `final_report` / `agent_message` for the UI.

The bundled chat UI (at `/`) uses `POST /api/chat/send/stream` to:

- Show **live agent steps** via SSE (`event: step`, `data: {"step": "..."}`) while the LangGraph pipeline runs.
- Then receive a final `event: done` with the full answer, provenance footer, chart image (if any), and execution trace for that turn.

The UI also includes an **Export PDF** button (enabled when a session is selected) to download the chat history as a formatted PDF with text and chart images.

## Observability

- **Request ID**: `X-Request-ID` on request/response; set automatically if missing.
- **Latency**: `X-Response-Time-Ms` and structured logs with `request_id` and `latency_ms`.
- **Logging**: Configured in `app.core.logging_config`; level via `LOG_LEVEL`.
- **Per-request query logs**: `data/chat.db` contains a `query_logs` table with one row per agent run (`created_at`, `session_id`, `user_query`, `sql_query`, `response_text`, `latency_ms`) for audit and debugging. These are exposed via `GET /api/logs`.

## LangGraph pipeline diagram

The pipeline has two reference diagrams: **before** and **after** adding the chart-showing tool.

**Before** (without chart generation): the flow went from Router to either Direct LLM or Hybrid RAG (SQL Agent → Guardrail → Execute → Report → Formatter → Judge).

![LangGraph pipeline — before chart tool](langgraph_pipeline_workflow_old.png)

**After adding the chart showing tool**: when the user asks for a chart and the database returns rows, execution goes through a **CHART** node (generate chart from DB results) before **REPORT**. The decision “Chart requested? & DB rows?” branches to CHART then REPORT, or straight to REPORT.

![LangGraph pipeline — after chart tool](langgraph_pipeline_workflow_updated.png)

## Docker

From project root:

```bash
docker-compose up --build
```

API at http://localhost:8000. The compose file mounts `./data` for persistent SQLite; ensure `data/knowledge.db` exists if you use Hybrid RAG.

## Migration from Flask/Django app

- **Chat**: Use `POST /api/chat` with `query` or keep using `POST /api/chat/send/` with `message`.
- **Sessions**: Use `GET /api/sessions` or legacy `GET /api/chat/sessions/` and `GET /api/chat/history/{id}/`.
- **PDF export**: Use `GET /api/sessions/{id}/export/pdf` or `GET /api/chat/history/{id}/export/pdf` to download chat history (text + chart images).
- **DB**: Use default SQLite at `data/chat.db`, or set `DATABASE_URL` and run Alembic for PostgreSQL.
- **Knowledge DB**: Use `data/knowledge.db`; copy or generate it from your claims data into this project’s `data/` folder.

See `docs/MIGRATION.md` for more detail.
