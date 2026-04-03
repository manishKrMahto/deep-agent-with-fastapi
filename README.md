# Deep Research Agent — FastAPI

Production-style **FastAPI** backend for the **PBM Deep Research Agent**: multi-agent **LangGraph** hybrid RAG with session persistence, streaming agent steps, observability, and a bundled chat UI.

---

## Features

- **Django → FastAPI**: Migrated stack with a frontend that consumes the API (chat at `/`, sessions, history, streaming).
- **Memory persistence**: Short-term conversation context is kept in-session and passed into the pipeline.
- **Live streaming**: LangGraph emits **agent_step** events over **SSE**; the UI updates in real time.
- **Output validation**: The notebook `test_query.ipynb` can validate answers against expected pandas results via the local API.
- **Charts on request**: Natural-language chart requests can return **text + base64 PNG**; images persist in `messages.chart_image_base64` and appear in PDF exports.
- **PDF export**: **Export PDF** in the chat header or `GET /api/sessions/{id}/export/pdf`.
- **Knowledge DB**: `data/knowledge.db` powers Hybrid RAG SQL; optional bootstrap from `pbm_claims_full.csv` at startup.

---

## Architecture

- **API**: FastAPI, Pydantic, OpenAPI at `/docs`.
- **Agents**: `DOC_TOOL` → routing → **Direct LLM** or **Hybrid RAG** (`SQL_AGENT` → `SQL_GUARDRAIL` → `SQL_EXECUTE` → optional `CHART` → `REPORT` → `FORMATTER` → `JUDGE`).
- **State**: `AgentState` holds `query`, `route`, `sql_query`, `db_result`, `history`, `answer`, `sources`, `confidence`, `reasoning`, etc.
- **DB**: SQLAlchemy for chat (sessions/messages, `query_logs`); SQLite under `data/` by default, PostgreSQL via `DATABASE_URL`.
- **Knowledge**: SQLite in `data/knowledge.db` (table `dataset`); schema introspection and read-only execution in services.

---

## Project structure

```
deep-agent-with-fastapi/
├── app/
│   ├── api/routes/         # chat, health, sessions, auth
│   ├── agents/             # router, direct_llm, sql, report, judge, formatter, doc_tool, chart
│   ├── graph/              # agent_state, langgraph_builder
│   ├── db/
│   ├── services/
│   └── main.py
├── data/                   # chat.db, knowledge.db, optional CSV
├── templates/chat/         # Chat UI
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── alembic.ini
└── README.md
```

---

## Setup

1. **Virtual env and install**

   ```bash
   git clone https://github.com/manishKrMahto/deep-agent-with-fastapi.git
   cd deep-agent-with-fastapi
   python -m venv .venv
   .venv\Scripts\activate
   # source .venv/bin/activate   # macOS/Linux
   pip install -r requirements.txt
   ```

2. **Environment** — create `.env` in the project root:

   ```env
   OPENAI_API_KEY=your_key
   PORT=8000
   LOG_LEVEL=INFO
   # Optional: DATABASE_URL=postgresql://user:pass@host/db
   ```

3. **Migrations**

   ```bash
   alembic upgrade head
   ```

4. **Data**

   - **Chat DB**: `data/chat.db` on first run (or `DATABASE_URL`).
   - **Knowledge DB**: `data/knowledge.db` for Hybrid RAG; auto-created from `pbm_claims_full.csv` if present, or:

     ```bash
     python -m app.scripts.init_knowledge_db --recreate
     ```

---

## Run

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- **Chat UI**: http://127.0.0.1:8000/
- **OpenAPI**: http://127.0.0.1:8000/docs
- **Logs**: http://127.0.0.1:8000/api/logs?limit=20

### Example queries

- Charts: `Create a chart for how many claims were filled each month?`
- SQL / text: `How has the usage of Erlotinib changed over time?`, `Can you show the total rebate for each region?`

---

## API

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Liveness / readiness |
| POST | `/api/auth/signup` | Sign up |
| POST | `/api/auth/login` | Login |
| PUT | `/api/auth/profile/name` | Update name |
| POST | `/api/chat` | Send message (`query`) |
| POST | `/api/chat/send/` | Legacy chat (`message`) |
| POST | `/api/chat/send/stream` | SSE: live steps, then `done` |
| GET | `/api/sessions` | List sessions |
| GET | `/api/sessions/{id}/history` | History (includes `chart_image_base64` when set) |
| GET | `/api/sessions/{id}/export/pdf` | PDF export |
| GET | `/api/chat/sessions/` | Legacy sessions |
| GET | `/api/chat/history/{id}/` | Legacy history |
| GET | `/api/chat/history/{id}/export/pdf` | Legacy PDF |
| GET | `/api/logs` | Recent `query_logs` |

---

## Observability

- **Request ID**: `X-Request-ID`
- **Latency**: `X-Response-Time-Ms` and structured logs
- **Logging**: `app.core.logging_config`; level via `LOG_LEVEL`

---

## LangGraph pipeline diagram

Animated Mermaid flowchart (edge animation works best in [Mermaid Live](https://mermaid.live) and compatible renderers). **Interactive view (animated):** [open this diagram in Mermaid Live](https://mermaid.live/view#pako:eNqVle1umzAUhm_lyFKlVkqrAAFSpHVjgaSZSOgoVdeRKmLBSdCIHRmyrUtyF_u_X7u_XcKMTWikdRJDgvPhx-dwXlnyFs1ogpGF5hn9OlvGrIDQmZAJAf6cnMBtaAch9D3_XqZEfBoJ83gGmfLm_PwKHL8X8Xca-r73KEEeQqaK1cC_C91gK83-qLjn9kO4scNrOB3792CPhyM7dJ0zCUgeMq0ssnOGgdsLp5432oH0o-fUoadIQNYRbXv-uL-dUTJPE0xmGK5eQfuiq7-u_6AEINNF-Sec78AdO6cR_zyeHQOGAAjdwbs7Z-AqkTBVS5mCzBQt-d6j8YLh4Pown-0Fru08_GNGJmTcXT-8DYbONLAHO7h9703tgTsOo9qrWtYxMKlvmRjc2YET1V5gD70jXOSAaTXufnB70cHhv3DElhlgUsLAvfGDMJKmYmQATOgGfT_g8_AZotqruDoGJhSUUql_q6cCe0m93z9__AKbpKu4wPKk4GSBc7nOz90WYrloQcE2uFWFKSUWzOO8gH2Fqs1RrTnaaY7qzVGjOWo2Ql-WU57MIz1Zcz1Zcz1Zcz1Zcz1Zcz1Zcz3Zf-rpr8uFOIN8RWmxhNmGfalPZ0o-3xZPGYYEz-NNVkBKCszWNCvF_xTnaY5aaMHSBFmiE1phtorLEG3LEhNULPEKT5DF3arGBE3Inm9bx-QjpavDTkY3iyWy5nGW82izTngLJ40XLH5GMEkw69ENKZDV6YoSyNqib8jSDOVCaXd1TeuaHdVQL1voCVnnxoWuKYaidjTF1LW2eblvoe-iKcdNVVfbqtE22oppqrwcTtKCspG8R8R1sv8DGOfyig).

```mermaid
flowchart TD

    START([START]) l1@--> DOC[DOC_TOOL]
    DOC l2@--> ROUTER{ROUTER}

    ROUTER l3@-->|DIRECT_LLM| DIRECT[DIRECT_LLM]
    DIRECT l4@--> CONF{confidence >= 0.85?}

    CONF l5@-->|yes| END([END])
    CONF l6@-->|no| JUDGE1[JUDGE]
    JUDGE1 l7@--> END

    ROUTER r1@-->|HYBRID_RAG| SQL_AGENT[SQL_AGENT]
    SQL_AGENT r2@--> SQL_GUARD[SQL_GUARDRAIL]
    SQL_GUARD r3@--> SQL_EXEC[SQL_EXECUTE]
    SQL_EXEC r4@--> REPORT[REPORT]
    REPORT r5@--> FORMATTER[FORMATTER]
    FORMATTER r6@--> JUDGE2[JUDGE]
    JUDGE2 r7@--> END

    l1@{ animate: true, animation: fast }
    l2@{ animate: true, animation: fast }
    l3@{ animate: true, animation: fast }
    l4@{ animate: true, animation: fast }
    l5@{ animate: true, animation: fast }
    l6@{ animate: true, animation: fast }
    l7@{ animate: true, animation: fast }

    r1@{ animate: true, animation: fast }
    r2@{ animate: true, animation: fast }
    r3@{ animate: true, animation: fast }
    r4@{ animate: true, animation: fast }
    r5@{ animate: true, animation: fast }
    r6@{ animate: true, animation: fast }
    r7@{ animate: true, animation: fast }

    linkStyle default interpolate basis
```

When the user requests a chart and the database returns rows, the running app inserts a **CHART** node between `SQL_EXECUTE` and `REPORT` (see `langgraph_builder.py`). Conceptually:

```mermaid
flowchart LR
    SQL_EXEC[SQL_EXECUTE] --> CHOICE{chart + rows?}
    CHOICE -->|yes| CHART[CHART]
    CHOICE -->|no| REPORT[REPORT]
    CHART --> REPORT
```

### Latest architecture

This is the **latest** end-to-end architecture: **Agent Picker** (routing), **retry loops** on direct confidence and SQL output quality, **DB logging** at key points, and **chart vs report** branching before formatting. In the codebase, **Agent Picker** corresponds to **ROUTER** / orchestration after `DOC_TOOL`.

```mermaid
flowchart TD

    %% START
    START([START]) e1@==> DOC[DOC_TOOL]
    DOC e2@==> ROUTER[AGENT PICKER]

    %% =========================
    %% 🔹 DIRECT LLM PATH
    %% =========================
    ROUTER e3@==>|Direct LLM| DIRECT[DIRECT_LLM]
    DIRECT e4@==> JUDGE1[JUDGE]
    JUDGE1 e5@==> CONF{Confidence High?}

    CONF e6@==>|Yes| END([END])
    CONF e7@==>|No → Retry| DIRECT

    %% =========================
    %% 🔹 SQL AGENT PATH
    %% =========================
    ROUTER e8@==>|SQL Agent| SQL_AGENT[SQL_AGENT]
    SQL_AGENT e9@==> SQL_GUARD[SQL_GUARDRAIL]
    SQL_GUARD e10@==> SQL_EXEC[SQL_EXECUTE]

    %% DB LOGGING AFTER EXECUTION
    SQL_EXEC e11@==> DB1[(DB LOGGING)]

    DB1 e12@==> JUDGE2[JUDGE]
    JUDGE2 e13@==> CHECK{Output Correct?}

    CHECK e14@==>|No → Retry| SQL_AGENT
    CHECK e15@==>|Yes| DECISION{Chart Requested?}

    %% CHART FLOW
    DECISION e16@==>|Yes| CHART[CHART GENERATION]
    CHART e17@==> REPORT[REPORT GENERATION]

    %% NO CHART FLOW
    DECISION e18@==>|No| REPORT

    %% FINAL FLOW
    REPORT e19@==> FORMATTER[FORMATTER]

    %% FINAL DB LOG
    FORMATTER e20@==> DB2[(DB LOGGING)]

    DB2 e21@==> END

    %% =========================
    %% 🔥 ANIMATION CONFIG
    %% =========================
    e1@{ animate: true, animation: fast }
    e2@{ animate: true, animation: fast }
    e3@{ animate: true, animation: fast }
    e4@{ animate: true, animation: fast }
    e5@{ animate: true, animation: fast }
    e6@{ animate: true, animation: fast }
    e7@{ animate: true, animation: fast }
    e8@{ animate: true, animation: fast }
    e9@{ animate: true, animation: fast }
    e10@{ animate: true, animation: fast }
    e11@{ animate: true, animation: fast }
    e12@{ animate: true, animation: fast }
    e13@{ animate: true, animation: fast }
    e14@{ animate: true, animation: fast }
    e15@{ animate: true, animation: fast }
    e16@{ animate: true, animation: fast }
    e17@{ animate: true, animation: fast }
    e18@{ animate: true, animation: fast }
    e19@{ animate: true, animation: fast }
    e20@{ animate: true, animation: fast }
    e21@{ animate: true, animation: fast }

    linkStyle default interpolate basis
```

---

## Docker

```bash
docker-compose up --build
```

API: http://localhost:8000 — ensure `data/knowledge.db` exists for Hybrid RAG.

---

## Migration from Flask / Django

- **Chat**: `POST /api/chat` with `query` or `POST /api/chat/send/` with `message`.
- **Sessions**: `GET /api/sessions` or legacy chat routes.
- **PDF**: `GET /api/sessions/{id}/export/pdf` or legacy PDF route.
- **DB**: `data/chat.db` or `DATABASE_URL` + Alembic.
- **Knowledge**: `data/knowledge.db` in `data/`.

See `docs/MIGRATION.md` for detail.
